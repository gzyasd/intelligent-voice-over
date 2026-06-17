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
    assert warnings == [("生成配音失败", "provider busy")]
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


def test_main_window_warns_when_evaluation_has_no_project(monkeypatch, qtbot) -> None:
    from ivo.ui.main_window import MainWindow

    warnings: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "ivo.ui.main_window.QMessageBox.warning",
        lambda parent, title, message: warnings.append((title, message)),
    )
    window = MainWindow()
    qtbot.addWidget(window)

    result = window.open_evaluation_report()

    assert result is None
    assert warnings == [("生成评估报告失败", "请先创建或打开项目")]


def test_main_window_warns_when_start_generation_has_no_project(monkeypatch, qtbot) -> None:
    from ivo.ui.main_window import MainWindow

    warnings: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "ivo.ui.main_window.QMessageBox.warning",
        lambda parent, title, message: warnings.append((title, message)),
    )
    window = MainWindow()
    qtbot.addWidget(window)

    result = window.request_local_preview()

    assert result is None
    assert warnings == [("无法开始生成", "请先在首页新建项目或从项目库打开已有项目，然后再开始生成配音。")]
    assert window.progress_label.text() == "请先在首页新建项目或从项目库打开已有项目，然后再开始生成配音。"


def test_main_window_warns_when_export_has_no_project(monkeypatch, qtbot) -> None:
    from ivo.ui.main_window import MainWindow

    warnings: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "ivo.ui.main_window.QMessageBox.warning",
        lambda parent, title, message: warnings.append((title, message)),
    )
    window = MainWindow()
    qtbot.addWidget(window)

    result = window.open_export_dialog()

    assert result is None
    assert warnings == [("无法导出", "请先在首页新建项目或从项目库打开已有项目，然后再导出。")]
    assert window.progress_label.text() == "请先在首页新建项目或从项目库打开已有项目，然后再导出。"


def test_run_log_panel_copy_uses_full_command_log(monkeypatch, qtbot) -> None:
    from ivo.adapters.local import CommandExecutionLog
    from ivo.ui.run_log import RunLogPanel

    copied: dict[str, str] = {}

    class FakeClipboard:
        def setText(self, text: str) -> None:
            copied["text"] = text

    monkeypatch.setattr(
        "ivo.ui.run_log.QApplication.clipboard",
        lambda: FakeClipboard(),
    )

    panel = RunLogPanel()
    qtbot.addWidget(panel)
    panel.append_command_output(
        CommandExecutionLog(
            stage="diarization",
            provider="pyannote-community-1-local",
            command=["python", "pyannote_diarization.py"],
            stderr=(
                "torchcodec is not installed correctly so built-in audio decoding will fail.\n"
                "Traceback (most recent call last):\n"
                "FileNotFoundError: libtorchcodec_core8.dll"
            ),
            exit_code=0,
        )
    )

    assert "Traceback" not in panel.plain_text()

    panel.copy_log()

    assert "Traceback (most recent call last):" in copied["text"]
    assert "libtorchcodec_core8.dll" in copied["text"]


def test_run_log_panel_can_hide_warning_logs(qtbot) -> None:
    from ivo.adapters.local import CommandExecutionLog
    from ivo.ui.run_log import RunLogPanel

    panel = RunLogPanel()
    qtbot.addWidget(panel)
    panel.append_stage_message("import", "开始导入", level="info")
    panel.append_command_output(
        CommandExecutionLog(
            stage="tts",
            provider="f5",
            command=["python", "tts.py"],
            stderr="FutureWarning: Python 3.10 support will stop later",
            exit_code=0,
        )
    )
    panel.append_stage_message("tts", "真正失败", level="error")

    assert "开始导入" in panel.plain_text()
    assert "命令警告" in panel.plain_text()
    assert "真正失败" in panel.plain_text()

    panel.show_warning_checkbox.setChecked(False)

    assert "开始导入" in panel.plain_text()
    assert "命令警告" not in panel.plain_text()
    assert "真正失败" in panel.plain_text()

    panel.error_only_checkbox.setChecked(True)

    assert "开始导入" not in panel.plain_text()
    assert "命令警告" not in panel.plain_text()
    assert "真正失败" in panel.plain_text()
