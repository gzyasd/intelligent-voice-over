from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ivo.core.project_library import ProjectLibraryItem
from ivo.ui.empty_states import EmptyStatePanel
from ivo.ui.theme import (
    BORDER,
    CARD_STYLE,
    DANGER,
    PRIMARY,
    PRIMARY_BUTTON_STYLE,
    SECONDARY_BUTTON_STYLE,
    SUCCESS,
    TEXT_SECONDARY,
    WARNING,
)


class ProjectLibraryPage(QWidget):
    open_project_requested = Signal(Path)
    open_folder_requested = Signal(Path)
    create_project_requested = Signal()
    open_existing_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.open_project_buttons: list[QPushButton] = []
        self.open_folder_buttons: list[QPushButton] = []
        self.empty_state: EmptyStatePanel | None = None
        self.open_existing_project_button = QPushButton("打开已有项目")
        self.open_existing_project_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self._summary_parts: list[str] = []

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(28, 28, 28, 28)
        self.content_layout.setSpacing(12)
        title = QLabel("项目库")
        title.setObjectName("PageTitle")
        self.content_layout.addWidget(title)
        subtitle = QLabel("查看每个作品的生成状态、总耗时和输出文件。")
        subtitle.setObjectName("SecondaryText")
        self.content_layout.addWidget(subtitle)
        self.setLayout(self.content_layout)

    def set_projects(self, projects: list[ProjectLibraryItem]) -> None:
        self._clear_project_widgets()
        self.open_project_buttons = []
        self.open_folder_buttons = []
        self.empty_state = None
        self._summary_parts = []
        if not projects:
            self.empty_state = EmptyStatePanel(
                title="还没有项目",
                description="新建一个配音项目，或打开之前保存的 .ivoproj 项目文件夹。",
                action_text="新建配音项目",
            )
            self.open_existing_project_button = QPushButton("打开已有项目")
            self.open_existing_project_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
            self.empty_state.action_button.clicked.connect(self.create_project_requested.emit)
            self.open_existing_project_button.clicked.connect(self.open_existing_requested.emit)
            self.content_layout.addWidget(self.empty_state)
            self.content_layout.addWidget(self.open_existing_project_button)
            self._summary_parts.extend(
                [
                    self.empty_state.title_label.text(),
                    self.empty_state.description_label.text(),
                    self.empty_state.action_button.text(),
                    self.open_existing_project_button.text(),
                ]
            )
            self.content_layout.addStretch()
            return
        for item in projects:
            self._add_project_card(item)
        self.content_layout.addStretch()

    def project_count(self) -> int:
        return len(self.open_project_buttons)

    def summary_text(self) -> str:
        return "\n".join(self._summary_parts)

    def _add_project_card(self, item: ProjectLibraryItem) -> None:
        card = QFrame()
        card.setStyleSheet(
            CARD_STYLE
            + """
            QFrame {
                border-radius: 14px;
            }
            """
        )
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        header = QHBoxLayout()
        name = QLabel(item.name)
        name.setStyleSheet("font-size: 17px; font-weight: 700;")
        status_badge = QLabel(item.status)
        status_badge.setStyleSheet(_status_badge_style(item.status))
        header.addWidget(name)
        header.addStretch()
        header.addWidget(status_badge)

        language = _language_text(item)
        meta = QLabel(language)
        meta.setObjectName("SecondaryText")
        meta.setStyleSheet(f"color: {TEXT_SECONDARY};")
        status = QLabel(item.status_detail or "尚未记录耗时")
        status.setObjectName("SecondaryText")
        status.setStyleSheet("font-size: 13px;")
        path_label = QLabel(str(item.path))
        path_label.setObjectName("SecondaryText")
        path_label.setWordWrap(True)
        path_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        open_project = QPushButton("打开项目")
        open_project.setStyleSheet(PRIMARY_BUTTON_STYLE)
        open_folder = QPushButton("打开文件夹")
        open_folder.setStyleSheet(SECONDARY_BUTTON_STYLE)
        open_project.clicked.connect(
            lambda _checked=False, path=item.path: self.open_project_requested.emit(path)
        )
        open_folder.clicked.connect(
            lambda _checked=False, path=item.path: self.open_folder_requested.emit(path)
        )
        actions = QHBoxLayout()
        actions.addWidget(open_project)
        actions.addWidget(open_folder)
        actions.addStretch()

        layout.addLayout(header)
        layout.addWidget(meta)
        layout.addWidget(status)
        layout.addWidget(path_label)
        layout.addLayout(actions)
        card.setLayout(layout)
        self.content_layout.addWidget(card)
        self.open_project_buttons.append(open_project)
        self.open_folder_buttons.append(open_folder)
        self._summary_parts.extend([item.name, item.status, item.status_detail, language])

    def _clear_project_widgets(self) -> None:
        while self.content_layout.count() > 1:
            item = self.content_layout.takeAt(1)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


def _language_text(item: ProjectLibraryItem) -> str:
    source = item.source_language or "未知"
    target = item.target_language or "未知"
    return f"{source} → {target}"


def _status_badge_style(status: str) -> str:
    color = {
        "已完成": SUCCESS,
        "生成中": PRIMARY,
        "失败": DANGER,
        "未完成": WARNING,
        "未开始": TEXT_SECONDARY,
    }.get(status, TEXT_SECONDARY)
    return f"""
        QLabel {{
            color: {color};
            background: #ffffff;
            border: 1px solid {BORDER};
            border-radius: 10px;
            padding: 5px 10px;
            font-weight: 700;
        }}
    """
