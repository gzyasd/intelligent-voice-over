from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ivo.core.visual_model_config import VisualModelConfig, VisualStageConfig
from ivo.ui.theme import (
    mark_card,
    mark_card_disabled,
    mark_card_highlighted,
    mark_heading2,
    mark_secondary_button,
    mark_status_badge,
)


SERVICE_TYPE_LABELS = {
    "local": "本地模型",
    "http": "在线 API",
    "disabled": "跳过",
}


class StatusPill(QLabel):
    def __init__(self, text: str = "尚未检查", status: str = "unchecked") -> None:
        super().__init__(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_status(text, status)

    def set_status(self, text: str, status: str) -> None:
        self.setText(text)
        mapped = {
            "ready": "ready",
            "applied": "applied",
            "warning": "warning",
            "draft": "warning",
            "missing": "missing",
            "failed": "failed",
        }.get(status, "unchecked")
        mark_status_badge(self, mapped)


class ConfigSummaryCard(QFrame):
    edit_requested = Signal()
    copy_requested = Signal()
    apply_requested = Signal()
    delete_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet("")
        mark_card(self)
        self.title_label = QLabel("尚未选择配置")
        mark_heading2(self.title_label)
        self.description_label = QLabel("")
        self.description_label.setWordWrap(True)
        self.description_label.setObjectName("SecondaryText")
        self.status_label = StatusPill("尚未检查", "unchecked")
        self.tags_label = QLabel("")
        self.tags_label.setWordWrap(True)
        self.tags_label.setObjectName("SecondaryText")
        self.models_label = QLabel("")
        self.models_label.setWordWrap(True)
        self.models_label.setObjectName("SecondaryText")
        self.edit_button = QPushButton("编辑")
        self.copy_button = QPushButton("复制为我的配置")
        self.apply_button = QPushButton("应用此配置")
        self.delete_button = QPushButton("删除")
        self.edit_button.setStyleSheet("")
        mark_secondary_button(self.edit_button)
        self.copy_button.setStyleSheet("")
        mark_secondary_button(self.copy_button)
        self.delete_button.setStyleSheet("")
        mark_secondary_button(self.delete_button)
        self.edit_button.clicked.connect(self.edit_requested.emit)
        self.copy_button.clicked.connect(self.copy_requested.emit)
        self.apply_button.clicked.connect(self.apply_requested.emit)
        self.delete_button.clicked.connect(self.delete_requested.emit)

        header = QHBoxLayout()
        header.addWidget(self.title_label)
        header.addStretch()
        header.addWidget(self.status_label)
        actions = QHBoxLayout()
        actions.addWidget(self.apply_button)
        actions.addWidget(self.edit_button)
        actions.addWidget(self.copy_button)
        actions.addStretch()
        actions.addWidget(self.delete_button)
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addLayout(header)
        layout.addWidget(self.description_label)
        layout.addWidget(self.tags_label)
        layout.addWidget(self.models_label)
        layout.addLayout(actions)
        self.setLayout(layout)

    def set_config(self, config: VisualModelConfig, *, applied: bool) -> None:
        self.title_label.setText(config.display_name)
        self.description_label.setText(config.description or "这是一份可视化模型配置。")
        status_text = "已应用" if applied else _check_status_text(config.last_check_status)
        status = "applied" if applied else config.last_check_status
        self.status_label.set_status(status_text, status)
        self.tags_label.setText("标签：" + " · ".join(config.tags or [config.quality_label]))
        models = "、".join(config.recommended_models) or "按阶段设置选择模型或服务"
        self.models_label.setText(f"推荐模型与服务：{models}")
        # 内置配置不能直接编辑或删除，需要先复制为自定义配置
        self.edit_button.setVisible(not config.builtin)
        self.delete_button.setVisible(not config.builtin)


class StageFlowEditor(QWidget):
    stage_edit_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._cards: dict[str, QLabel] = {}
        self._buttons: dict[str, QPushButton] = {}
        self._rows: dict[str, QFrame] = {}
        self._stages: list[VisualStageConfig] = []
        self._highlighted_stage_id: str | None = None
        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self.setLayout(self._layout)

    def set_stages(self, stages: list[VisualStageConfig]) -> None:
        self._stages = stages
        self._highlighted_stage_id = None
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards.clear()
        self._buttons.clear()
        self._rows.clear()
        for stage in stages:
            row = QFrame()
            row.setObjectName(f"stage_row_{stage.stage}")
            if stage.enabled:
                row.setStyleSheet("")
                mark_card(row)
            else:
                row.setStyleSheet("")
                mark_card_disabled(row)
            label = QLabel(_stage_summary(stage))
            label.setWordWrap(True)
            if not stage.enabled:
                label.setObjectName("SecondaryText")
            edit = QPushButton("编辑阶段")
            edit.setStyleSheet("")
            mark_secondary_button(edit)
            edit.setFixedWidth(80)
            edit.clicked.connect(lambda _checked=False, stage_id=stage.stage: self.stage_edit_requested.emit(stage_id))
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.addWidget(label)
            row_layout.addWidget(edit)
            row.setLayout(row_layout)
            self._layout.addWidget(row)
            self._cards[stage.stage] = label
            self._buttons[stage.stage] = edit
            self._rows[stage.stage] = row
        self._layout.addStretch()

    def highlight_stage(self, stage_id: str | None) -> None:
        """高亮显示正在编辑的阶段卡片"""
        # 取消之前的高亮
        if self._highlighted_stage_id and self._highlighted_stage_id in self._rows:
            prev_row = self._rows[self._highlighted_stage_id]
            prev_stage = next(
                (s for s in self._stages if s.stage == self._highlighted_stage_id), None
            )
            if prev_stage:
                prev_row.setStyleSheet("")
                if prev_stage.enabled:
                    mark_card(prev_row)
                else:
                    mark_card_disabled(prev_row)
        # 设置新高亮
        self._highlighted_stage_id = stage_id
        if stage_id and stage_id in self._rows:
            row = self._rows[stage_id]
            row.setStyleSheet("")
            mark_card_highlighted(row)

    def summary_text(self) -> str:
        return "\n".join(_stage_summary(stage) for stage in self._stages)


def _stage_summary(stage: VisualStageConfig) -> str:
    service = SERVICE_TYPE_LABELS.get(stage.service_type, stage.service_type)
    enabled = "启用" if stage.enabled else "关闭"
    provider = stage.provider_name or "未选择"
    validation = _check_status_text(stage.validation_status)
    return f"{stage.label}：{service} · {provider} · {enabled} · {validation}"


def _check_status_text(status: str) -> str:
    return {
        "ready": "可用",
        "warning": "需检查",
        "missing": "缺少模型",
        "failed": "不可用",
        "draft": "草稿",
        "unchecked": "尚未检查",
    }.get(status, "尚未检查")
