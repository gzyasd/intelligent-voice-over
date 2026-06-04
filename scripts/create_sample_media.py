from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


SAMPLES = [
    ("en_synthetic_1min.mp4", 440),
    ("ja_synthetic_1min.mp4", 554),
    ("ko_synthetic_1min.mp4", 659),
    ("multi_speaker_synthetic_1min.mp4", 880),
]


def build_ffmpeg_commands(output_dir: Path, *, ffmpeg: str = "ffmpeg") -> list[list[str]]:
    return [
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=1280x720:rate=24:duration=60",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={frequency}:duration=60",
            "-shortest",
            str(output_dir / filename).replace("\\", "/"),
        ]
        for filename, frequency in SAMPLES
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create authorized synthetic sample media.")
    parser.add_argument("--output-dir", default="sample_media", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    commands = build_ffmpeg_commands(args.output_dir, ffmpeg=args.ffmpeg)
    outputs = [command[-1] for command in commands]
    payload = {
        "commands": commands,
        "outputs": outputs,
        "note": "Generated files are authorized synthetic media for workflow testing only.",
    }
    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False))
        return 0

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for command in commands:
        subprocess.run(command, check=True)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
