from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    source = Path(args.audio)
    if not source.is_file():
        raise FileNotFoundError(source)

    Path(args.out).write_text(
        json.dumps(
            {
                "segments": [
                    {
                        "start_ms": 0,
                        "end_ms": 1200,
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
