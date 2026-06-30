from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_legacy_pyside_packaging_files_are_removed() -> None:
    assert not Path("src/ivo/ui").exists()
    assert not Path("src/ivo/app.py").exists()
    assert not Path("scripts/build_windows_package.py").exists()
    assert not Path("scripts/windows_desktop_entry.py").exists()
    assert not Path("scripts/capture_project_library_screenshots.py").exists()


def test_python_dependencies_do_not_include_pyside_or_qt_test_stack() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "pyside6" not in pyproject.lower()
    assert "pytest-qt" not in pyproject.lower()


def test_windows_package_wrapper_uses_electron_build_flow() -> None:
    script = Path("scripts/package-windows.ps1").read_text(encoding="utf-8")

    assert "uv run pytest" in script
    assert "uv run ruff check ." in script
    assert "uv run mypy src server" in script
    assert "pnpm install --frozen-lockfile" in script
    assert "pnpm run typecheck" in script
    assert "pnpm run build:win" in script
    assert "build_windows_package.py" not in script


def test_ci_no_longer_installs_qt_or_runs_legacy_packager() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "QT_QPA_PLATFORM" not in workflow
    assert "Install Qt runtime dependencies" not in workflow
    assert "build_windows_package.py" not in workflow
    assert "from server.main import app" in workflow
    assert "pnpm run typecheck" in workflow
    assert "pnpm run build" in workflow


def test_pyinstaller_spec_uses_fastapi_server_entrypoint() -> None:
    spec = Path("scripts/build-python.spec").read_text(encoding="utf-8")

    assert "scripts' / 'ivo_server_entry.py'" in spec
    assert "collect_submodules('server')" in spec
    assert "collect_submodules('ivo')" in spec
    assert "'PySide6'" not in spec


def test_electron_builder_uses_current_build_artifacts() -> None:
    document = Path("electron-builder.yml").read_text(encoding="utf-8")

    assert "output: dist-installer" in document
    assert "- dist/renderer/index.html" in document
    assert "- dist/renderer/assets/**/*" in document
    assert "- from: dist/python" in document
    assert "dist3/" not in document


def test_packaged_window_loads_renderer_build() -> None:
    source = Path("electron/window-manager.ts").read_text(encoding="utf-8")

    assert "'dist', 'renderer', 'index.html'" in source


def test_frontend_can_recover_if_python_ready_event_was_sent_early() -> None:
    main_source = Path("electron/main.ts").read_text(encoding="utf-8")
    preload_source = Path("electron/preload.ts").read_text(encoding="utf-8")
    app_source = Path("src/App.vue").read_text(encoding="utf-8")

    assert "python-service:get-current" in main_source
    assert "getPythonServiceCurrent" in preload_source
    assert "getPythonServiceCurrent" in app_source


def test_python_service_startup_timeout_allows_pyinstaller_cold_start() -> None:
    source = Path("electron/python-service.ts").read_text(encoding="utf-8")

    assert "DEFAULT_HEALTH_CHECK_TIMEOUT_MS = 120000" in source
    assert "IVO_PYTHON_HEALTH_TIMEOUT_MS" in source


def test_packaged_python_service_uses_persistent_user_data_root() -> None:
    source = Path("electron/python-service.ts").read_text(encoding="utf-8")

    assert "IVO_USER_DATA_DIR" in source
    assert "app.getPath('userData')" in source


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
