from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ivo.core.project import DubbingProject
from ivo.core.speakers import SpeakerProfile
from ivo.core.timeline import DubbingSegment
from ivo.ui.theme import mark_card


VALID_STATUSES: set[str] = {
    "pending",
    "running",
    "needs_review",
    "approved",
    "failed",
    "rendered",
}

STATUS_LABELS: dict[str, str] = {
    "pending": "待处理",
    "running": "处理中",
    "needs_review": "待审核",
    "approved": "已审核",
    "failed": "失败",
    "rendered": "已生成",
}

QUALITY_FILTERS: dict[str, str] = {
    "all": "全部",
    "failed": "失败",
    "duration_too_long": "配音偏长",
    "duration_too_short": "配音偏短",
    "silent_audio": "静音",
    "missing_reference_audio": "缺参考音频",
    "speaker_ambiguous": "说话人不确定",
}


class TimelineEditor(QWidget):
    regenerate_requested = Signal(str)

    COLUMN_ID = 0
    COLUMN_SPEAKER = 1
    COLUMN_SOURCE_TEXT = 2
    COLUMN_TARGET_TEXT = 3
    COLUMN_EMOTION = 4
    COLUMN_STYLE_PROMPT = 5
    COLUMN_STATUS = 6
    COLUMN_QUALITY_FLAGS = 7
    COLUMN_ACTION = 8
    HEADERS = [
        "\u7247\u6bb5",
        "\u8bf4\u8bdd\u4eba",
        "\u539f\u6587",
        "\u4e2d\u6587",
        "\u60c5\u7eea",
        "\u98ce\u683c\u63d0\u793a",
        "\u72b6\u6001",
        "\u8d28\u91cf\u6807\u8bb0",
        "\u64cd\u4f5c",
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project: DubbingProject | None = None
        self.save_buttons: list[QPushButton] = []
        self.regenerate_buttons: list[QPushButton] = []
        self.set_reference_buttons: list[QPushButton] = []
        self.clear_reference_buttons: list[QPushButton] = []
        self.rename_speaker_buttons: list[QPushButton] = []
        self._all_segments: list[DubbingSegment] = []
        self._visible_segments: list[DubbingSegment] = []
        self._quality_filter = "all"
        self.quality_filter_combo = QComboBox()
        self.quality_filter_combo.addItems(list(QUALITY_FILTERS.values()))
        self.quality_filter_combo.currentIndexChanged.connect(self._handle_quality_filter_changed)
        self.review_summary_label = QLabel("总片段：0；已审核：0；已生成：0；质量标记：0")
        self.quality_summary_label = QLabel("质量摘要：暂无质量问题")
        self.detail_source_label = QLabel("原文：请选择一句台词")
        self.detail_target_label = QLabel("中文：请选择一句台词")
        self.detail_speaker_label = QLabel("说话人：-")
        self.detail_emotion_label = QLabel("情绪：-")
        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self._refresh_detail_from_selection)
        self.table.setAlternatingRowColors(True)
        self._hide_technical_columns()

        layout = QVBoxLayout()
        layout.addWidget(self.quality_filter_combo)
        layout.addWidget(self.review_summary_label)
        layout.addWidget(self.quality_summary_label)
        layout.addWidget(self._build_detail_panel())
        layout.addWidget(self.table)
        self.setLayout(layout)

    def set_project(self, project: DubbingProject) -> None:
        self.project = project
        self.set_segments(project.timeline.list_segments())

    def set_segments(self, segments: list[DubbingSegment]) -> None:
        self._all_segments = segments
        visible_segments = self._filtered_segments(segments)
        self._visible_segments = visible_segments
        self.save_buttons = []
        self.regenerate_buttons = []
        self.set_reference_buttons = []
        self.clear_reference_buttons = []
        self.rename_speaker_buttons = []
        self.quality_summary_label.setText(_build_quality_summary(segments))
        self.review_summary_label.setText(_build_review_summary(segments))
        self.table.setRowCount(len(visible_segments))
        for row, segment in enumerate(visible_segments):
            values = [
                segment.id,
                self._speaker_display_text(segment.speaker_id),
                segment.source_text,
                segment.target_text,
                segment.emotion or "",
                segment.style_prompt or "",
                _status_label(segment.status),
                ", ".join(_quality_flag_label(flag) for flag in segment.quality_flags),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in {
                    self.COLUMN_ID,
                    self.COLUMN_SOURCE_TEXT,
                    self.COLUMN_QUALITY_FLAGS,
                }:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if column == self.COLUMN_SPEAKER:
                    item.setData(Qt.ItemDataRole.UserRole, segment.speaker_id)
                self.table.setItem(row, column, item)
            self.table.setCellWidget(row, self.COLUMN_ACTION, self._build_action_widget(row, segment.id))
        if visible_segments:
            self._refresh_detail_for_segment(visible_segments[0])
        else:
            self._clear_detail_panel()

    def _build_detail_panel(self) -> QFrame:
        panel = QFrame()
        panel.setStyleSheet("")
        mark_card(panel)
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.addWidget(QLabel("当前句子"))
        layout.addWidget(self.detail_source_label)
        layout.addWidget(self.detail_target_label)
        layout.addWidget(self.detail_speaker_label)
        layout.addWidget(self.detail_emotion_label)
        panel.setLayout(layout)
        return panel

    def _hide_technical_columns(self) -> None:
        self.table.setColumnHidden(self.COLUMN_ID, True)
        self.table.setColumnHidden(self.COLUMN_STYLE_PROMPT, True)
        self.table.setColumnHidden(self.COLUMN_QUALITY_FLAGS, True)

    def _refresh_detail_from_selection(self) -> None:
        selected_rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if not selected_rows:
            return
        row = selected_rows[0]
        if row < 0 or row >= len(self._visible_segments):
            return
        self._refresh_detail_for_segment(self._visible_segments[row])

    def _refresh_detail_for_segment(self, segment: DubbingSegment) -> None:
        self.detail_source_label.setText(f"原文：{segment.source_text}")
        self.detail_target_label.setText(f"中文：{segment.target_text}")
        self.detail_speaker_label.setText(f"说话人：{self._speaker_display_text(segment.speaker_id)}")
        self.detail_emotion_label.setText(f"情绪：{segment.emotion or '未标注'}")

    def _clear_detail_panel(self) -> None:
        self.detail_source_label.setText("原文：请选择一句台词")
        self.detail_target_label.setText("中文：请选择一句台词")
        self.detail_speaker_label.setText("说话人：-")
        self.detail_emotion_label.setText("情绪：-")

    def _build_action_widget(self, row: int, segment_id: str) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        save_button = QPushButton("\u4fdd\u5b58")
        save_button.setAccessibleName("保存")
        save_button.setToolTip("保存当前行修改")
        regenerate_button = QPushButton("\u91cd\u751f\u6210")
        regenerate_button.setAccessibleName("重生成")
        regenerate_button.setToolTip("重新生成该片段配音")
        set_reference_button = QPushButton("\u8bbe\u53c2\u8003")
        set_reference_button.setAccessibleName("设参考")
        set_reference_button.setToolTip("设为说话人参考音频")
        clear_reference_button = QPushButton("\u6e05\u53c2\u8003")
        clear_reference_button.setAccessibleName("清参考")
        clear_reference_button.setToolTip("清除说话人参考音频")
        rename_speaker_button = QPushButton("\u91cd\u547d\u540d")
        rename_speaker_button.setAccessibleName("重命名")
        rename_speaker_button.setToolTip("重命名说话人")
        save_button.clicked.connect(lambda _checked=False, row=row: self.save_row(row))
        regenerate_button.clicked.connect(
            lambda _checked=False, segment_id=segment_id: self.regenerate_requested.emit(segment_id)
        )
        set_reference_button.clicked.connect(
            lambda _checked=False, segment_id=segment_id: self.set_speaker_reference_segment(segment_id)
        )
        clear_reference_button.clicked.connect(
            lambda _checked=False, segment_id=segment_id: self.clear_speaker_reference_segment(segment_id)
        )
        rename_speaker_button.clicked.connect(
            lambda _checked=False, segment_id=segment_id: self.rename_speaker_from_segment(segment_id)
        )
        layout.addWidget(save_button)
        layout.addWidget(regenerate_button)
        layout.addWidget(set_reference_button)
        layout.addWidget(clear_reference_button)
        layout.addWidget(rename_speaker_button)
        widget.setLayout(layout)
        self.save_buttons.append(save_button)
        self.regenerate_buttons.append(regenerate_button)
        self.set_reference_buttons.append(set_reference_button)
        self.clear_reference_buttons.append(clear_reference_button)
        self.rename_speaker_buttons.append(rename_speaker_button)
        return widget

    def save_row(self, row: int) -> DubbingSegment:
        if self.project is None:
            raise RuntimeError("请先创建或打开项目。")

        segment_id = self._cell_text(row, self.COLUMN_ID)
        status = _status_value(self._cell_text(row, self.COLUMN_STATUS))
        if status not in VALID_STATUSES:
            raise ValueError(f"无效片段状态：{status}")
        current = self.project.timeline.get_segment(segment_id)
        speaker_id = self._speaker_id_for_row(row)
        target_text = self._cell_text(row, self.COLUMN_TARGET_TEXT)
        style_prompt = self._optional_cell_text(row, self.COLUMN_STYLE_PROMPT)
        editable_changed = (
            speaker_id != current.speaker_id
            or target_text != current.target_text
            or style_prompt != current.style_prompt
        )
        if current.status == "rendered" and editable_changed:
            status = "needs_review"
            self._remove_rendered_audio(segment_id)

        return self.project.timeline.update_segment(
            segment_id,
            speaker_id=speaker_id,
            target_text=target_text,
            emotion=self._optional_cell_text(row, self.COLUMN_EMOTION),
            style_prompt=style_prompt,
            status=status,
        )

    def set_speaker_reference_segment(self, segment_id: str) -> SpeakerProfile:
        if self.project is None:
            raise RuntimeError("请先创建或打开项目。")
        segment = self.project.timeline.get_segment(segment_id)
        profile = self.project.speakers.set_reference_segment(
            segment.speaker_id,
            segment.id,
            display_name=segment.speaker_id,
        )
        self.set_project(self.project)
        return profile

    def clear_speaker_reference_segment(self, segment_id: str) -> SpeakerProfile:
        if self.project is None:
            raise RuntimeError("请先创建或打开项目。")
        segment = self.project.timeline.get_segment(segment_id)
        profile = self.project.speakers.clear_reference_segment(segment.speaker_id, segment.id)
        self.set_project(self.project)
        return profile

    def rename_speaker_from_segment(self, segment_id: str) -> SpeakerProfile | None:
        if self.project is None:
            raise RuntimeError("请先创建或打开项目。")
        segment = self.project.timeline.get_segment(segment_id)
        display_name, accepted = QInputDialog.getText(
            self,
            "\u91cd\u547d\u540d\u89d2\u8272",
            "\u89d2\u8272\u540d\u79f0",
            text=self._speaker_display_text(segment.speaker_id),
        )
        if not accepted or not display_name.strip():
            return None
        profile = self.project.speakers.rename(segment.speaker_id, display_name.strip())
        self.set_project(self.project)
        return profile

    def _cell_text(self, row: int, column: int) -> str:
        item = self.table.item(row, column)
        return item.text().strip() if item is not None else ""

    def _optional_cell_text(self, row: int, column: int) -> str | None:
        value = self._cell_text(row, column)
        return value or None

    def _speaker_id_for_row(self, row: int) -> str:
        item = self.table.item(row, self.COLUMN_SPEAKER)
        if item is None:
            return ""
        text = item.text().strip()
        stored_speaker_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(stored_speaker_id, str) and self._speaker_display_text(stored_speaker_id) == text:
            return stored_speaker_id
        return text

    def _speaker_display_text(self, speaker_id: str) -> str:
        if self.project is None:
            return speaker_id
        profile = self.project.speakers.get(speaker_id)
        if profile is None:
            return speaker_id
        return profile.display_name

    def set_quality_filter(self, quality_filter: str) -> None:
        self._quality_filter = quality_filter
        label = QUALITY_FILTERS.get(quality_filter)
        if label is not None:
            self.quality_filter_combo.setCurrentText(label)
        self.set_segments(self._all_segments)

    def visible_segment_ids(self) -> list[str]:
        ids: list[str] = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, self.COLUMN_ID)
            if item is not None:
                ids.append(item.text())
        return ids

    def _filtered_segments(self, segments: list[DubbingSegment]) -> list[DubbingSegment]:
        if self._quality_filter == "all":
            return segments
        if self._quality_filter == "failed":
            return [segment for segment in segments if segment.status == "failed"]
        return [
            segment
            for segment in segments
            if self._quality_filter in segment.quality_flags
        ]

    def _handle_quality_filter_changed(self, index: int) -> None:
        filters = list(QUALITY_FILTERS.keys())
        if index < 0 or index >= len(filters):
            return
        self._quality_filter = filters[index]
        self.set_segments(self._all_segments)

    def _remove_rendered_audio(self, segment_id: str) -> None:
        if self.project is None:
            return
        audio_path = self.project.path / "work" / "generated_segments" / f"{segment_id}.wav"
        if audio_path.is_file():
            audio_path.unlink()


