from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ivo.core.settings import SeriesType
from ivo.core.timeline import SourceLanguage
from ivo.workspace_paths import default_runs_dir


class ProjectWizardValues(BaseModel):
    project_name: str
    source_video: Path
    output_dir: Path
    source_language: SourceLanguage
    processing_mode: str
    series_type: SeriesType
    translation_style_notes: str
    glossary_path: Path | None = None
    start_immediately: bool = False


class ProjectWizard(QDialog):
    STEP_TITLES = ["选择视频", "内容与语言", "生成方案", "确认创建"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("新建配音项目")
        self._start_immediately = False

        self.project_name_edit = QLineEdit()
        self.video_path_edit = QLineEdit()
        self.video_browse_button = QPushButton("浏览视频")
        self.output_dir_edit = QLineEdit(str(default_runs_dir()))
        self.output_dir_browse_button = QPushButton("浏览输出目录")
        self.source_language_combo = QComboBox()
        self.source_language_combo.addItem("英语", "en")
        self.source_language_combo.addItem("日语", "ja")
        self.source_language_combo.addItem("韩语", "ko")
        self.processing_mode_combo = QComboBox()
        self.processing_mode_combo.addItem("快速预览", "fast_preview")
        self.processing_mode_combo.addItem("高质量导出", "high_quality_export")
        self.series_type_combo = QComboBox()
        self.series_type_combo.addItem("美剧", "american_drama")
        self.series_type_combo.addItem("日剧", "japanese_drama")
        self.series_type_combo.addItem("韩剧", "korean_drama")
        self.series_type_combo.addItem("其他", "other")
        self.translation_style_notes_edit = QPlainTextEdit()
        self.translation_style_notes_edit.setPlaceholderText("例如：日剧口吻，自然，不要书面腔。")
        self.glossary_path_edit = QLineEdit()
        self.glossary_browse_button = QPushButton("浏览术语表")
        self.step_title_label = QLabel(self.STEP_TITLES[0])
        self.step_title_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.step_stack = QStackedWidget()
        self.back_step_button = QPushButton("上一步")
        self.next_step_button = QPushButton("下一步")
        self.create_project_button = QPushButton("创建项目")
        self.create_and_start_button = QPushButton("创建并开始生成")
        self.cancel_button = QPushButton("取消")
        self.create_project_button.setEnabled(False)
        self.create_and_start_button.setEnabled(False)
        self.back_step_button.setEnabled(False)

        self.video_browse_button.clicked.connect(self.browse_video_file)
        self.output_dir_browse_button.clicked.connect(self.browse_output_dir)
        self.glossary_browse_button.clicked.connect(self.browse_glossary_file)
        self.create_project_button.clicked.connect(self.accept)
        self.create_and_start_button.clicked.connect(self.accept_and_start)
        self.cancel_button.clicked.connect(self.reject)
        self.back_step_button.clicked.connect(self.previous_step)
        self.next_step_button.clicked.connect(self.next_step)
        self.project_name_edit.textChanged.connect(self._refresh_create_button)
        self.video_path_edit.textChanged.connect(self._refresh_create_button)
        self.output_dir_edit.textChanged.connect(self._refresh_create_button)

        self.step_stack.addWidget(self._build_video_step())
        self.step_stack.addWidget(self._build_content_step())
        self.step_stack.addWidget(self._build_generation_step())
        self.step_stack.addWidget(self._build_confirm_step())

        layout = QVBoxLayout()
        layout.addWidget(self.step_title_label)
        layout.addWidget(self.step_stack)
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.back_step_button)
        button_layout.addWidget(self.next_step_button)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.create_and_start_button)
        button_layout.addWidget(self.create_project_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self._refresh_step_buttons()

    def _build_video_step(self) -> QWidget:
        page = QWidget()
        form = QFormLayout()
        form.addRow("项目名称", self.project_name_edit)
        form.addRow("源视频", self.video_path_edit)
        form.addRow("", self.video_browse_button)
        form.addRow("输出目录", self.output_dir_edit)
        form.addRow("", self.output_dir_browse_button)
        page.setLayout(form)
        return page

    def _build_content_step(self) -> QWidget:
        page = QWidget()
        form = QFormLayout()
        form.addRow("源语言", self.source_language_combo)
        form.addRow("剧集类型", self.series_type_combo)
        form.addRow("翻译风格备注", self.translation_style_notes_edit)
        form.addRow("术语表", self.glossary_path_edit)
        form.addRow("", self.glossary_browse_button)
        page.setLayout(form)
        return page

    def _build_generation_step(self) -> QWidget:
        page = QWidget()
        form = QFormLayout()
        form.addRow("处理模式", self.processing_mode_combo)
        form.addRow("生成方案", QLabel("使用当前模型中心推荐配置"))
        page.setLayout(form)
        return page

    def _build_confirm_step(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QLabel("确认后会创建项目。也可以直接创建并开始生成配音。"))
        page.setLayout(layout)
        return page

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
            "视频文件 (*.mp4 *.mkv *.mov *.avi);;所有文件 (*)",
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
            "选择术语表",
            "",
            "JSON 文件 (*.json);;所有文件 (*)",
        )
        if path:
            self.glossary_path_edit.setText(path)

    def set_source_language(self, source_language: SourceLanguage) -> None:
        _set_combo_by_data(self.source_language_combo, source_language)

    def set_processing_mode(self, processing_mode: str) -> None:
        _set_combo_by_data(self.processing_mode_combo, processing_mode)

    def set_series_type(self, series_type: SeriesType) -> None:
        _set_combo_by_data(self.series_type_combo, series_type)

    def values(self) -> ProjectWizardValues:
        raw_glossary_path = self.glossary_path_edit.text().strip()
        return ProjectWizardValues(
            project_name=self.project_name_edit.text().strip(),
            source_video=Path(self.video_path_edit.text().strip()),
            output_dir=Path(self.output_dir_edit.text().strip()),
            source_language=self.source_language_combo.currentData(),
            processing_mode=self.processing_mode_combo.currentData(),
            series_type=self.series_type_combo.currentData(),
            translation_style_notes=self.translation_style_notes_edit.toPlainText().strip(),
            glossary_path=Path(raw_glossary_path) if raw_glossary_path else None,
            start_immediately=self._start_immediately,
        )

    def _refresh_create_button(self) -> None:
        is_valid = self.is_valid()
        self.create_project_button.setEnabled(is_valid)
        self.create_and_start_button.setEnabled(is_valid)

    def step_titles(self) -> list[str]:
        return list(self.STEP_TITLES)

    def current_step_title(self) -> str:
        return self.STEP_TITLES[self.step_stack.currentIndex()]

    def next_step(self) -> None:
        index = min(self.step_stack.currentIndex() + 1, self.step_stack.count() - 1)
        self.step_stack.setCurrentIndex(index)
        self._refresh_step_buttons()

    def previous_step(self) -> None:
        index = max(self.step_stack.currentIndex() - 1, 0)
        self.step_stack.setCurrentIndex(index)
        self._refresh_step_buttons()

    def accept_and_start(self) -> None:
        self._start_immediately = True
        self.accept()

    def _refresh_step_buttons(self) -> None:
        index = self.step_stack.currentIndex()
        self.step_title_label.setText(self.STEP_TITLES[index])
        self.back_step_button.setEnabled(index > 0)
        self.next_step_button.setEnabled(index < self.step_stack.count() - 1)


def _set_combo_by_data(combo: QComboBox, value: str) -> None:
    for index in range(combo.count()):
        if combo.itemData(index) == value:
            combo.setCurrentIndex(index)
            return
    raise ValueError(f"Unknown combo value: {value}")
