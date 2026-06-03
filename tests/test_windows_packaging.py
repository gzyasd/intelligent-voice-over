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


def test_windows_packaging_documentation_mentions_build_command() -> None:
    document = Path("docs/windows-packaging.md").read_text(encoding="utf-8")

    assert "scripts/build_windows_package.py" in document
    assert "uv tool run pyinstaller" in document
    assert "ffmpeg" in document.lower()
    assert "IntelligentVoiceOver.exe" in document
    assert "模型权重不会被打包" in document
    assert "未授权" in document
    assert "GitHub Release" in document
