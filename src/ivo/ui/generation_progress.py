from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ivo.pipeline.progress import PipelineProgressEvent, PipelineStage, STAGE_LABELS, STAGE_ORDER
from ivo.ui.theme import (
    active_color,
    mark_card,
    mark_elapsed_label,
    mark_heading2,
    mark_progress_idle,
    mark_progress_paused,
    mark_progress_running,
)

STATUS_TEXT = {
    "started": "进行中",
    "progress": "进行中",
    "completed": "已完成",
    "failed": "失败",
    "skipped": "已跳过",
}


class GenerationProgressPanel(QWidget):
    pause_requested = Signal()
    resume_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._stage_labels: dict[PipelineStage, QLabel] = {}
        self._stage_statuses: dict[PipelineStage, str] = {
            stage: "pending" for stage in STAGE_ORDER
        }

        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.current_stage_label = QLabel("等待开始")
        mark_heading2(self.current_stage_label)
        self.elapsed_label = QLabel("已用时 00:00")
        mark_elapsed_label(self.elapsed_label)
        self.current_item_label = QLabel("尚未处理句子")
        self.current_item_label.setObjectName("SecondaryText")
        self.detail_label = QLabel("创建项目后点击开始生成。")
        self.detail_label.setWordWrap(True)
        self.failure_label = QLabel("")
        self.failure_label.setWordWrap(True)
        self.failure_label.setObjectName("DangerText")
        self.recovery_hint_label = QLabel("")
        self.recovery_hint_label.setWordWrap(True)
        self.recovery_hint_label.setObjectName("SecondaryText")
        self.pause_button = QPushButton("暂停")
        self.resume_button = QPushButton("继续")
        self.pause_button.clicked.connect(self.pause_requested.emit)
        self.resume_button.clicked.connect(self.resume_requested.emit)
        self.set_idle_controls()

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)
        card = QFrame()
        card.setStyleSheet("")
        mark_card(card)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)
        card_layout.addWidget(self.current_stage_label)
        card_layout.addWidget(self.elapsed_label)
        card_layout.addWidget(self.overall_progress)
        card_layout.addWidget(self.current_item_label)
        card_layout.addWidget(self.detail_label)
        card_layout.addWidget(self.failure_label)
        card_layout.addWidget(self.recovery_hint_label)
        controls = QHBoxLayout()
        controls.addWidget(self.pause_button)
        controls.addWidget(self.resume_button)
        controls.addStretch()
        card_layout.addLayout(controls)
        for stage in STAGE_ORDER:
            label = QLabel(f"{STAGE_LABELS[stage]}：等待中")
            label.setObjectName(f"stage_{stage}")
            card_layout.addWidget(label)
            self._stage_labels[stage] = label
        card.setLayout(card_layout)
        root_layout.addWidget(card)
        self.setLayout(root_layout)

    def handle_progress(self, event: PipelineProgressEvent) -> None:
        self.overall_progress.setValue(event.overall_percent)
        self.current_stage_label.setText(event.stage_label)
        self.detail_label.setText(event.message or event.stage_label)
        if event.current_item is not None and event.total_items is not None:
            self.current_item_label.setText(f"第 {event.current_item} / {event.total_items} 句")
        elif event.stage != "tts":
            self.current_item_label.setText("正在处理当前阶段")

        self._stage_statuses[event.stage] = event.status
        self._refresh_stage_label(event.stage)

        if event.status == "failed":
            self.failure_label.setText(f"{event.stage_label}失败：{event.message}")
            self.recovery_hint_label.setText(
                "请先到模型中心检查模型目录、LM Studio 或在线 API 配置，然后重试失败阶段。"
            )
        elif event.status == "completed":
            self.failure_label.clear()
            self.recovery_hint_label.clear()

    def stage_status(self, stage: PipelineStage) -> str:
        return self._stage_statuses[stage]

    def set_elapsed_seconds(self, seconds: int) -> None:
        self.elapsed_label.setText(f"已用时 {_format_elapsed(seconds)}")

    def set_idle_controls(self) -> None:
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(False)
        self.overall_progress.setStyleSheet("")
        mark_progress_idle(self.overall_progress)

    def set_running_controls(self) -> None:
        self.pause_button.setEnabled(True)
        self.resume_button.setEnabled(False)
        self.overall_progress.setStyleSheet("")
        mark_progress_running(self.overall_progress)

    def set_paused_controls(self) -> None:
        self.pause_button.setEnabled(False)
        self.resume_button.setEnabled(True)
        self.overall_progress.setStyleSheet("")
        mark_progress_paused(self.overall_progress)

    def set_finished_controls(self) -> None:
        self.set_idle_controls()

    def reset(self) -> None:
        self.overall_progress.setValue(0)
        self.current_stage_label.setText("等待开始")
        self.set_elapsed_seconds(0)
        self.current_item_label.setText("尚未处理句子")
        self.detail_label.setText("创建项目后点击开始生成。")
        self.failure_label.clear()
        self.recovery_hint_label.clear()
        self.set_idle_controls()
        for stage in STAGE_ORDER:
            self._stage_statuses[stage] = "pending"
            self._refresh_stage_label(stage)

    def _refresh_stage_label(self, stage: PipelineStage) -> None:
        status = self._stage_statuses[stage]
        text = STATUS_TEXT.get(status, "等待中")
        color = _status_color(status)
        self._stage_labels[stage].setText(f"{STAGE_LABELS[stage]}：{text}")
        self._stage_labels[stage].setStyleSheet(f"color: {color};")


def _status_color(status: str) -> str:
    if status == "completed":
        return active_color("success")
    if status == "failed":
        return active_color("danger")
    if status in {"started", "progress"}:
        return active_color("warning")
    return active_color("text_secondary")


def _format_elapsed(seconds: int) -> str:
    minutes, rest = divmod(max(0, seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{rest:02d}"
    return f"{minutes:02d}:{rest:02d}"
