from __future__ import annotations

import argparse
import json
import wave
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--speaker", required=True)
    parser.add_argument("--audio-out", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--duration-ms", type=int, default=1000)
    args = parser.parse_args()

    audio_path = Path(args.audio_out)
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 16000
    sample_count = int(sample_rate * (args.duration_ms / 1000))
    with wave.open(str(audio_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * sample_count)

    Path(args.json_out).write_text(
        json.dumps(
            {
                "audio_path": str(audio_path),
                "duration_ms": args.duration_ms,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
