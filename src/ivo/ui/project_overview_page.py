from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

from ivo.core.project import DubbingProject
from ivo.core.project_status import ProjectStatusSnapshot
from ivo.ui.theme import (
    mark_card,
    mark_heading2,
    mark_primary_button,
    mark_secondary_button,
)

LANGUAGE_LABELS = {
    "en": "英语",
    "ja": "日语",
    "ko": "韩语",
    "zh": "中文",
}


class ProjectOverviewPage(QWidget):
    start_requested = Signal()
    create_requested = Signal()
    progress_requested = Signal()
    open_folder_requested = Signal(Path)
    open_output_requested = Signal(Path)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._snapshot: ProjectStatusSnapshot | None = None
        self._primary_action_mode = "create"

        self.project_name_label = QLabel("还没有打开项目")
        mark_heading2(self.project_name_label)
        self.source_media_label = QLabel("先新建或打开一个配音项目。")
        self.source_media_label.setObjectName("SecondaryText")
        self.language_label = QLabel("语言：未设置")
        self.status_label = QLabel("未开始")
        self.profile_label = QLabel("模型方案：当前推荐配置")
        self.profile_label.setObjectName("SecondaryText")
        self.primary_action_button = QPushButton("新建配音项目")
        self.primary_action_button.setStyleSheet("")
        mark_primary_button(self.primary_action_button)
        self.open_folder_button = QPushButton("打开项目文件夹")
        self.open_folder_button.setStyleSheet("")
        mark_secondary_button(self.open_folder_button)
        self.open_output_button = QPushButton("打开生成视频")
        self.open_output_button.setStyleSheet("")
        mark_secondary_button(self.open_output_button)

        self.primary_action_button.clicked.connect(self._emit_primary_action)
        self.open_folder_button.clicked.connect(self._emit_open_folder)
        self.open_output_button.clicked.connect(self._emit_open_output)

        card = QFrame()
        card.setStyleSheet("")
        mark_card(card)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(9)
        card_layout.addWidget(self.project_name_label)
        card_layout.addWidget(self.source_media_label)
        card_layout.addWidget(self.language_label)
        card_layout.addWidget(self.status_label)
        card_layout.addWidget(self.profile_label)
        card_layout.addWidget(self.primary_action_button)
        card_layout.addWidget(self.open_folder_button)
        card_layout.addWidget(self.open_output_button)
        card.setLayout(card_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(card)
        self.setLayout(layout)
        self.set_project_snapshot(None)

    def set_project_snapshot(self, snapshot: ProjectStatusSnapshot | None) -> None:
        self._snapshot = snapshot
        if snapshot is None:
            self.project_name_label.setText("还没有打开项目")
            self.source_media_label.setText("先新建或打开一个配音项目。")
            self.language_label.setText("语言：未设置")
            self.status_label.setText("未开始")
            self.profile_label.setText("模型方案：当前推荐配置")
            self.primary_action_button.setText("新建配音项目")
            self._primary_action_mode = "create"
            self.open_folder_button.setEnabled(False)
            self.open_output_button.setEnabled(False)
            return

        self.project_name_label.setText(snapshot.name)
        source_name = snapshot.source_media_path.name if snapshot.source_media_path else ""
        if snapshot.content_type == "audio":
            self.source_media_label.setText(f"源音频：{source_name}" if source_name else "源音频")
            self.open_output_button.setText("打开生成音频")
        else:
            self.source_media_label.setText(f"源视频：{source_name}" if source_name else "源视频")
            self.open_output_button.setText("打开生成视频")
        source = LANGUAGE_LABELS.get(snapshot.source_language, snapshot.source_language)
        target = LANGUAGE_LABELS.get(snapshot.target_language, snapshot.target_language)
        self.language_label.setText(f"{source} -> {target}")
        self.status_label.setText(snapshot.status_label)
        self.primary_action_button.setText(_primary_action_text(snapshot.primary_action))
        self._primary_action_mode = snapshot.primary_action
        self.open_folder_button.setEnabled(True)
        self.open_output_button.setEnabled(snapshot.open_output_enabled)

    def set_project(self, project: DubbingProject | None) -> None:
        if project is None:
            self.set_project_snapshot(None)
            return
        from ivo.core.project_status import read_project_status_snapshot

        self.set_project_snapshot(
            read_project_status_snapshot(project.path, active_project_paths=set())
        )

    def _emit_primary_action(self) -> None:
        if self._primary_action_mode == "create":
            self.create_requested.emit()
            return
        if self._primary_action_mode == "open_output":
            self._emit_open_output()
            return
        if self._primary_action_mode == "progress":
            self.progress_requested.emit()
            return
        self.start_requested.emit()

    def _emit_open_folder(self) -> None:
        if self._snapshot is not None:
            self.open_folder_requested.emit(self._snapshot.project_path)

    def _emit_open_output(self) -> None:
        if self._snapshot is not None and self._snapshot.final_output_path is not None:
            self.open_output_requested.emit(self._snapshot.final_output_path)


def _primary_action_text(action: str) -> str:
    return {
        "create": "新建配音项目",
        "start": "开始生成",
        "resume": "继续/重试生成",
        "progress": "查看进度",
        "open_output": "查看成品",
    }.get(action, "开始生成")
