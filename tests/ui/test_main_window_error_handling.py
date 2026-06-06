from __future__ import annotations


def test_main_window_warns_when_local_preview_worker_fails(monkeypatch, qtbot) -> None:
    from ivo.ui.main_window import MainWindow

    warnings: list[tuple[str, str]] = []

    def fake_warning(parent, title: str, message: str):
        warnings.append((title, message))

    monkeypatch.setattr("ivo.ui.main_window.QMessageBox.warning", fake_warning)

    window = MainWindow()
    qtbot.addWidget(window)
    window.local_preview_button.setEnabled(False)

    window.handle_local_preview_failed("provider busy")

    assert window.local_preview_button.isEnabled() is True
    assert warnings == [("本地命令预览失败", "provider busy")]
    assert "provider busy" in window.progress_label.text()
    assert "provider busy" in window.run_log_panel.plain_text()


def test_run_log_panel_formats_adapter_error(qtbot) -> None:
    from ivo.adapters.base import AdapterError
    from ivo.ui.run_log import RunLogPanel

    panel = RunLogPanel()
    qtbot.addWidget(panel)

    panel.append_adapter_error(
        AdapterError(
            provider="broken-tts",
            stage="tts",
            message="local command failed",
            command=["python", "tts.py"],
            exit_code=1,
            stderr_summary="model missing",
            output_json_path="tts.json",
        )
    )

    text = panel.plain_text()
    assert "tts" in text
    assert "broken-tts" in text
    assert "退出码：1" in text
    assert "命令：python tts.py" in text
    assert "python tts.py" in text
    assert "model missing" in text


def test_readiness_worker_runs_local_profile_check(monkeypatch, tmp_path) -> None:
    from ivo.local_readiness import LocalReadinessReport
    from ivo.ui.workers import ReadinessWorker

    profiles_path = tmp_path / "profiles.json"
    models_dir = tmp_path / "models"
    captured: dict[str, object] = {}
    expected = LocalReadinessReport(
        ok=True,
        checked_profiles=["tts:f5"],
        skipped_dry_run_profiles=[],
        missing=[],
    )

    def fake_check_profiles_readiness(raw_profiles_path, *, models_dir):
        captured["profiles_path"] = raw_profiles_path
        captured["models_dir"] = models_dir
        return expected

    monkeypatch.setattr("ivo.ui.workers.check_profiles_readiness", fake_check_profiles_readiness)

    worker = ReadinessWorker(profiles_path, models_dir=models_dir)
    worker.run()

    assert worker.result == expected
    assert captured == {"profiles_path": profiles_path, "models_dir": models_dir}
