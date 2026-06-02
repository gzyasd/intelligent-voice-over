from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ivo.core.project import DubbingProject
from ivo.core.timeline import DubbingSegment


VALID_STATUSES: set[str] = {
    "pending",
    "running",
    "needs_review",
    "approved",
    "failed",
    "rendered",
}


class TimelineEditor(QWidget):
    regenerate_requested = Signal(str)

    COLUMN_ID = 0
    COLUMN_SPEAKER = 1
    COLUMN_SOURCE_TEXT = 2
    COLUMN_TARGET_TEXT = 3
    COLUMN_EMOTION = 4
    COLUMN_STATUS = 5
    COLUMN_QUALITY_FLAGS = 6
    COLUMN_ACTION = 7
    HEADERS = [
        "\u7247\u6bb5",
        "\u8bf4\u8bdd\u4eba",
        "\u539f\u6587",
        "\u4e2d\u6587",
        "\u60c5\u7eea",
        "\u72b6\u6001",
        "\u8d28\u91cf\u6807\u8bb0",
        "\u64cd\u4f5c",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project: DubbingProject | None = None
        self.save_buttons: list[QPushButton] = []
        self.regenerate_buttons: list[QPushButton] = []
        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)

        layout = QVBoxLayout()
        layout.addWidget(self.table)
        self.setLayout(layout)

    def set_project(self, project: DubbingProject) -> None:
        self.project = project
        self.set_segments(project.timeline.list_segments())

    def set_segments(self, segments: list[DubbingSegment]) -> None:
        self.save_buttons = []
        self.regenerate_buttons = []
        self.table.setRowCount(len(segments))
        for row, segment in enumerate(segments):
            values = [
                segment.id,
                segment.speaker_id,
                segment.source_text,
                segment.target_text,
                segment.emotion or "",
                segment.status,
                ", ".join(segment.quality_flags),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {
                    self.COLUMN_ID,
                    self.COLUMN_SOURCE_TEXT,
                    self.COLUMN_QUALITY_FLAGS,
                }:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, column, item)
            self.table.setCellWidget(row, self.COLUMN_ACTION, self._build_action_widget(row, segment.id))

    def _build_action_widget(self, row: int, segment_id: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        save_button = QPushButton("\u4fdd\u5b58")
        regenerate_button = QPushButton("\u91cd\u751f\u6210")
        save_button.clicked.connect(lambda _checked=False, row=row: self.save_row(row))
        regenerate_button.clicked.connect(
            lambda _checked=False, segment_id=segment_id: self.regenerate_requested.emit(segment_id)
        )
        layout.addWidget(save_button)
        layout.addWidget(regenerate_button)
        widget.setLayout(layout)
        self.save_buttons.append(save_button)
        self.regenerate_buttons.append(regenerate_button)
        return widget

    def save_row(self, row: int) -> DubbingSegment:
        if self.project is None:
            raise RuntimeError("Timeline editor has no project.")

        segment_id = self._cell_text(row, self.COLUMN_ID)
        status = self._cell_text(row, self.COLUMN_STATUS)
        if status not in VALID_STATUSES:
            raise ValueError(f"invalid segment status: {status}")

        return self.project.timeline.update_segment(
            segment_id,
            speaker_id=self._cell_text(row, self.COLUMN_SPEAKER),
            target_text=self._cell_text(row, self.COLUMN_TARGET_TEXT),
            emotion=self._optional_cell_text(row, self.COLUMN_EMOTION),
            status=status,
        )

    def _cell_text(self, row: int, column: int) -> str:
        item = self.table.item(row, column)
        return item.text().strip() if item is not None else ""

    def _optional_cell_text(self, row: int, column: int) -> str | None:
        value = self._cell_text(row, column)
        return value or None
