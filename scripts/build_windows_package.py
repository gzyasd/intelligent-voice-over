"""Build the Windows desktop package.

.. deprecated::
    此脚本为旧版 PySide6 打包流程，已被 electron-builder + PyInstaller 工作流取代。
    新项目请使用 `pnpm run build:win` / `build:mac` / `build:linux`。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import warnings
import zipfile
from pathlib import Path

warnings.warn(
    "scripts/build_windows_package.py is deprecated. Use 'pnpm run build:win/mac/linux' instead.",
    DeprecationWarning,
    stacklevel=2,
)


APP_NAME = "IntelligentVoiceOver"
VERSION_FILE = Path("src") / "ivo" / "__init__.py"
LOCAL_RUNTIME_DIRS = (".venv", ".venv-pyannote")

# Fallback search paths for runtime dirs that don't exist at project root.
_WORKTREE_BASE = Path(__file__).resolve().parent.parent / ".worktrees"


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


def portable_archive_path(output_dir: Path) -> Path:
    return output_dir / f"{APP_NAME}-{read_project_version()}-win64-portable.zip"


def build_release_manifest(
    output_dir: Path,
    *,
    ffmpeg_dir: Path | None = None,
    include_local_runtimes: bool = True,
) -> dict[str, object]:
    included_data = ["examples", "docs"]
    if ffmpeg_dir is not None:
        included_data.append("ffmpeg")
    if include_local_runtimes:
        included_data.extend(LOCAL_RUNTIME_DIRS)
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
            (
                "Local model Python runtimes are bundled; model weights must be placed in "
                "the app models directory or selected in the UI."
                if include_local_runtimes
                else "Local model runtimes and model weights must be installed on the target machine."
            ),
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


def write_release_manifest(
    output_dir: Path,
    *,
    ffmpeg_dir: Path | None = None,
    include_local_runtimes: bool = True,
) -> Path:
    manifest_path = release_manifest_path(output_dir)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            build_release_manifest(
                output_dir,
                ffmpeg_dir=ffmpeg_dir,
                include_local_runtimes=include_local_runtimes,
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return manifest_path


def write_portable_readme(output_dir: Path) -> Path:
    app_dir = output_dir / APP_NAME
    readme_path = app_dir / "README_FIRST.txt"
    readme_path.write_text(
        "\n".join(
            [
                "Intelligent Voice Over Windows 便携版使用说明",
                "",
                "不要只复制 IntelligentVoiceOver.exe。",
                "本程序依赖同目录下的 _internal 文件夹，里面包含 Python、PySide6、FFmpeg 等运行时文件。",
                "",
                "正确使用方式：",
                "1. 解压整个 win64-portable.zip。",
                "2. 保持 IntelligentVoiceOver 文件夹结构完整。",
                "3. 双击 IntelligentVoiceOver\\IntelligentVoiceOver.exe 启动。",
                "",
                "本包已内置本地模型 Python 运行环境（.venv 和 .venv-pyannote）。",
                "模型权重不会内置在本包中，请把模型放到 IntelligentVoiceOver\\models，或在客户端中选择已有模型目录。",
                "GPU 驱动、CUDA 驱动组件、LM Studio 仍需在本机准备好。",
            ]
        ),
        encoding="utf-8",
    )
    return readme_path


def build_portable_archive(output_dir: Path) -> Path:
    app_dir = output_dir / APP_NAME
    if not app_dir.is_dir():
        raise FileNotFoundError(app_dir)
    archive_path = portable_archive_path(output_dir)
    if archive_path.exists():
        archive_path.unlink()
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(app_dir.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(output_dir).as_posix())
    return archive_path


def copy_portable_support_files(
    output_dir: Path,
    *,
    root: Path | None = None,
    include_local_runtimes: bool = True,
) -> list[Path]:
    project_root = root or Path.cwd()
    app_dir = output_dir / APP_NAME
    if not app_dir.is_dir():
        raise FileNotFoundError(app_dir)

    copied: list[Path] = []
    examples_source = project_root / "examples"
    if examples_source.is_dir():
        examples_target = app_dir / "examples"
        _replace_tree(examples_source, examples_target)
        copied.append(examples_target)

    if include_local_runtimes:
        for runtime_dir in LOCAL_RUNTIME_DIRS:
            source = project_root / runtime_dir
            # Fallback: look in any worktree directory
            if not source.is_dir() and _WORKTREE_BASE.is_dir():
                for wt in _WORKTREE_BASE.iterdir():
                    candidate = wt / runtime_dir
                    if candidate.is_dir():
                        source = candidate
                        print(f"[build] Found {runtime_dir} in worktree {wt.name}")
                        break
            if not source.is_dir():
                print(f"[build] Skipping {runtime_dir} (not found)")
                continue
            target = app_dir / runtime_dir
            _replace_tree(source, target)
            copied.append(target)
    return copied


def _replace_tree(source: Path, target: Path) -> None:
    if target.exists():
        _remove_tree_safe(target)
    shutil.copytree(source, target, ignore=_copy_ignore)


def _remove_tree_safe(target: Path) -> None:
    """Remove a directory tree."""
    shutil.rmtree(target, ignore_errors=True)


def _copy_ignore(directory: str, names: list[str]) -> set[str]:
    ignored_names = {
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".git",
        ".hg",
        ".svn",
    }
    return {
        name
        for name in names
        if name in ignored_names or name.endswith((".pyc", ".pyo"))
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Windows desktop package.")
    parser.add_argument("--output-dir", default="dist", type=Path)
    parser.add_argument("--ffmpeg-dir", type=Path)
    parser.add_argument(
        "--skip-local-runtimes",
        action="store_true",
        help="Do not copy .venv and .venv-pyannote into the portable package.",
    )
    parser.add_argument(
        "--create-archive",
        action="store_true",
        help="Create a portable zip archive after building the app directory.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ffmpeg_dir = discover_ffmpeg_dir(args.ffmpeg_dir)
    if not args.dry_run and ffmpeg_dir is None:
        parser.error(
            "FFmpeg directory was not found. Pass --ffmpeg-dir or set IVO_FFMPEG_DIR "
            "so the Windows package can bundle FFmpeg."
        )

    command = build_command(args.output_dir, ffmpeg_dir=ffmpeg_dir)
    include_local_runtimes = not args.skip_local_runtimes
    create_archive = args.create_archive
    if args.dry_run:
        print(
            json.dumps(
                {
                    "command": command,
                    "manifest_path": str(release_manifest_path(args.output_dir)),
                    "create_archive": create_archive,
                    "portable_archive_path": (
                        str(portable_archive_path(args.output_dir)) if create_archive else None
                    ),
                    "manifest": build_release_manifest(
                        args.output_dir,
                        ffmpeg_dir=ffmpeg_dir,
                        include_local_runtimes=include_local_runtimes,
                    ),
                },
                ensure_ascii=False,
            )
        )
        return 0

    # Move heavy runtime dirs out of old dist so COLLECT removal is fast.
    # rename() is O(1) regardless of directory size, avoiding the slow
    # recursive deletion of .venv-pyannote with its long-path files.
    moved_runtimes: dict[str, Path] = {}
    if not args.dry_run and include_local_runtimes:
        old_dist = args.output_dir / APP_NAME
        # Clean up any leftover _prev_* dirs from previous runs (non-blocking).
        for prev in old_dist.parent.glob("_prev_*"):
            if prev.is_dir():
                subprocess.Popen(
                    [sys.executable, "-c",
                     f"import shutil; shutil.rmtree(r'{prev}', ignore_errors=True)"],
                )
        for runtime_dir in LOCAL_RUNTIME_DIRS:
            old_runtime = old_dist / runtime_dir
            if old_runtime.is_dir():
                tmp = old_dist.parent / f"_prev_{runtime_dir}_{os.getpid()}"
                old_runtime.rename(tmp)
                moved_runtimes[runtime_dir] = tmp
                print(f"[build] Moved {runtime_dir} out of old dist")

    subprocess.run(command, check=True)
    copied_paths = copy_portable_support_files(
        args.output_dir,
        include_local_runtimes=include_local_runtimes,
    )

    # Clean up moved runtime dirs in background (non-blocking).
    for tmp_path in moved_runtimes.values():
        subprocess.Popen(
            [sys.executable, "-c",
             f"import shutil; shutil.rmtree(r'{tmp_path}', ignore_errors=True)"],
        )
    manifest_path = write_release_manifest(
        args.output_dir,
        ffmpeg_dir=ffmpeg_dir,
        include_local_runtimes=include_local_runtimes,
    )
    write_portable_readme(args.output_dir)
    for copied_path in copied_paths:
        print(f"Copied support files: {copied_path}")
    print(f"Release manifest written: {manifest_path}")
    if create_archive:
        archive_path = build_portable_archive(args.output_dir)
        print(f"Portable archive written: {archive_path}")
    else:
        print(f"Portable archive skipped: {portable_archive_path(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
