from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    if not Path(args.audio).is_file():
        raise FileNotFoundError(args.audio)

    Path(args.out).write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "id": "seg-001",
                        "start_ms": 100,
                        "end_ms": 1100,
                        "text": "Well, hi.",
                        "speaker_id": "speaker-1",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
