from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", required=True)
    parser.add_argument("--vocals-out", required=True)
    parser.add_argument("--background-out", required=True)
    parser.add_argument("--json-out", required=True)
    args = parser.parse_args()

    source = Path(args.audio)
    if not source.is_file():
        raise FileNotFoundError(source)

    vocals = Path(args.vocals_out)
    background = Path(args.background_out)
    vocals.parent.mkdir(parents=True, exist_ok=True)
    background.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, vocals)
    shutil.copy2(source, background)

    Path(args.json_out).write_text(
        json.dumps(
            {
                "vocals_path": str(vocals),
                "background_path": str(background),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
