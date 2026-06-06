from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


APP_NAME = "IntelligentVoiceOver"
VERSION_FILE = Path("src") / "ivo" / "__init__.py"


def build_command(output_dir: Path, *, ffmpeg_dir: Path | None = None) -> list[str]:
    root = Path.cwd()
    command = [
        "uv",
        "run",
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--name",
        APP_NAME,
        "--windowed",
        "--paths",
        str(root / "src"),
        "--distpath",
        str(output_dir),
        "--workpath",
        str(output_dir / "build"),
        "--specpath",
        str(output_dir / "spec"),
        "--collect-all",
        "PySide6",
        "--add-data",
        f"{root / 'examples'};examples",
        "--add-data",
        f"{root / 'docs'};docs",
    ]
    if ffmpeg_dir is not None:
        command.extend(["--add-data", f"{ffmpeg_dir};ffmpeg"])
    command.append(str(root / "scripts" / "windows_desktop_entry.py"))
    return command


def release_manifest_path(output_dir: Path) -> Path:
    return output_dir / APP_NAME / "release-manifest.json"


def build_release_manifest(
    output_dir: Path,
    *,
    ffmpeg_dir: Path | None = None,
) -> dict[str, object]:
    included_data = ["examples", "docs"]
    if ffmpeg_dir is not None:
        included_data.append("ffmpeg")
    return {
        "name": APP_NAME,
        "version": read_project_version(),
        "entrypoint": str(output_dir / APP_NAME / f"{APP_NAME}.exe"),
        "included_data": included_data,
        "excluded_paths": [
            "models",
            "测试视频",
            "sample_media",
            "scratch",
            "runs",
            ".ivo-work",
            "*.mp4",
            "*.wav",
            ".env",
        ],
        "excluded_secrets": ["API keys and tokens", "HF_TOKEN", "ModelScope token"],
        "notes": [
            "Model weights are not bundled.",
            "Unauthorized media is not bundled.",
            (
                f"FFmpeg is bundled from {ffmpeg_dir}."
                if ffmpeg_dir is not None
                else "FFmpeg is not bundled for this build."
            ),
            "Local model runtimes and model weights must be installed on the target machine.",
        ],
    }


def discover_ffmpeg_dir(configured_dir: Path | None = None) -> Path | None:
    for candidate in (configured_dir, _env_ffmpeg_dir()):
        if candidate is not None:
            resolved = candidate.resolve()
            if _has_ffmpeg_binaries(resolved):
                return resolved

    if not sys.platform.startswith("win"):
        return None

    executable = shutil.which("ffmpeg")
    if executable is None:
        return None
    executable_dir = Path(executable).resolve().parent
    root = executable_dir.parent if executable_dir.name.lower() == "bin" else executable_dir
    if _has_ffmpeg_binaries(root):
        return root
    return None


def _env_ffmpeg_dir() -> Path | None:
    configured = os.getenv("IVO_FFMPEG_DIR")
    return Path(configured) if configured else None


def _has_ffmpeg_binaries(ffmpeg_dir: Path) -> bool:
    return any(
        (ffmpeg_dir / relative).is_file()
        for relative in (
            Path("bin") / "ffmpeg.exe",
            Path("bin") / "ffmpeg",
            Path("ffmpeg.exe"),
            Path("ffmpeg"),
        )
    )


def read_project_version(version_file: Path = VERSION_FILE) -> str:
    for line in version_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("__version__"):
            _name, _separator, raw_value = line.partition("=")
            return raw_value.strip().strip("\"'")
    raise RuntimeError(f"Cannot find __version__ in {version_file}")


def write_release_manifest(output_dir: Path, *, ffmpeg_dir: Path | None = None) -> Path:
    manifest_path = release_manifest_path(output_dir)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            build_release_manifest(output_dir, ffmpeg_dir=ffmpeg_dir),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Windows desktop package.")
    parser.add_argument("--output-dir", default="dist", type=Path)
    parser.add_argument("--ffmpeg-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ffmpeg_dir = discover_ffmpeg_dir(args.ffmpeg_dir)
    if not args.dry_run and ffmpeg_dir is None:
        parser.error(
            "FFmpeg directory was not found. Pass --ffmpeg-dir or set IVO_FFMPEG_DIR "
            "so the Windows package can bundle FFmpeg."
        )

    command = build_command(args.output_dir, ffmpeg_dir=ffmpeg_dir)
    if args.dry_run:
        print(
            json.dumps(
                {
                    "command": command,
                    "manifest_path": str(release_manifest_path(args.output_dir)),
                    "manifest": build_release_manifest(args.output_dir, ffmpeg_dir=ffmpeg_dir),
                },
                ensure_ascii=False,
            )
        )
        return 0

    subprocess.run(command, check=True)
    manifest_path = write_release_manifest(args.output_dir, ffmpeg_dir=ffmpeg_dir)
    print(f"Release manifest written: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
