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
    BORDER,
    DANGER,
    MODEL_CENTER_LIST_STYLE,
    SECONDARY_BUTTON_STYLE,
    SUCCESS,
    SURFACE,
    TEXT_SECONDARY,
    WARNING,
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
        color = {
            "ready": SUCCESS,
            "applied": SUCCESS,
            "warning": WARNING,
            "missing": DANGER,
            "failed": DANGER,
            "draft": WARNING,
        }.get(status, TEXT_SECONDARY)
        self.setStyleSheet(
            f"""
            QLabel {{
                color: {color};
                background: {SURFACE};
                border: 1px solid {color};
                border-radius: 10px;
                padding: 3px 9px;
                font-size: 12px;
                font-weight: 600;
            }}
            """
        )


class ConfigSummaryCard(QFrame):
    edit_requested = Signal()
    copy_requested = Signal()
    apply_requested = Signal()
    delete_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setStyleSheet(MODEL_CENTER_LIST_STYLE)
        self.title_label = QLabel("尚未选择配置")
        self.title_label.setStyleSheet("font-size: 20px; font-weight: 700;")
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
        self.edit_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.copy_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.delete_button.setStyleSheet(
            f"""
            QPushButton {{
                background: {SURFACE};
                color: {DANGER};
                border: 1px solid {BORDER};
                border-radius: 10px;
                padding: 9px 14px;
            }}
            """
        )
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
        actions.addWidget(self.delete_button)
        actions.addStretch()
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
        self.delete_button.setVisible(not config.builtin)


class StageFlowEditor(QWidget):
    stage_edit_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._cards: dict[str, QLabel] = {}
        self._buttons: dict[str, QPushButton] = {}
        self._stages: list[VisualStageConfig] = []
        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(8)
        self.setLayout(self._layout)

    def set_stages(self, stages: list[VisualStageConfig]) -> None:
        self._stages = stages
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._cards.clear()
        self._buttons.clear()
        for stage in stages:
            row = QFrame()
            row.setStyleSheet(
                f"""
                QFrame {{
                    background: {SURFACE};
                    border: 1px solid {BORDER};
                    border-radius: 10px;
                }}
                """
            )
            label = QLabel(_stage_summary(stage))
            label.setWordWrap(True)
            edit = QPushButton("编辑阶段")
            edit.setStyleSheet(SECONDARY_BUTTON_STYLE)
            edit.clicked.connect(lambda _checked=False, stage_id=stage.stage: self.stage_edit_requested.emit(stage_id))
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(12, 10, 12, 10)
            row_layout.addWidget(label)
            row_layout.addWidget(edit)
            row.setLayout(row_layout)
            self._layout.addWidget(row)
            self._cards[stage.stage] = label
            self._buttons[stage.stage] = edit
        self._layout.addStretch()

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
