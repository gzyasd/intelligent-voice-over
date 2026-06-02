from __future__ import annotations


def test_main_window_opens_wizard_and_creates_project(monkeypatch, qtbot, tmp_path) -> None:
    from PySide6.QtWidgets import QDialog

    from ivo.ui.project_wizard import ProjectWizard
    from ivo.ui.main_window import MainWindow

    source_video = tmp_path / "episode.mp4"
    source_video.write_bytes(b"video")
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    class AcceptedWizard(ProjectWizard):
        def __init__(self, parent=None) -> None:
            super().__init__(parent)
            self.project_name_edit.setText("Episode 01")
            self.video_path_edit.setText(str(source_video))
            self.output_dir_edit.setText(str(output_dir))
            self.source_language_combo.setCurrentText("ko")

        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr("ivo.ui.main_window.ProjectWizard", AcceptedWizard)

    window = MainWindow()
    qtbot.addWidget(window)

    project = window.open_project_wizard()

    assert project is not None
    assert project.path == output_dir / "Episode 01.ivoproj"
    assert project.source_language == "ko"
    assert window.source_video_path == source_video
    assert window.progress_label.text() == "项目已创建"


def test_main_window_warns_when_wizard_input_is_invalid(monkeypatch, qtbot) -> None:
    from PySide6.QtWidgets import QDialog

    from ivo.ui.project_wizard import ProjectWizard
    from ivo.ui.main_window import MainWindow

    warnings: list[tuple[str, str]] = []

    class InvalidWizard(ProjectWizard):
        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

    def fake_warning(parent, title: str, message: str) -> None:
        warnings.append((title, message))

    monkeypatch.setattr("ivo.ui.main_window.ProjectWizard", InvalidWizard)
    monkeypatch.setattr("ivo.ui.main_window.QMessageBox.warning", fake_warning)

    window = MainWindow()
    qtbot.addWidget(window)

    project = window.open_project_wizard()

    assert project is None
    assert warnings == [("新建项目失败", "请填写项目名称、源视频和输出目录。")]
