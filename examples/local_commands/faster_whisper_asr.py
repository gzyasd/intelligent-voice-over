from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="ASR command adapter for faster-whisper.")
    parser.add_argument("--audio", required=True)
    parser.add_argument("--language", required=True, choices=["en", "ja", "ko"])
    parser.add_argument("--model", default="base")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--compute-type", default="float16")
    parser.add_argument("--out", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    audio = Path(args.audio)
    if not audio.is_file():
        raise FileNotFoundError(audio)

    if args.dry_run:
        write_contract(
            Path(args.out),
            [
                {
                    "id": "seg-001",
                    "start_ms": 100,
                    "end_ms": 1100,
                    "text": "Well, hi.",
                    "speaker_id": "speaker-1",
                }
            ],
        )
        return 0

    try:
        from faster_whisper import WhisperModel  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: faster-whisper. Install it in the command environment before "
            "running this adapter, for example: uv pip install faster-whisper"
        ) from exc

    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    segments, _info = model.transcribe(str(audio), language=args.language, vad_filter=True)
    payload: list[dict[str, Any]] = []
    for index, segment in enumerate(segments, start=1):
        payload.append(
            {
                "id": f"seg-{index:03d}",
                "start_ms": int(segment.start * 1000),
                "end_ms": int(segment.end * 1000),
                "text": segment.text.strip(),
                "speaker_id": "unknown",
            }
        )
    write_contract(Path(args.out), payload)
    return 0


def write_contract(output_path: Path, segments: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"segments": segments}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
