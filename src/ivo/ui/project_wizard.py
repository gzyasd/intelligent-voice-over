from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ivo.core.timeline import SourceLanguage


class ProjectWizardValues(BaseModel):
    project_name: str
    source_video: Path
    output_dir: Path
    source_language: SourceLanguage
    processing_mode: str


class ProjectWizard(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("\u65b0\u5efa\u914d\u97f3\u9879\u76ee")

        self.project_name_edit = QLineEdit()
        self.video_path_edit = QLineEdit()
        self.video_browse_button = QPushButton("\u6d4f\u89c8\u89c6\u9891")
        self.output_dir_edit = QLineEdit()
        self.output_dir_browse_button = QPushButton("\u6d4f\u89c8\u8f93\u51fa\u76ee\u5f55")
        self.source_language_combo = QComboBox()
        self.source_language_combo.addItems(["en", "ja", "ko"])
        self.processing_mode_combo = QComboBox()
        self.processing_mode_combo.addItems(["fast_preview", "high_quality_export"])

        self.video_browse_button.clicked.connect(self.browse_video_file)
        self.output_dir_browse_button.clicked.connect(self.browse_output_dir)

        form = QFormLayout()
        form.addRow("\u9879\u76ee\u540d\u79f0", self.project_name_edit)
        form.addRow("\u6e90\u89c6\u9891", self.video_path_edit)
        form.addRow("", self.video_browse_button)
        form.addRow("\u8f93\u51fa\u76ee\u5f55", self.output_dir_edit)
        form.addRow("", self.output_dir_browse_button)
        form.addRow("\u6e90\u8bed\u8a00", self.source_language_combo)
        form.addRow("\u5904\u7406\u6a21\u5f0f", self.processing_mode_combo)

        layout = QVBoxLayout()
        layout.addLayout(form)
        self.setLayout(layout)

    def is_valid(self) -> bool:
        return bool(
            self.project_name_edit.text().strip()
            and self.video_path_edit.text().strip()
            and self.output_dir_edit.text().strip()
        )

    def browse_video_file(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "\u9009\u62e9\u6e90\u89c6\u9891",
            "",
            "Video files (*.mp4 *.mkv *.mov *.avi);;All files (*)",
        )
        if path:
            self.video_path_edit.setText(path)

    def browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "\u9009\u62e9\u8f93\u51fa\u76ee\u5f55",
            "",
        )
        if path:
            self.output_dir_edit.setText(path)

    def values(self) -> ProjectWizardValues:
        return ProjectWizardValues(
            project_name=self.project_name_edit.text().strip(),
            source_video=Path(self.video_path_edit.text().strip()),
            output_dir=Path(self.output_dir_edit.text().strip()),
            source_language=self.source_language_combo.currentText(),  # type: ignore[arg-type]
            processing_mode=self.processing_mode_combo.currentText(),
        )
