from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ivo.core.project_library import ProjectLibraryItem
from ivo.ui.empty_states import EmptyStatePanel
from ivo.ui.theme import (
    mark_card,
    mark_heading3,
    mark_primary_button,
    mark_secondary_button,
    mark_status_badge,
)


class ProjectLibraryPage(QWidget):
    open_project_requested = Signal(Path)
    open_folder_requested = Signal(Path)
    create_project_requested = Signal()
    open_existing_requested = Signal()

    # Minimum card width in pixels; grid will fit as many columns as possible.
    _CARD_MIN_WIDTH = 320

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.open_project_buttons: list[QPushButton] = []
        self.open_folder_buttons: list[QPushButton] = []
        self.empty_state: EmptyStatePanel | None = None
        self.open_existing_project_button = QPushButton("打开已有项目")
        self.open_existing_project_button.setStyleSheet("")
        mark_secondary_button(self.open_existing_project_button)
        self._summary_parts: list[str] = []
        self._card_widgets: list[QWidget] = []
        self._card_items: list[ProjectLibraryItem] = []

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(28, 28, 28, 28)
        self.content_layout.setSpacing(12)
        title = QLabel("项目库")
        title.setObjectName("PageTitle")
        self.content_layout.addWidget(title)
        subtitle = QLabel("查看每个作品的生成状态、总耗时和输出文件。")
        subtitle.setObjectName("SecondaryText")
        self.content_layout.addWidget(subtitle)

        # Scroll area with a container widget for the grid
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._grid_container = QWidget()
        self._grid_layout = QGridLayout()
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(12)
        self._grid_container.setLayout(self._grid_layout)
        self._scroll.setWidget(self._grid_container)

        self.content_layout.addWidget(self._scroll, 1)
        self.setLayout(self.content_layout)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Recalculate grid columns when the page is resized."""
        super().resizeEvent(event)
        self._reflow_grid()

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
            self.open_existing_project_button.setStyleSheet("")
            mark_secondary_button(self.open_existing_project_button)
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
            return

        for item in projects:
            card = self._build_card(item)
            self._card_widgets.append(card)
            self._card_items.append(item)

        self._reflow_grid()

    def project_count(self) -> int:
        return len(self.open_project_buttons)

    def summary_text(self) -> str:
        return "\n".join(self._summary_parts)

    # ── Internal ───────────────────────────────────────────────────────

    def _build_card(self, item: ProjectLibraryItem) -> QWidget:
        """Build a single project card widget."""
        card = QFrame()
        card.setStyleSheet("")
        mark_card(card)
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setSpacing(8)
        name = QLabel(item.name)
        name.setMinimumWidth(1)
        mark_heading3(name)
        status_badge = QLabel(item.status)
        _apply_project_status_badge(status_badge, item.status)
        header.addWidget(name, 1)
        header.addWidget(status_badge)

        language = _language_text(item)
        meta = QLabel(language)
        meta.setObjectName("SecondaryText")

        status = QLabel(item.status_detail or "尚未记录耗时")
        status.setObjectName("SecondaryText")

        path_label = QLabel(str(item.path))
        path_label.setObjectName("SecondaryText")
        path_label.setWordWrap(True)

        open_project = QPushButton("打开项目")
        open_project.setStyleSheet("")
        mark_primary_button(open_project)
        open_folder = QPushButton("打开文件夹")
        open_folder.setStyleSheet("")
        mark_secondary_button(open_folder)
        open_project.clicked.connect(
            lambda _checked=False, p=item.path: self.open_project_requested.emit(p)
        )
        open_folder.clicked.connect(
            lambda _checked=False, p=item.path: self.open_folder_requested.emit(p)
        )

        actions = QHBoxLayout()
        actions.setSpacing(8)
        actions.addWidget(open_project)
        actions.addWidget(open_folder)
        actions.addStretch()

        layout.addLayout(header)
        layout.addWidget(meta)
        layout.addWidget(status)
        layout.addWidget(path_label)
        layout.addLayout(actions)
        card.setLayout(layout)

        # Store button references
        self.open_project_buttons.append(open_project)
        self.open_folder_buttons.append(open_folder)
        self._summary_parts.extend([item.name, item.status, item.status_detail, language])

        return card

    def _reflow_grid(self) -> None:
        """Reposition cards into the grid based on available width."""
        # Clear existing grid items
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item and item.widget():
                item.widget().setParent(None)  # type: ignore[union-attr]

        if not self._card_widgets:
            return

        scroll_width = self._scroll.viewport().width() - 4  # small padding
        cols = max(1, scroll_width // self._CARD_MIN_WIDTH)

        for idx, card in enumerate(self._card_widgets):
            row = idx // cols
            col = idx % cols
            self._grid_layout.addWidget(card, row, col)

        # Make each card stretch to fill its cell
        for row_idx in range((len(self._card_widgets) + cols - 1) // cols):
            self._grid_layout.setRowStretch(row_idx, 0)
        # Let last row have stretch to fill remaining space if needed
        if self._card_widgets:
            last_row = (len(self._card_widgets) - 1) // cols
            self._grid_layout.setRowStretch(last_row, 1)

    def _clear_project_widgets(self) -> None:
        """Remove all project cards from the grid."""
        for w in self._card_widgets:
            w.deleteLater()
        self._card_widgets.clear()
        self._card_items.clear()
        # Also remove empty state widgets that may have been added to content_layout
        while self.content_layout.count() > 3:  # title, subtitle, scroll = 3
            item = self.content_layout.takeAt(3)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


def _language_text(item: ProjectLibraryItem) -> str:
    source = item.source_language or "未知"
    target = item.target_language or "未知"
    return f"{source} → {target}"


def _apply_project_status_badge(label: QLabel, status: str) -> None:
    mapped = {
        "已完成": "ready",
        "生成中": "applied",
        "失败": "failed",
        "未完成": "warning",
        "未开始": "unchecked",
    }.get(status, "unchecked")
    mark_status_badge(label, mapped)