def _quality_flag_label(flag: str) -> str:
    labels = {
        "duration_too_short": "配音偏短",
        "duration_too_long": "配音偏长",
        "duration_mismatch": "时长不匹配",
        "tts_retried": "已自动重试",
        "duration_ok": "时长正常",
        "silent_audio": "音频静音",
        "missing_reference_audio": "缺少参考音频",
        "speaker_unmatched": "说话人未匹配",
        "speaker_ambiguous": "说话人不确定",
    }
    return labels.get(flag, flag)


def _status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


def _status_value(label_or_status: str) -> str:
    if label_or_status in VALID_STATUSES:
        return label_or_status
    for status, label in STATUS_LABELS.items():
        if label == label_or_status:
            return status
    return label_or_status


def _build_review_summary(segments: list[DubbingSegment]) -> str:
    total_segments = len(segments)
    reviewed_segments = sum(1 for segment in segments if segment.status in {"approved", "rendered"})
    rendered_segments = sum(1 for segment in segments if segment.status == "rendered")
    quality_flagged_segments = sum(1 for segment in segments if segment.quality_flags)
    return (
        f"总片段：{total_segments}；已审核：{reviewed_segments}；"
        f"已生成：{rendered_segments}；质量标记：{quality_flagged_segments}"
    )


def _build_quality_summary(segments: list[DubbingSegment]) -> str:
    counts: dict[str, int] = {}
    for segment in segments:
        for flag in segment.quality_flags:
            counts[flag] = counts.get(flag, 0) + 1
    if not counts:
        return "质量摘要：暂无质量问题"
    joined = "; ".join(f"{_quality_flag_label(flag)}: {count}" for flag, count in counts.items())
    return f"质量摘要：{joined}"
