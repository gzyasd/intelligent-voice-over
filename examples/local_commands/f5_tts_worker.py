from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
from pathlib import Path
from typing import Any

from f5_tts_command import write_silent_wav, wav_duration_ms

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def main() -> int:
    # 强制 stdout/stdin 用 UTF-8，避免中文路径/输出在 GBK 系统上解码失败
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Persistent JSONL worker for local F5-TTS.")
    parser.add_argument("--model-dir")
    parser.add_argument("--vocoder-dir")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    engine = None
    if not args.dry_run:
        # _load_engine 会 import torch/transformers/f5_tts，这些库可能往 stdout
        # 打印日志（版本/进度/警告），会污染 JSONL 协议流。重定向到 stderr（adapter
        # 已将 stderr 设为 DEVNULL，安全丢弃）。
        with contextlib.redirect_stdout(sys.stderr):
            engine = _load_engine(args)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            _write_response({"ok": False, "id": None, "error": str(exc)})
            continue
        if request.get("type") == "shutdown":
            break
        _write_response(_handle_request(request, args=args, engine=engine))
    return 0


def _handle_request(
    request: dict[str, Any],
    *,
    args: argparse.Namespace,
    engine: Any,
) -> dict[str, Any]:
    request_id = request.get("id")
    try:
        audio_path = Path(str(request["audio_out"]))
        duration_ms = int(request.get("duration_ms") or 1000)
        if args.dry_run:
            write_silent_wav(audio_path, duration_ms=duration_ms)
        else:
            if engine is None:
                raise RuntimeError("F5-TTS engine is not initialized")
            reference_audio = str(request.get("reference_audio") or "")
            if not reference_audio:
                raise ValueError("reference_audio is required")
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            # infer 期间 F5-TTS 可能用 tqdm 往 stdout 打印推理进度，污染 JSONL 协议流。
            # 重定向到 stderr（adapter 已丢弃）。
            with contextlib.redirect_stdout(sys.stderr):
                engine.infer(
                    ref_file=reference_audio,
                    ref_text=str(request.get("reference_text") or ""),
                    gen_text=str(request["text"]),
                    file_wave=str(audio_path),
                    speed=float(request.get("speed") or 1.0),
                )
            duration_ms = wav_duration_ms(audio_path)
        return {
            "ok": True,
            "id": request_id,
            "audio_path": str(audio_path),
            "duration_ms": duration_ms,
        }
    except Exception as exc:
        return {"ok": False, "id": request_id, "error": str(exc)}


def _load_engine(args: argparse.Namespace) -> Any:
    if not args.model_dir:
        raise ValueError("--model-dir is required")
    model_dir = Path(args.model_dir).resolve()
    if not model_dir.is_dir():
        raise ValueError(f"model directory not found: {model_dir}")

    preferred_checkpoint = model_dir / "F5TTS_v1_Base" / "model_1250000.safetensors"
    checkpoints = sorted(model_dir.rglob("*.safetensors"))
    if not checkpoints:
        raise ValueError(f"F5-TTS checkpoint not found under: {model_dir}")
    checkpoint = preferred_checkpoint if preferred_checkpoint.is_file() else checkpoints[-1]
    vocab_candidates = [checkpoint.parent / "vocab.txt", model_dir / "vocab.txt"]
    vocab = next((path for path in vocab_candidates if path.is_file()), None)
    if vocab is None:
        raise ValueError(f"F5-TTS vocab.txt not found under: {model_dir}")

    vocoder_dir = (
        Path(args.vocoder_dir).resolve()
        if args.vocoder_dir
        else model_dir.parent / "vocos-mel-24khz"
    )
    if not vocoder_dir.is_dir():
        raise ValueError(f"local vocoder directory not found: {vocoder_dir}")

    from _f5_tts_runner import _mock_unneeded_training_modules, _patch_torchaudio_load

    _mock_unneeded_training_modules()
    _patch_torchaudio_load()
    from f5_tts.api import F5TTS  # type: ignore[import-not-found]

    return F5TTS(
        model="F5TTS_v1_Base",
        ckpt_file=str(checkpoint),
        vocab_file=str(vocab),
        vocoder_local_path=str(vocoder_dir),
        device=None if args.device == "auto" else args.device,
    )


def _write_response(response: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(response, ensure_ascii=True) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
