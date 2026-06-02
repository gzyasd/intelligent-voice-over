from __future__ import annotations


def test_main_window_opens_export_dialog_and_runs_export(monkeypatch, qtbot, tmp_path) -> None:
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

    def fake_export_dubbed_video(request, confirmation):
        request.output_path.write_bytes(b"final")
        return request.output_path

    monkeypatch.setattr("ivo.ui.main_window.ExportDialog", AcceptedExportDialog)
    monkeypatch.setattr("ivo.ui.main_window.export_dubbed_video", fake_export_dubbed_video)

    window = MainWindow()
    qtbot.addWidget(window)
    window.current_project = project
    window.source_video_path = source_video

    output = window.open_export_dialog()

    assert output is not None
    assert output.read_bytes() == b"final"
    assert window.progress_label.text() == "最终导出已完成"


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
    assert warnings == [("最终导出失败", "请填写导出路径并确认素材处理权利。")]


def test_main_window_warns_when_final_export_fails(monkeypatch, qtbot, tmp_path) -> None:
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
    warnings: list[tuple[str, str]] = []

    class AcceptedExportDialog(ExportDialog):
        def __init__(self, parent=None) -> None:
            super().__init__(parent)
            self.output_path_edit.setText(str(tmp_path / "final.mp4"))
            self.confirmation_checkbox.setChecked(True)

        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

    def fake_export_dubbed_video(request, confirmation):
        raise RuntimeError("ffmpeg failed")

    monkeypatch.setattr("ivo.ui.main_window.ExportDialog", AcceptedExportDialog)
    monkeypatch.setattr("ivo.ui.main_window.export_dubbed_video", fake_export_dubbed_video)
    monkeypatch.setattr(
        "ivo.ui.main_window.QMessageBox.warning",
        lambda parent, title, message: warnings.append((title, message)),
    )

    window = MainWindow()
    qtbot.addWidget(window)
    window.current_project = project
    window.source_video_path = source_video

    output = window.open_export_dialog()

    assert output is None
    assert warnings == [("最终导出失败", "ffmpeg failed")]
    assert "ffmpeg failed" in window.progress_label.text()
