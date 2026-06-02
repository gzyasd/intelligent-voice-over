from __future__ import annotations


def test_main_window_opens_export_dialog_and_starts_background_export(
    monkeypatch,
    qtbot,
    tmp_path,
) -> None:
    from PySide6.QtWidgets import QDialog

    from ivo.core.project import DubbingProject
    from ivo.ui.export_dialog import ExportDialog
    from ivo.ui.main_window import MainWindow

    source_video = tmp_path / "episode.mp4"
    source_video.write_bytes(b"video")
    project = DubbingProject.create(
        tmp_path / "Episode 01.ivoproj",
        name="Episode 01",
        source_language="en",
        target_language="zh",
        source_video=source_video,
    )
    (project.path / "work" / "background.wav").write_bytes(b"background")

    class AcceptedExportDialog(ExportDialog):
        def __init__(self, parent=None) -> None:
            super().__init__(parent)
            self.output_path_edit.setText(str(tmp_path / "final.mp4"))
            self.confirmation_checkbox.setChecked(True)

        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

    captured: dict[str, object] = {}
    fake_worker = object()

    monkeypatch.setattr("ivo.ui.main_window.ExportDialog", AcceptedExportDialog)

    window = MainWindow()
    qtbot.addWidget(window)
    window.current_project = project
    window.source_video_path = source_video

    def fake_start_final_export_background(dialog):
        captured["dialog"] = dialog
        window.progress_label.setText("\u6b63\u5728\u6700\u7ec8\u5bfc\u51fa")
        window.export_button.setEnabled(False)
        return fake_worker

    monkeypatch.setattr(window, "start_final_export_background", fake_start_final_export_background)

    worker = window.open_export_dialog()

    assert worker is fake_worker
    assert captured["dialog"].output_path() == tmp_path / "final.mp4"
    assert window.export_button.isEnabled() is False
    assert window.progress_label.text() == "\u6b63\u5728\u6700\u7ec8\u5bfc\u51fa"


def test_main_window_warns_when_export_dialog_is_incomplete(monkeypatch, qtbot) -> None:
    from PySide6.QtWidgets import QDialog

    from ivo.ui.export_dialog import ExportDialog
    from ivo.ui.main_window import MainWindow

    warnings: list[tuple[str, str]] = []

    class IncompleteExportDialog(ExportDialog):
        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr("ivo.ui.main_window.ExportDialog", IncompleteExportDialog)
    monkeypatch.setattr(
        "ivo.ui.main_window.QMessageBox.warning",
        lambda parent, title, message: warnings.append((title, message)),
    )

    window = MainWindow()
    qtbot.addWidget(window)

    output = window.open_export_dialog()

    assert output is None
    assert warnings == [
        (
            "\u6700\u7ec8\u5bfc\u51fa\u5931\u8d25",
            "\u8bf7\u586b\u5199\u5bfc\u51fa\u8def\u5f84\u5e76\u786e\u8ba4\u7d20\u6750\u5904\u7406\u6743\u5229\u3002",
        )
    ]


def test_main_window_warns_when_final_export_worker_fails(monkeypatch, qtbot) -> None:
    from ivo.ui.main_window import MainWindow

    warnings: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "ivo.ui.main_window.QMessageBox.warning",
        lambda parent, title, message: warnings.append((title, message)),
    )

    window = MainWindow()
    qtbot.addWidget(window)
    window.export_button.setEnabled(False)

    window.handle_final_export_failed("ffmpeg failed")

    assert window.export_button.isEnabled() is True
    assert warnings == [("\u6700\u7ec8\u5bfc\u51fa\u5931\u8d25", "ffmpeg failed")]
    assert "ffmpeg failed" in window.progress_label.text()
