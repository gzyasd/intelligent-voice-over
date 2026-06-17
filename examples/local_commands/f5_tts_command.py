from __future__ import annotations

import argparse
import json
import runpy
import subprocess
import sys
import wave
from pathlib import Path
from typing import Any


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
        if not run_f5_tts_cli_in_process(command):
            try:
                subprocess.run(command, check=True)
            except (OSError, subprocess.CalledProcessError) as exc:
                raise SystemExit(f"TTS engine command failed: {command}") from exc
        if not audio_path.is_file():
            raise SystemExit(f"TTS engine did not create audio output: {audio_path}")
        write_contract(Path(args.json_out), audio_path, args.duration_ms)
        return 0

    try:
        import f5_tts  # type: ignore[import-not-found]  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: F5-TTS. Install and expose your F5-TTS inference entrypoint, "
            "then replace this skeleton body with the project-specific call."
        ) from exc

    raise SystemExit(
        "F5-TTS package import succeeded, but this skeleton still needs the local model-specific "
        "inference call wired for your checkpoint and voice reference format."
    )


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
    }
    return [str(item).format(**values) for item in raw_command]


def run_f5_tts_cli_in_process(command: list[str]) -> bool:
    executable = Path(command[0]).name.lower()
    if executable not in {"f5-tts_infer-cli", "f5-tts_infer-cli.exe"}:
        return False

    import torchaudio

    original_argv = sys.argv[:]
    original_load = torchaudio.load
    try:
        sys.argv = ["f5-tts_infer-cli", *command[1:]]
        torchaudio.load = load_audio_with_soundfile
        runpy.run_module("f5_tts.infer.infer_cli", run_name="__main__")
    except SystemExit as exc:
        if exc.code not in (None, 0):
            raise
    finally:
        torchaudio.load = original_load
        sys.argv = original_argv
    return True


def load_audio_with_soundfile(
    uri: str | Path,
    frame_offset: int = 0,
    num_frames: int = -1,
    normalize: bool = True,
    channels_first: bool = True,
    format: str | None = None,
    buffer_size: int = 4096,
    backend: str | None = None,
) -> tuple[Any, int]:
    del normalize, format, buffer_size, backend

    import soundfile as sf
    import torch

    frames = -1 if num_frames is None or num_frames < 0 else num_frames
    data, sample_rate = sf.read(
        str(uri),
        start=frame_offset,
        frames=frames,
        dtype="float32",
        always_2d=True,
    )
    tensor = torch.from_numpy(data)
    if channels_first:
        tensor = tensor.transpose(0, 1).contiguous()
    return tensor, int(sample_rate)


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


if __name__ == "__main__":
    raise SystemExit(main())
