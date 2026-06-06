from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from ivo.core.project import DubbingProject
from ivo.ui.theme import CARD_STYLE, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE, TEXT_SECONDARY

LANGUAGE_LABELS = {
    "en": "英语",
    "ja": "日语",
    "ko": "韩语",
    "zh": "中文",
}


class ProjectOverviewPage(QWidget):
    start_requested = Signal()
    create_requested = Signal()
    open_folder_requested = Signal(Path)
    open_video_requested = Signal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project: DubbingProject | None = None

        self.project_name_label = QLabel("还没有打开项目")
        self.project_name_label.setStyleSheet("font-size: 20px; font-weight: 700;")
        self.source_video_label = QLabel("先新建或打开一个配音项目。")
        self.source_video_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self.language_label = QLabel("语言：未设置")
        self.status_label = QLabel("未开始")
        self.profile_label = QLabel("模型方案：当前推荐配置")
        self.profile_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self.primary_action_button = QPushButton("新建配音项目")
        self.primary_action_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.open_folder_button = QPushButton("打开项目文件夹")
        self.open_folder_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.open_video_button = QPushButton("打开生成视频")
        self.open_video_button.setStyleSheet(SECONDARY_BUTTON_STYLE)

        self.primary_action_button.clicked.connect(self._emit_primary_action)
        self.open_folder_button.clicked.connect(self._emit_open_folder)
        self.open_video_button.clicked.connect(self._emit_open_video)

        card = QFrame()
        card.setStyleSheet(CARD_STYLE)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(9)
        card_layout.addWidget(self.project_name_label)
        card_layout.addWidget(self.source_video_label)
        card_layout.addWidget(self.language_label)
        card_layout.addWidget(self.status_label)
        card_layout.addWidget(self.profile_label)
        card_layout.addWidget(self.primary_action_button)
        card_layout.addWidget(self.open_folder_button)
        card_layout.addWidget(self.open_video_button)
        card.setLayout(card_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(card)
        self.setLayout(layout)
        self.set_project(None)

    def set_project(self, project: DubbingProject | None) -> None:
        self._project = project
        if project is None:
            self.project_name_label.setText("还没有打开项目")
            self.source_video_label.setText("先新建或打开一个配音项目。")
            self.language_label.setText("语言：未设置")
            self.status_label.setText("未开始")
            self.profile_label.setText("模型方案：当前推荐配置")
            self.primary_action_button.setText("新建配音项目")
            self.open_folder_button.setEnabled(False)
            self.open_video_button.setEnabled(False)
            return

        self.project_name_label.setText(project.name)
        self.source_video_label.setText(str(project.source_video_path or project.path))
        source = LANGUAGE_LABELS.get(project.source_language, project.source_language)
        target = LANGUAGE_LABELS.get(project.target_language, project.target_language)
        self.language_label.setText(f"{source} -> {target}")
        status = _project_status(project)
        self.status_label.setText(status)
        self.primary_action_button.setText(_primary_action_text(status))
        self.open_folder_button.setEnabled(True)
        self.open_video_button.setEnabled((project.path / "renders" / "local-preview.mp4").is_file())

    def _emit_primary_action(self) -> None:
        if self._project is None:
            self.create_requested.emit()
            return
        self.start_requested.emit()

    def _emit_open_folder(self) -> None:
        if self._project is not None:
            self.open_folder_requested.emit(self._project.path)

    def _emit_open_video(self) -> None:
        if self._project is None:
            return
        video_path = self._project.path / "renders" / "local-preview.mp4"
        if video_path.is_file():
            self.open_video_requested.emit(video_path)


def _project_status(project: DubbingProject) -> str:
    records = project.jobs.list_records()
    if not records:
        return "未开始"
    if any(record.status == "failed" for record in records):
        return "生成失败"
    if any(record.status == "running" for record in records):
        return "生成中"
    if project.jobs.get("export") is not None and project.jobs.get("export").status == "completed":  # type: ignore[union-attr]
        return "已完成"
    return "可继续"


def _primary_action_text(status: str) -> str:
    if status == "生成失败":
        return "重试失败阶段"
    if status == "已完成":
        return "查看成品"
    if status == "生成中":
        return "查看进度"
    return "开始生成"
