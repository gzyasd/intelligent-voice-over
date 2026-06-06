from __future__ import annotations

import json
import os
import subprocess
import sys
import zipfile
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def load_windows_packager():
    spec = spec_from_file_location(
        "build_windows_package",
        Path("scripts") / "build_windows_package.py",
    )
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_windows_package_script_dry_run_outputs_pyinstaller_command(tmp_path) -> None:
    ffmpeg_root = tmp_path / "ffmpeg-8.1.1-full_build"
    ffmpeg_bin = ffmpeg_root / "bin"
    ffmpeg_bin.mkdir(parents=True)
    (ffmpeg_bin / "ffmpeg.exe").write_text("fake", encoding="utf-8")
    (ffmpeg_bin / "ffprobe.exe").write_text("fake", encoding="utf-8")
    env = {**os.environ, "IVO_FFMPEG_DIR": str(ffmpeg_root)}

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_windows_package.py",
            "--dry-run",
            "--output-dir",
            "dist-test",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)
    command = payload["command"]
    manifest = payload["manifest"]

    assert payload["portable_archive_path"].endswith("-win64-portable.zip")
    assert command[:3] == ["uv", "run", "pyinstaller"]
    assert "pyinstaller" in command
    assert "--name" in command
    assert "IntelligentVoiceOver" in command
    assert "--windowed" in command
    assert "--paths" in command
    paths_index = command.index("--paths")
    assert Path(command[paths_index + 1]).is_absolute()
    assert Path(command[paths_index + 1]).name == "src"
    assert "--collect-all" in command
    assert "PySide6" in command
    assert "--add-data" in command
    add_data_values = [
        command[index + 1]
        for index, item in enumerate(command)
        if item == "--add-data"
    ]
    assert any(
        value.endswith("examples;examples") and Path(value.split(";")[0]).is_absolute()
        for value in add_data_values
    )
    assert any(
        value.endswith("docs;docs") and Path(value.split(";")[0]).is_absolute()
        for value in add_data_values
    )
    assert any(
        value.split(";")[1] == "ffmpeg" and Path(value.split(";")[0]).is_absolute()
        for value in add_data_values
    )
    assert Path(command[-1]).is_absolute()
    assert Path(command[-1]).name == "windows_desktop_entry.py"
    assert manifest["name"] == "IntelligentVoiceOver"
    assert manifest["version"] == "0.1.0"
    assert manifest["entrypoint"].endswith("IntelligentVoiceOver.exe")
    assert "examples" in manifest["included_data"]
    assert "docs" in manifest["included_data"]
    assert "ffmpeg" in manifest["included_data"]
    assert "models" in manifest["excluded_paths"]
    assert "测试视频" in manifest["excluded_paths"]
    assert "sample_media" in manifest["excluded_paths"]
    assert "runs" in manifest["excluded_paths"]
    assert ".ivo-work" in manifest["excluded_paths"]
    assert "*.mp4" in manifest["excluded_paths"]
    assert "*.wav" in manifest["excluded_paths"]
    assert ".env" in manifest["excluded_paths"]
    assert "API keys and tokens" in manifest["excluded_secrets"]


def test_windows_package_archive_contains_whole_app_directory(tmp_path) -> None:
    packager = load_windows_packager()
    app_dir = tmp_path / "dist" / "IntelligentVoiceOver"
    internal = app_dir / "_internal"
    ffmpeg_bin = internal / "ffmpeg" / "bin"
    ffmpeg_bin.mkdir(parents=True)
    (app_dir / "IntelligentVoiceOver.exe").write_bytes(b"exe")
    (internal / "python310.dll").write_bytes(b"dll")
    (ffmpeg_bin / "ffmpeg.exe").write_bytes(b"ffmpeg")

    readme_path = packager.write_portable_readme(tmp_path / "dist")
    archive_path = packager.build_portable_archive(tmp_path / "dist")

    assert readme_path == app_dir / "README_FIRST.txt"
    assert "不要只复制" in readme_path.read_text(encoding="utf-8")
    with zipfile.ZipFile(archive_path) as archive:
        names = set(archive.namelist())

    assert "IntelligentVoiceOver/IntelligentVoiceOver.exe" in names
    assert "IntelligentVoiceOver/_internal/python310.dll" in names
    assert "IntelligentVoiceOver/_internal/ffmpeg/bin/ffmpeg.exe" in names
    assert "IntelligentVoiceOver/README_FIRST.txt" in names


def test_windows_package_powershell_script_excludes_models_and_media() -> None:
    text = Path("scripts/package-windows.ps1").read_text(encoding="utf-8")

    assert "models" in text
    assert "测试视频" in text
    assert "*.mp4" in text
    assert "*.wav" in text
    assert ".env" in text
    assert "pyinstaller" in text.lower()
    assert "uv run pytest" in text
    assert "uv run ruff check ." in text
    assert "uv run mypy src" in text


def test_windows_packaging_documentation_mentions_build_command() -> None:
    document = Path("docs/windows-packaging.md").read_text(encoding="utf-8")

    assert "scripts/build_windows_package.py" in document
    assert "scripts/package-windows.ps1" in document
    assert "uv run pyinstaller" in document
    assert "ffmpeg" in document.lower()
    assert "FFmpeg 已随发布包内置" in document
    assert "IntelligentVoiceOver.exe" in document
    assert "release-manifest.json" in document
    assert "win64-portable.zip" in document
    assert "模型权重不会被打包" in document
    assert "未授权" in document
    assert "GitHub Release" in document


def test_sample_media_script_dry_run_outputs_ffmpeg_commands() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "scripts/create_sample_media.py",
            "--dry-run",
            "--output-dir",
            "sample-media-test",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    commands = payload["commands"]
    outputs = payload["outputs"]

    assert len(commands) == 4
    assert all(command[0] == "ffmpeg" for command in commands)
    assert "sample-media-test/en_synthetic_1min.mp4" in outputs
    assert "sample-media-test/multi_speaker_synthetic_1min.mp4" in outputs
    assert "authorized synthetic media" in payload["note"]


def test_ci_runs_windows_package_dry_run() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "Build package dry-run" in workflow
    assert "scripts/build_windows_package.py --dry-run" in workflow
