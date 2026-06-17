from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ivo.core.project_library import ProjectLibraryItem
from ivo.ui.empty_states import EmptyStatePanel
from ivo.ui.theme import (
    mark_card,
    mark_caption_text,
    mark_compact_button,
    mark_heading3,
    mark_primary_button,
    mark_secondary_button,
    mark_status_badge,
    mark_sub_text,
)


class ProjectLibraryPage(QWidget):
    open_project_requested = Signal(Path)
    open_folder_requested = Signal(Path)
    open_output_requested = Signal(Path)
    create_project_requested = Signal()
    open_existing_requested = Signal()
    delete_project_requested = Signal(Path)

    # Card dimensions — fixed width & height so cards never stretch
    _CARD_WIDTH = 300
    _CARD_HEIGHT = 180

    # Status filter values
    _STATUS_FILTER_ALL = "全部"
    _STATUS_FILTER_RUNNING = "生成中"
    _STATUS_FILTER_COMPLETED = "已完成"
    _STATUS_FILTER_INCOMPLETE = "未完成"
    _STATUS_FILTER_FAILED = "生成失败"
    _STATUS_FILTER_NOT_STARTED = "未开始"

    # Sort values
    _SORT_UPDATED = "最近更新"
    _SORT_NAME = "名称"
    _SORT_STATUS = "状态"
    _SORT_ELAPSED = "总耗时"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.open_project_buttons: list[QPushButton] = []
        self.open_folder_buttons: list[QPushButton] = []
        self.open_output_buttons: list[QPushButton] = []
        self.empty_state: EmptyStatePanel | None = None
        self._no_match_state: EmptyStatePanel | None = None
        self._empty_wrapper: QWidget | None = None
        self.open_existing_project_button = QPushButton("打开已有项目")
        self.open_existing_project_button.setStyleSheet("")
        mark_secondary_button(self.open_existing_project_button)
        self._summary_parts: list[str] = []
        self._card_widgets: list[QWidget] = []
        self._card_items: list[ProjectLibraryItem] = []
        self._all_items: list[ProjectLibraryItem] = []

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(28, 28, 28, 28)
        self.content_layout.setSpacing(12)

        # ── Header row: title + action buttons ──
        header_row = QHBoxLayout()
        header_row.setSpacing(12)
        title = QLabel("项目库")
        title.setObjectName("PageTitle")
        subtitle = QLabel("查看每个作品的生成状态、总耗时和输出文件。")
        subtitle.setObjectName("SecondaryText")
        header_row.addWidget(title)
        header_row.addWidget(subtitle, 1)
        self._btn_create = QPushButton("新建项目")
        self._btn_create.setStyleSheet("")
        mark_primary_button(self._btn_create)
        self._btn_create.clicked.connect(self.create_project_requested.emit)
        self._btn_open_existing = QPushButton("打开已有项目")
        self._btn_open_existing.setStyleSheet("")
        mark_secondary_button(self._btn_open_existing)
        self._btn_open_existing.clicked.connect(self.open_existing_requested.emit)
        header_row.addWidget(self._btn_create)
        header_row.addWidget(self._btn_open_existing)
        self.content_layout.addLayout(header_row)

        # ── Toolbar: search + filter + sort (wrapped in a widget for hide/show) ──
        self._toolbar_widget = QWidget()
        toolbar_inner = QHBoxLayout()
        toolbar_inner.setContentsMargins(0, 0, 0, 0)
        toolbar_inner.setSpacing(10)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("搜索项目名称、语言或路径")
        self._search_edit.setClearButtonEnabled(True)
        self._search_edit.setMaximumWidth(280)
        self._search_edit.textChanged.connect(self._apply_filter)
        toolbar_inner.addWidget(self._search_edit)

        self._status_filter = QComboBox()
        self._status_filter.addItems([
            self._STATUS_FILTER_ALL,
            self._STATUS_FILTER_RUNNING,
            self._STATUS_FILTER_COMPLETED,
            self._STATUS_FILTER_INCOMPLETE,
            self._STATUS_FILTER_FAILED,
            self._STATUS_FILTER_NOT_STARTED,
        ])
        self._status_filter.setMinimumWidth(100)
        self._status_filter.currentIndexChanged.connect(self._apply_filter)
        toolbar_inner.addWidget(self._status_filter)

        self._sort_combo = QComboBox()
        self._sort_combo.addItems([
            self._SORT_UPDATED,
            self._SORT_NAME,
            self._SORT_STATUS,
            self._SORT_ELAPSED,
        ])
        self._sort_combo.setMinimumWidth(100)
        self._sort_combo.currentIndexChanged.connect(self._apply_filter)
        toolbar_inner.addWidget(self._sort_combo)
        toolbar_inner.addStretch()
        self._toolbar_widget.setLayout(toolbar_inner)
        self.content_layout.addWidget(self._toolbar_widget)

        # ── Statistics bar (wrapped in a widget for hide/show) ──
        self._stats_widget = QWidget()
        stats_inner = QHBoxLayout()
        stats_inner.setContentsMargins(0, 0, 0, 0)
        stats_inner.setSpacing(20)
        self._stat_labels: dict[str, QLabel] = {}
        for key, label_text in [
            ("all", "全部项目"),
            ("completed", "已完成"),
            ("running", "生成中"),
            ("failed", "生成失败"),
        ]:
            stat_label = QLabel(f"{label_text} 0")
            stat_label.setObjectName("SecondaryText")
            mark_caption_text(stat_label)
            self._stat_labels[key] = stat_label
            stats_inner.addWidget(stat_label)
        stats_inner.addStretch()
        self._stats_widget.setLayout(stats_inner)
        self.content_layout.addWidget(self._stats_widget)

        # ── Main content area (switches between scroll grid and empty state) ──
        self._content_stack = QVBoxLayout()
        self._content_stack.setContentsMargins(0, 0, 0, 0)
        self._content_stack.setSpacing(0)

        # Scroll area with flow container for cards
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._flow_container = QWidget()
        self._flow_layout = QVBoxLayout()
        self._flow_layout.setContentsMargins(0, 0, 0, 0)
        self._flow_layout.setSpacing(14)
        self._flow_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._flow_container.setLayout(self._flow_layout)
        self._scroll.setWidget(self._flow_container)

        self._content_stack.addWidget(self._scroll)
        self.content_layout.addLayout(self._content_stack, 1)
        self.setLayout(self.content_layout)

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Recalculate card wrapping when the page is resized."""
        super().resizeEvent(event)
        self._schedule_reflow_cards()

    def set_projects(self, projects: list[ProjectLibraryItem]) -> None:
        self._clear_project_widgets()
        self.open_project_buttons = []
        self.open_folder_buttons = []
        self.open_output_buttons = []
        self.empty_state = None
        self._no_match_state = None
        self._summary_parts = []
        self._all_items = list(projects)

        self._update_stats(projects)

        if not projects:
            self._show_empty_state()
            return

        self._toolbar_widget.show()
        self._stats_widget.show()
        self._scroll.show()
        self._apply_filter()

    def project_count(self) -> int:
        return len(self.open_project_buttons)

    def summary_text(self) -> str:
        return "\n".join(self._summary_parts)

    # ── Internal ───────────────────────────────────────────────────────

    def _schedule_reflow_cards(self) -> None:
        """Defer reflow to the next event-loop tick so viewport size is stable."""
        QTimer.singleShot(0, self._reflow_cards)

    def _show_empty_state(self) -> None:
        self._scroll.hide()
        self._toolbar_widget.hide()
        self._stats_widget.hide()

        self.empty_state = EmptyStatePanel(
            title="还没有项目",
            description="新建一个配音项目，或打开之前保存的 .ivoproj 项目文件夹。",
            action_text="新建配音项目",
        )
        self.empty_state.setMaximumWidth(520)
        self.empty_state.action_button.setMaximumWidth(240)
        self.empty_state.action_button.clicked.connect(self.create_project_requested.emit)

        self.open_existing_project_button = QPushButton("打开已有项目")
        self.open_existing_project_button.setStyleSheet("")
        self.open_existing_project_button.setMaximumWidth(240)
        mark_secondary_button(self.open_existing_project_button)
        self.open_existing_project_button.clicked.connect(self.open_existing_requested.emit)

        # Wrap in a centered container
        self._empty_wrapper = QWidget()
        empty_layout = QVBoxLayout()
        empty_layout.setContentsMargins(0, 56, 0, 0)
        empty_layout.setSpacing(12)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._empty_wrapper.setLayout(empty_layout)
        empty_layout.addWidget(self.empty_state, alignment=Qt.AlignmentFlag.AlignHCenter)
        empty_layout.addWidget(
            self.open_existing_project_button, alignment=Qt.AlignmentFlag.AlignHCenter
        )
        self._content_stack.addWidget(self._empty_wrapper)

        self._summary_parts.extend(
            [
                self.empty_state.title_label.text(),
                self.empty_state.description_label.text(),
                self.empty_state.action_button.text(),
                self.open_existing_project_button.text(),
            ]
        )

    def _show_no_match_state(self) -> None:
        self._scroll.hide()

        self._no_match_state = EmptyStatePanel(
            title="没有匹配项目",
            description="换个关键词，或清空筛选条件后再查看全部项目。",
            action_text="清空筛选",
        )
        self._no_match_state.setMaximumWidth(520)
        self._no_match_state.action_button.setMaximumWidth(240)
        self._no_match_state.action_button.clicked.connect(self._clear_filters)

        # Wrap in a centered container (same pattern as _show_empty_state)
        self._empty_wrapper = QWidget()
        empty_layout = QVBoxLayout()
        empty_layout.setContentsMargins(0, 56, 0, 0)
        empty_layout.setSpacing(12)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._empty_wrapper.setLayout(empty_layout)
        empty_layout.addWidget(self._no_match_state, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._content_stack.addWidget(self._empty_wrapper)

        self._summary_parts.extend(
            [
                self._no_match_state.title_label.text(),
                self._no_match_state.description_label.text(),
                self._no_match_state.action_button.text(),
            ]
        )

    def _clear_filters(self) -> None:
        self._search_edit.clear()
        self._status_filter.setCurrentText(self._STATUS_FILTER_ALL)
        self._sort_combo.setCurrentText(self._SORT_UPDATED)
        self._apply_filter()

    def _update_stats(self, items: list[ProjectLibraryItem]) -> None:
        counts: dict[str, int] = {"all": len(items), "completed": 0, "running": 0, "failed": 0}
        for item in items:
            if item.status == "已完成":
                counts["completed"] += 1
            elif item.status == "生成中":
                counts["running"] += 1
            elif item.status == "生成失败":
                counts["failed"] += 1
        label_map = {"all": "全部项目", "completed": "已完成", "running": "生成中", "failed": "生成失败"}
        for key, label in self._stat_labels.items():
            label.setText(f"{label_map[key]} {counts[key]}")

    def _apply_filter(self) -> None:
        """Filter and sort items, then rebuild cards."""
        search = self._search_edit.text().strip().lower()
        status_filter = self._status_filter.currentText()
        sort_key = self._sort_combo.currentText()

        filtered = list(self._all_items)

        # Search filter — matches name, languages, path, content type, status, output
        if search:
            filtered = [item for item in filtered if search in _searchable_text(item)]

        # Status filter
        if status_filter != self._STATUS_FILTER_ALL:
            filtered = [item for item in filtered if item.status == status_filter]

        # Sort
        if sort_key == self._SORT_NAME:
            filtered.sort(key=lambda i: i.name.lower())
        elif sort_key == self._SORT_STATUS:
            status_order = {"生成中": 0, "上次中断": 1, "未完成": 2, "未开始": 3, "生成失败": 4, "已完成": 5}
            filtered.sort(key=lambda i: status_order.get(i.status, 5))
        elif sort_key == self._SORT_ELAPSED:
            filtered.sort(key=lambda i: i.elapsed_seconds or 0, reverse=True)
        else:  # 最近更新 (default)
            filtered.sort(key=lambda i: i.updated_at, reverse=True)

        # Rebuild cards
        self._clear_project_widgets()
        self.open_project_buttons = []
        self.open_folder_buttons = []
        self.open_output_buttons = []
        self._summary_parts = []

        # No-match state: projects exist but filter yields nothing
        if not filtered and self._all_items:
            self._show_no_match_state()
            return

        self._scroll.show()

        for item in filtered:
            card = self._build_card(item)
            self._card_widgets.append(card)
            self._card_items.append(item)

        self._schedule_reflow_cards()

    def _build_card(self, item: ProjectLibraryItem) -> QWidget:
        """Build a single compact project card widget with fixed size."""
        card = QFrame()
        card.setStyleSheet("")
        mark_card(card)
        card.setFixedSize(self._CARD_WIDTH, self._CARD_HEIGHT)
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(3)

        # ── Header: name + status badge ──
        header = QHBoxLayout()
        header.setSpacing(6)
        name = QLabel(item.name)
        name.setMinimumWidth(1)
        mark_heading3(name)
        status_badge = QLabel(item.status)
        status_badge.setFixedHeight(24)
        status_badge.setMinimumWidth(40)
        status_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        _apply_project_status_badge(status_badge, item.status)
        header.addWidget(name, 1)
        header.addWidget(status_badge)
        layout.addLayout(header)

        # ── Info: content type + language on one line ──
        type_text = _content_type_text(item)
        language = _language_text(item)
        info_label = QLabel(f"{type_text}  ·  {language}")
        info_label.setObjectName("SecondaryText")
        mark_caption_text(info_label)
        layout.addWidget(info_label)

        # ── Status detail / elapsed time ──
        detail_text = item.status_detail or "尚未记录耗时"
        detail_label = QLabel(detail_text)
        detail_label.setObjectName("SecondaryText")
        mark_sub_text(detail_label)
        layout.addWidget(detail_label)

        # ── Output file ──
        output_text = _output_text(item)
        output_label = QLabel(output_text)
        output_label.setObjectName("SecondaryText")
        mark_sub_text(output_label)
        layout.addWidget(output_label)

        # ── Spacer ──
        layout.addStretch(1)

        # ── Actions ──
        actions = QHBoxLayout()
        actions.setSpacing(6)

        open_project = QPushButton("打开项目")
        open_project.setStyleSheet("")
        mark_compact_button(open_project)
        open_folder = QPushButton("文件夹")
        open_folder.setStyleSheet("")
        mark_compact_button(open_folder)
        open_project.clicked.connect(
            lambda _checked=False, p=item.path: self.open_project_requested.emit(p)
        )
        open_folder.clicked.connect(
            lambda _checked=False, p=item.path: self.open_folder_requested.emit(p)
        )
        actions.addWidget(open_project)
        actions.addWidget(open_folder)

        # Open output button (only if final output exists)
        if item.final_output_path is not None:
            open_output = QPushButton("成品")
            open_output.setStyleSheet("")
            mark_compact_button(open_output)
            open_output.clicked.connect(
                lambda _checked=False, p=item.final_output_path: self.open_output_requested.emit(p)
            )
            actions.addWidget(open_output)
            self.open_output_buttons.append(open_output)

        actions.addStretch()

        delete_button = QPushButton("删除")
        delete_button.setStyleSheet("")
        mark_compact_button(delete_button)
        delete_button.clicked.connect(
            lambda _checked=False, p=item.path: self.delete_project_requested.emit(p)
        )
        actions.addWidget(delete_button)
        layout.addLayout(actions)

        card.setLayout(layout)

        # Tooltip with full path
        card.setToolTip(str(item.path))

        # Store button references
        self.open_project_buttons.append(open_project)
        self.open_folder_buttons.append(open_folder)
        self._summary_parts.extend([item.name, item.status, item.status_detail, language])

        return card

    def _reflow_cards(self) -> None:
        """Reposition cards into rows that wrap based on available width.

        Uses a simple row-based layout: each row is an HBox, cards are
        distributed across rows so they wrap naturally without stretching.
        """
        # Remove existing rows from the flow layout
        while self._flow_layout.count():
            item = self._flow_layout.takeAt(0)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                w.setParent(None)
            else:
                # It's a layout (a row) — reparent its widgets too
                sub = item.layout()
                if sub is not None:
                    while sub.count():
                        sub_item = sub.takeAt(0)
                        sw = sub_item.widget() if sub_item is not None else None
                        if sw is not None:
                            sw.setParent(None)

        if not self._card_widgets:
            return

        scroll_width = max(self._scroll.viewport().width(), self._CARD_WIDTH)
        # How many cards fit per row
        cols = max(1, (scroll_width + 14) // (self._CARD_WIDTH + 14))

        row: QHBoxLayout | None = None
        for idx, card in enumerate(self._card_widgets):
            col_in_row = idx % cols
            if col_in_row == 0:
                row = QHBoxLayout()
                row.setSpacing(14)
                row.setAlignment(Qt.AlignmentFlag.AlignLeft)
                self._flow_layout.addLayout(row)
            if row is not None:
                row.addWidget(card)

        # Add stretch at the end of the last row to keep cards left-aligned
        if row is not None:
            row.addStretch()

        # Add a vertical stretch at the bottom so rows stay at the top
        self._flow_layout.addStretch(1)

    def _clear_project_widgets(self) -> None:
        """Remove all project cards and state panels from the layout."""
        for w in self._card_widgets:
            w.deleteLater()
        self._card_widgets.clear()
        self._card_items.clear()
        # Remove empty state / no-match state / empty wrapper from _content_stack
        # First item is always the scroll area
        while self._content_stack.count() > 1:
            item = self._content_stack.takeAt(1)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()


def _content_type_text(item: ProjectLibraryItem) -> str:
    return "音频" if item.content_type == "audio" else "视频"


def _language_text(item: ProjectLibraryItem) -> str:
    source = item.source_language or "未知"
    target = item.target_language or "未知"
    return f"{source} → {target}"


def _output_text(item: ProjectLibraryItem) -> str:
    if item.final_output_path is not None:
        return item.final_output_path.name
    return "暂无输出"


def _searchable_text(item: ProjectLibraryItem) -> str:
    """Build a lowercase string containing all searchable fields for an item."""
    parts: list[str] = [
        item.name,
        str(item.path),
        item.source_language or "",
        item.target_language or "",
        _language_text(item),
        _content_type_text(item),
        item.status,
        item.status_detail,
    ]
    if item.final_output_path is not None:
        parts.append(item.final_output_path.name)
        parts.append(str(item.final_output_path))
    return " ".join(part for part in parts if part).lower()


def _apply_project_status_badge(label: QLabel, status: str) -> None:
    mapped = {
        "已完成": "ready",
        "生成中": "applied",
        "上次中断": "warning",
        "生成失败": "failed",
        "未完成": "warning",
        "未开始": "unchecked",
    }.get(status, "unchecked")
    mark_status_badge(label, mapped)
