from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from ivo.pipeline.progress import PipelineProgressEvent, PipelineStage, STAGE_LABELS, STAGE_ORDER
from ivo.ui.theme import CARD_STYLE, DANGER, SUCCESS, TEXT_SECONDARY, WARNING

STATUS_TEXT = {
    "started": "进行中",
    "progress": "进行中",
    "completed": "已完成",
    "failed": "失败",
    "skipped": "已跳过",
}


class GenerationProgressPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._stage_labels: dict[PipelineStage, QLabel] = {}
        self._stage_statuses: dict[PipelineStage, str] = {
            stage: "pending" for stage in STAGE_ORDER
        }

        self.overall_progress = QProgressBar()
        self.overall_progress.setRange(0, 100)
        self.current_stage_label = QLabel("等待开始")
        self.current_stage_label.setStyleSheet("font-size: 18px; font-weight: 700;")
        self.current_item_label = QLabel("尚未处理句子")
        self.current_item_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self.detail_label = QLabel("创建项目后点击开始生成。")
        self.detail_label.setWordWrap(True)
        self.failure_label = QLabel("")
        self.failure_label.setWordWrap(True)
        self.failure_label.setStyleSheet(f"color: {DANGER}; font-weight: 600;")
        self.recovery_hint_label = QLabel("")
        self.recovery_hint_label.setWordWrap(True)
        self.recovery_hint_label.setStyleSheet(f"color: {TEXT_SECONDARY};")

        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(12)
        card = QFrame()
        card.setStyleSheet(CARD_STYLE)
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(10)
        card_layout.addWidget(self.current_stage_label)
        card_layout.addWidget(self.overall_progress)
        card_layout.addWidget(self.current_item_label)
        card_layout.addWidget(self.detail_label)
        card_layout.addWidget(self.failure_label)
        card_layout.addWidget(self.recovery_hint_label)
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

    def reset(self) -> None:
        self.overall_progress.setValue(0)
        self.current_stage_label.setText("等待开始")
        self.current_item_label.setText("尚未处理句子")
        self.detail_label.setText("创建项目后点击开始生成。")
        self.failure_label.clear()
        self.recovery_hint_label.clear()
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
        return SUCCESS
    if status == "failed":
        return DANGER
    if status in {"started", "progress"}:
        return WARNING
    return TEXT_SECONDARY
