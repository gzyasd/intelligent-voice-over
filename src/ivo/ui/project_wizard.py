from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ivo.core.settings import SeriesType
from ivo.core.timeline import SourceLanguage


class ProjectWizardValues(BaseModel):
    project_name: str
    source_video: Path
    output_dir: Path
    source_language: SourceLanguage
    processing_mode: str
    series_type: SeriesType
    translation_style_notes: str
    glossary_path: Path | None = None


class ProjectWizard(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新建配音项目")

        self.project_name_edit = QLineEdit()
        self.video_path_edit = QLineEdit()
        self.video_browse_button = QPushButton("浏览视频")
        self.output_dir_edit = QLineEdit()
        self.output_dir_browse_button = QPushButton("浏览输出目录")
        self.source_language_combo = QComboBox()
        self.source_language_combo.addItems(["en", "ja", "ko"])
        self.processing_mode_combo = QComboBox()
        self.processing_mode_combo.addItems(["fast_preview", "high_quality_export"])
        self.series_type_combo = QComboBox()
        self.series_type_combo.addItems(["american_drama", "japanese_drama", "korean_drama", "other"])
        self.translation_style_notes_edit = QPlainTextEdit()
        self.translation_style_notes_edit.setPlaceholderText("例如：日剧口吻，自然，不要书面腔。")
        self.glossary_path_edit = QLineEdit()
        self.glossary_browse_button = QPushButton("浏览术语表 JSON")

        self.video_browse_button.clicked.connect(self.browse_video_file)
        self.output_dir_browse_button.clicked.connect(self.browse_output_dir)
        self.glossary_browse_button.clicked.connect(self.browse_glossary_file)

        form = QFormLayout()
        form.addRow("项目名称", self.project_name_edit)
        form.addRow("源视频", self.video_path_edit)
        form.addRow("", self.video_browse_button)
        form.addRow("输出目录", self.output_dir_edit)
        form.addRow("", self.output_dir_browse_button)
        form.addRow("源语言", self.source_language_combo)
        form.addRow("处理模式", self.processing_mode_combo)
        form.addRow("剧集类型", self.series_type_combo)
        form.addRow("翻译风格备注", self.translation_style_notes_edit)
        form.addRow("术语表 JSON", self.glossary_path_edit)
        form.addRow("", self.glossary_browse_button)

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
            "选择源视频",
            "",
            "Video files (*.mp4 *.mkv *.mov *.avi);;All files (*)",
        )
        if path:
            self.video_path_edit.setText(path)

    def browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "选择输出目录",
            "",
        )
        if path:
            self.output_dir_edit.setText(path)

    def browse_glossary_file(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择术语表 JSON",
            "",
            "JSON files (*.json);;All files (*)",
        )
        if path:
            self.glossary_path_edit.setText(path)

    def values(self) -> ProjectWizardValues:
        raw_glossary_path = self.glossary_path_edit.text().strip()
        return ProjectWizardValues(
            project_name=self.project_name_edit.text().strip(),
            source_video=Path(self.video_path_edit.text().strip()),
            output_dir=Path(self.output_dir_edit.text().strip()),
            source_language=self.source_language_combo.currentText(),  # type: ignore[arg-type]
            processing_mode=self.processing_mode_combo.currentText(),
            series_type=self.series_type_combo.currentText(),  # type: ignore[arg-type]
            translation_style_notes=self.translation_style_notes_edit.toPlainText().strip(),
            glossary_path=Path(raw_glossary_path) if raw_glossary_path else None,
        )
