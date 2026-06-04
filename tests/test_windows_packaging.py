from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_windows_package_script_dry_run_outputs_pyinstaller_command() -> None:
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
    )

    payload = json.loads(result.stdout)
    command = payload["command"]
    manifest = payload["manifest"]

    assert command[:3] == ["uv", "tool", "run"]
    assert "pyinstaller" in command
    assert "--name" in command
    assert "IntelligentVoiceOver" in command
    assert "--windowed" in command
    assert "--paths" in command
    assert "src" in command
    assert "--collect-all" in command
    assert "PySide6" in command
    assert "--add-data" in command
    assert "examples;examples" in command
    assert "docs;docs" in command
    assert command[-1] == "scripts/windows_desktop_entry.py"
    assert manifest["name"] == "IntelligentVoiceOver"
    assert manifest["version"] == "0.1.0"
    assert manifest["entrypoint"].endswith("IntelligentVoiceOver.exe")
    assert "examples" in manifest["included_data"]
    assert "docs" in manifest["included_data"]
    assert "models" in manifest["excluded_paths"]
    assert "sample_media" in manifest["excluded_paths"]
    assert "API keys and tokens" in manifest["excluded_secrets"]


def test_windows_packaging_documentation_mentions_build_command() -> None:
    document = Path("docs/windows-packaging.md").read_text(encoding="utf-8")

    assert "scripts/build_windows_package.py" in document
    assert "uv tool run pyinstaller" in document
    assert "ffmpeg" in document.lower()
    assert "IntelligentVoiceOver.exe" in document
    assert "release-manifest.json" in document
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
