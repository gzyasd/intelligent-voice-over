from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def build_command(output_dir: Path) -> list[str]:
    return [
        "uv",
        "tool",
        "run",
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--name",
        "IntelligentVoiceOver",
        "--windowed",
        "--paths",
        "src",
        "--distpath",
        str(output_dir),
        "--workpath",
        str(output_dir / "build"),
        "--specpath",
        str(output_dir / "spec"),
        "--collect-all",
        "PySide6",
        "--add-data",
        "examples;examples",
        "--add-data",
        "docs;docs",
        "scripts/windows_desktop_entry.py",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Windows desktop package.")
    parser.add_argument("--output-dir", default="dist", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    command = build_command(args.output_dir)
    if args.dry_run:
        print(json.dumps({"command": command}, ensure_ascii=False))
        return 0

    subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
