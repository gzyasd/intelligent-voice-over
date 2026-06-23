from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any

# Force HuggingFace Hub offline mode so F5-TTS / vocos load from local cache
# instead of attempting network downloads (which timeout and crash the process).
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def main() -> int:
    # Suppress known harmless Google API Python version FutureWarning
    import warnings

    warnings.filterwarnings(
        "ignore",
        message=".*Python version.*Google.*",
        category=FutureWarning,
    )

    parser = argparse.ArgumentParser(description="TTS command adapter skeleton for F5-TTS.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--speaker", required=True)
    parser.add_argument("--audio-out", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--reference-audio")
    parser.add_argument("--reference-text", default="")
    parser.add_argument("--style-prompt", default="")
    parser.add_argument("--duration-ms", type=int, default=1000)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--model-dir")
    parser.add_argument("--vocoder-dir")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--engine-command-json")
    parser.add_argument("--engine-command-json-file")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    audio_path = Path(args.audio_out)
    if args.dry_run:
        write_silent_wav(audio_path, duration_ms=args.duration_ms)
        write_contract(Path(args.json_out), audio_path, args.duration_ms)
        return 0

    engine_command_json = load_engine_command_json(args)
    if engine_command_json:
        command = render_engine_command(engine_command_json, args)
        # Try in-process first; if it crashes, fall back to subprocess with retries.
        if run_f5_tts_with_retries(command, audio_path):
            write_contract(Path(args.json_out), audio_path, wav_duration_ms(audio_path))
            return 0
        raise SystemExit(f"TTS engine failed after retries: {command}")

    try:
        run_direct_inference(args)
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"F5-TTS local inference failed: {exc}") from exc
    write_contract(Path(args.json_out), audio_path, wav_duration_ms(audio_path))
    return 0


def run_direct_inference(args: argparse.Namespace) -> None:
    """Run the installed F5-TTS Python API against the bundled local checkpoint."""
    if not args.model_dir:
        raise ValueError("--model-dir is required when no engine command is configured")
    if not args.reference_audio:
        raise ValueError("--reference-audio is required for voice cloning")

    model_dir = Path(args.model_dir).resolve()
    reference_audio = Path(args.reference_audio).resolve()
    output_path = Path(args.audio_out).resolve()
    if not model_dir.is_dir():
        raise ValueError(f"model directory not found: {model_dir}")
    if not reference_audio.is_file():
        raise ValueError(f"reference audio not found: {reference_audio}")

    preferred_checkpoint = model_dir / "F5TTS_v1_Base" / "model_1250000.safetensors"
    checkpoints = sorted(model_dir.rglob("*.safetensors"))
    if not checkpoints:
        raise ValueError(f"F5-TTS checkpoint not found under: {model_dir}")
    checkpoint = (
        preferred_checkpoint
        if preferred_checkpoint.is_file()
        else next(
            (path for path in checkpoints if (path.parent / "vocab.txt").is_file()),
            checkpoints[-1],
        )
    )
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

    output_path.parent.mkdir(parents=True, exist_ok=True)
    engine = F5TTS(
        model="F5TTS_v1_Base",
        ckpt_file=str(checkpoint),
        vocab_file=str(vocab),
        vocoder_local_path=str(vocoder_dir),
        device=None if args.device == "auto" else args.device,
    )
    engine.infer(
        ref_file=str(reference_audio),
        ref_text=args.reference_text,
        gen_text=args.text,
        file_wave=str(output_path),
        speed=args.speed,
    )
    if not output_path.is_file():
        raise RuntimeError(f"F5-TTS did not create output audio: {output_path}")


def load_engine_command_json(args: argparse.Namespace) -> str | None:
    if args.engine_command_json and args.engine_command_json_file:
        raise SystemExit("Use only one of --engine-command-json or --engine-command-json-file")
    if args.engine_command_json_file:
        return Path(args.engine_command_json_file).read_text(encoding="utf-8")
    return args.engine_command_json


def render_engine_command(raw_json: str, args: argparse.Namespace) -> list[str]:
    raw_command = json.loads(raw_json)
    if not isinstance(raw_command, list) or not raw_command:
        raise SystemExit("--engine-command-json must be a non-empty JSON array")

    values: dict[str, Any] = {
        "text": args.text,
        "speaker": args.speaker,
        "audio_out": args.audio_out,
        "audio_out_dir": str(Path(args.audio_out).parent),
        "audio_out_name": Path(args.audio_out).name,
        "json_out": args.json_out,
        "reference_audio": args.reference_audio or "",
        "reference_text": args.reference_text,
        "style_prompt": args.style_prompt,
        "duration_ms": args.duration_ms,
        "speed": args.speed,
    }
    return [str(item).format(**values) for item in raw_command]


def run_f5_tts_with_retries(command: list[str], expected_output: Path) -> bool:
    """Run F5-TTS via subprocess with limited retries.

    The subprocess uses _f5_tts_runner.py which mocks out the training-only
    modules (trainer/dataset) to avoid the pyarrow/arrow.dll crash, and
    patches torchaudio.load to use soundfile. With these patches the crash
    should not occur, so we keep retries minimal (2 attempts) to avoid
    wasting GPU resources if something else goes wrong.
    """
    import time

    for attempt in range(2):
        if try_subprocess(command, expected_output):
            if expected_output.is_file():
                return True
        # Clean up partial output before retry
        if expected_output.is_file():
            expected_output.unlink(missing_ok=True)
        # Brief delay before retry to let GPU state settle
        if attempt < 1:
            time.sleep(2)
    return False


def try_subprocess(command: list[str], expected_output: Path) -> bool:
    """Run TTS engine via subprocess.

    For F5-TTS CLI commands (starting with "f5-tts_infer-cli"), uses
    _f5_tts_runner.py wrapper which mocks training-only modules (trainer/dataset)
    to avoid the pyarrow/arrow.dll crash, and patches torchaudio.load to use
    soundfile.

    For other engine commands (e.g. custom Python scripts), executes directly.

    A timeout (300s) is enforced to prevent the subprocess from hanging
    indefinitely and wasting GPU resources. Output is redirected to a log
    file to avoid pipe buffer deadlock with the parent process.
    """
    log_dir = expected_output.parent / "tts_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / (expected_output.stem + ".log")

    if command and command[0] == "f5-tts_infer-cli":
        # F5-TTS CLI: use wrapper script with mock/patch
        runner_script = str(Path(__file__).parent / "_f5_tts_runner.py")
        full_command = [sys.executable, runner_script, "--", *command[1:]]
    else:
        # Other engine commands (custom scripts): execute directly
        full_command = command

    try:
        with open(log_file, "w", encoding="utf-8") as log_fh:
            result = subprocess.run(
                full_command,
                check=False,
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                timeout=300,
            )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        return False
    except (OSError, subprocess.SubprocessError):
        return False


def write_silent_wav(output_path: Path, *, duration_ms: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 16000
    sample_count = int(sample_rate * (duration_ms / 1000))
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * sample_count)


def write_contract(output_path: Path, audio_path: Path, duration_ms: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "audio_path": str(audio_path),
                "duration_ms": duration_ms,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def wav_duration_ms(path: Path) -> int:
    with wave.open(str(path), "rb") as wav_file:
        return round(wav_file.getnframes() / wav_file.getframerate() * 1000)


if __name__ == "__main__":
    raise SystemExit(main())
