from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
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
from ivo.model_services.provider_store import ProviderStore
from ivo.model_services.stages import STAGE_LABELS
from ivo.workspace_paths import default_runs_dir
from ivo.ui.theme import mark_caption_text, mark_heading2, mark_scheme_detail_frame


class ProjectWizardValues(BaseModel):
    project_name: str
    source_media: Path
    content_type: Literal["video", "audio"]
    output_dir: Path
    source_language: SourceLanguage
    scheme_id: str | None = None
    series_type: SeriesType
    translation_style_notes: str
    glossary_path: Path | None = None
    start_immediately: bool = False


class ProjectWizard(QDialog):
    STEP_TITLES = ["选择素材", "内容与语言", "选择方案", "确认创建"]

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        store: ProviderStore | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("新建配音项目")
        self._start_immediately = False
        self._store = store

        self.project_name_edit = QLineEdit()
        self.media_path_edit = QLineEdit()
        self.media_browse_button = QPushButton("浏览素材")
        self.output_dir_edit = QLineEdit(str(default_runs_dir()))
        self.output_dir_browse_button = QPushButton("浏览输出目录")
        self.source_language_combo = QComboBox()
        self.source_language_combo.addItem("英语", "en")
        self.source_language_combo.addItem("日语", "ja")
        self.source_language_combo.addItem("韩语", "ko")
        self.scheme_combo = QComboBox()
        self._scheme_detail_label = QLabel("")
        self._scheme_detail_label.setWordWrap(True)
        self._scheme_detail_frame = QFrame()
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
        mark_heading2(self.step_title_label)
        self.step_stack = QStackedWidget()
        self.back_step_button = QPushButton("上一步")
        self.next_step_button = QPushButton("下一步")
        self.create_project_button = QPushButton("创建项目")
        self.create_and_start_button = QPushButton("创建并开始生成")
        self.cancel_button = QPushButton("取消")
        self.create_project_button.setEnabled(False)
        self.create_and_start_button.setEnabled(False)
        self.back_step_button.setEnabled(False)

        self._load_schemes()

        self.media_browse_button.clicked.connect(self.browse_media_file)
        self.output_dir_browse_button.clicked.connect(self.browse_output_dir)
        self.glossary_browse_button.clicked.connect(self.browse_glossary_file)
        self.create_project_button.clicked.connect(self.accept)
        self.create_and_start_button.clicked.connect(self.accept_and_start)
        self.cancel_button.clicked.connect(self.reject)
        self.back_step_button.clicked.connect(self.previous_step)
        self.next_step_button.clicked.connect(self.next_step)
        self.project_name_edit.textChanged.connect(self._refresh_create_button)
        self.media_path_edit.textChanged.connect(self._refresh_create_button)
        self.output_dir_edit.textChanged.connect(self._refresh_create_button)
        self.scheme_combo.currentIndexChanged.connect(self._on_scheme_changed)

        self.step_stack.addWidget(self._build_media_step())
        self.step_stack.addWidget(self._build_content_step())
        self.step_stack.addWidget(self._build_scheme_step())
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
        # Initialize scheme detail display
        self._on_scheme_changed(0)

    def _load_schemes(self) -> None:
        """Load schemes from the provider store and populate the combo."""
        self.scheme_combo.clear()
        if self._store is None:
            self.scheme_combo.addItem("（无可用方案，请先在方案管理中创建）", None)
            return
        schemes = self._store.load_schemes()
        if not schemes:
            self.scheme_combo.addItem("（无可用方案，请先在方案管理中创建）", None)
            return
        # Check for default scheme
        default_id = self._store.load_default_scheme_id()
        for scheme in schemes:
            label = scheme.display_name
            if scheme.id == default_id:
                label = f"⭐ {label}（默认）"
            self.scheme_combo.addItem(label, scheme.id)
        # Pre-select default scheme if available
        if default_id:
            for i in range(self.scheme_combo.count()):
                if self.scheme_combo.itemData(i) == default_id:
                    self.scheme_combo.setCurrentIndex(i)
                    break

    def _on_scheme_changed(self, _index: int) -> None:
        """Update scheme detail display when selection changes."""
        scheme_id = self.scheme_combo.currentData()
        if not scheme_id or self._store is None:
            self._scheme_detail_label.setText("请先在「方案管理」中创建并配置方案。")
            return
        scheme = self._store.get_scheme(scheme_id)
        if scheme is None:
            self._scheme_detail_label.setText("方案信息不可用。")
            return
        lines: list[str] = []
        if scheme.description:
            lines.append(scheme.description)
        if scheme.bindings:
            lines.append("阶段配置：")
            for binding in scheme.bindings:
                stage_label = STAGE_LABELS.get(binding.stage, binding.stage)
                config = self._store.get_stage_config(binding.stage_config_id)
                if config:
                    kind_label = "本地" if config.kind == "local" else "API"
                    provider = config.provider_key
                    model = config.model_name or config.protocol
                    lines.append(f"  {stage_label}：{kind_label} · {provider} · {model}")
                else:
                    lines.append(f"  {stage_label}：（配置已删除）")
        else:
            lines.append("此方案尚未绑定任何阶段配置。")
        if scheme.prefer_gpu:
            lines.append("硬件偏好：优先 GPU")
        content_types = "、".join(scheme.content_types) if scheme.content_types else "通用"
        lines.append(f"内容类型：{content_types}")
        self._scheme_detail_label.setText("\n".join(lines))

    def _build_media_step(self) -> QWidget:
        page = QWidget()
        form = QFormLayout()
        form.addRow("项目名称", self.project_name_edit)
        form.addRow("源素材", self.media_path_edit)
        form.addRow("", self.media_browse_button)
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

    def _build_scheme_step(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        hint = QLabel("选择已配置的配音方案，该方案将用于项目的全部流水线阶段。")
        layout.addWidget(hint)

        form = QFormLayout()
        form.addRow("配音方案", self.scheme_combo)
        layout.addLayout(form)

        # Detail frame
        self._scheme_detail_frame.setFrameShape(QFrame.Shape.StyledPanel)
        mark_scheme_detail_frame(self._scheme_detail_frame)
        detail_layout = QVBoxLayout()
        detail_layout.setContentsMargins(10, 10, 10, 10)
        mark_caption_text(self._scheme_detail_label)
        detail_layout.addWidget(self._scheme_detail_label)
        self._scheme_detail_frame.setLayout(detail_layout)
        layout.addWidget(self._scheme_detail_frame)

        layout.addStretch()
        page.setLayout(layout)
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
            and self.media_path_edit.text().strip()
            and self.output_dir_edit.text().strip()
        )

    def browse_media_file(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "选择源素材",
            "",
            "视频文件 (*.mp4 *.mkv *.mov *.avi);;音频文件 (*.wav *.mp3 *.m4a *.flac *.aac *.ogg);;所有文件 (*)",
        )
        if path:
            self.media_path_edit.setText(path)

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

    def set_series_type(self, series_type: SeriesType) -> None:
        _set_combo_by_data(self.series_type_combo, series_type)

    def values(self) -> ProjectWizardValues:
        raw_glossary_path = self.glossary_path_edit.text().strip()
        scheme_id = self.scheme_combo.currentData()
        raw_path = self.media_path_edit.text().strip()
        source_path = Path(raw_path)
        # Auto-detect content type by file extension
        suffix = source_path.suffix.lower()
        if suffix in (".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg"):
            content_type: Literal["video", "audio"] = "audio"
        else:
            content_type = "video"
        return ProjectWizardValues(
            project_name=self.project_name_edit.text().strip(),
            source_media=source_path,
            content_type=content_type,
            output_dir=Path(self.output_dir_edit.text().strip()),
            source_language=self.source_language_combo.currentData(),
            scheme_id=scheme_id if isinstance(scheme_id, str) else None,
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
