from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


APP_NAME = "IntelligentVoiceOver"
VERSION_FILE = Path("src") / "ivo" / "__init__.py"


def build_command(output_dir: Path) -> list[str]:
    return [
        "uv",
        "tool",
        "run",
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--name",
        APP_NAME,
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


def release_manifest_path(output_dir: Path) -> Path:
    return output_dir / APP_NAME / "release-manifest.json"


def build_release_manifest(output_dir: Path) -> dict[str, object]:
    return {
        "name": APP_NAME,
        "version": read_project_version(),
        "entrypoint": str(output_dir / APP_NAME / f"{APP_NAME}.exe"),
        "included_data": ["examples", "docs"],
        "excluded_paths": [
            "models",
            "测试视频",
            "sample_media",
            "scratch",
            "*.mp4",
            "*.wav",
            ".env",
        ],
        "excluded_secrets": ["API keys and tokens", "HF_TOKEN", "ModelScope token"],
        "notes": [
            "Model weights are not bundled.",
            "Unauthorized media is not bundled.",
            "FFmpeg and local model runtimes must be installed on the target machine.",
        ],
    }


def read_project_version(version_file: Path = VERSION_FILE) -> str:
    for line in version_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            _name, _separator, raw_value = line.partition("=")
            return raw_value.strip().strip("\"'")
    raise RuntimeError(f"Cannot find __version__ in {version_file}")


def write_release_manifest(output_dir: Path) -> Path:
    manifest_path = release_manifest_path(output_dir)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(build_release_manifest(output_dir), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Windows desktop package.")
    parser.add_argument("--output-dir", default="dist", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    command = build_command(args.output_dir)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "command": command,
                    "manifest_path": str(release_manifest_path(args.output_dir)),
                    "manifest": build_release_manifest(args.output_dir),
                },
                ensure_ascii=False,
            )
        )
        return 0

    subprocess.run(command, check=True)
    manifest_path = write_release_manifest(args.output_dir)
    print(f"Release manifest written: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
