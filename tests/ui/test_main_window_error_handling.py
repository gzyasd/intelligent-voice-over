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
