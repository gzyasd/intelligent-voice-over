from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="TTS command adapter skeleton for F5-TTS.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--speaker", required=True)
    parser.add_argument("--audio-out", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--reference-audio")
    parser.add_argument("--reference-text", default="")
    parser.add_argument("--style-prompt", default="")
    parser.add_argument("--duration-ms", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    audio_path = Path(args.audio_out)
    if args.dry_run:
        write_silent_wav(audio_path, duration_ms=args.duration_ms)
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
