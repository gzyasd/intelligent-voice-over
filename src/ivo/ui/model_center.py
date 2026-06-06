from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ivo.core.model_presets import builtin_model_presets
from ivo.ui.advanced_model_settings import AdvancedModelSettings
from ivo.ui.theme import CARD_STYLE, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE


class ModelCenter(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.advanced_settings = AdvancedModelSettings()
        self.advanced_container = QWidget()
        self.advanced_container.setVisible(False)

        self.model_dir_edit = QLineEdit("models")
        self.model_dir_button = QPushButton("选择模型目录")
        self.check_models_button = QPushButton("一键检查模型")
        self.toggle_advanced_button = QPushButton("显示开发者设置")
        self.preset_combo = QComboBox()
        self._summary_parts: list[str] = []

        layout = QVBoxLayout()
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)
        title = QLabel("模型中心")
        title.setObjectName("PageTitle")
        subtitle = QLabel("选择一个推荐方案即可开始。高级配置默认隐藏。")
        subtitle.setObjectName("SecondaryText")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        for preset in builtin_model_presets():
            self.preset_combo.addItem(preset.display_name, preset.id)
            card = _preset_card(preset.display_name, preset.description)
            layout.addWidget(card)
            self._summary_parts.extend([preset.display_name, preset.description])

        self.model_dir_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.check_models_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.toggle_advanced_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        layout.addWidget(QLabel("模型目录"))
        layout.addWidget(self.model_dir_edit)
        layout.addWidget(self.model_dir_button)
        layout.addWidget(self.check_models_button)
        layout.addWidget(self.toggle_advanced_button)
        self._summary_parts.extend(["选择模型目录", "一键检查模型"])

        advanced_layout = QVBoxLayout()
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.addWidget(self.advanced_settings)
        self.advanced_container.setLayout(advanced_layout)
        layout.addWidget(self.advanced_container)
        layout.addStretch()
        self.setLayout(layout)
        self.toggle_advanced_button.clicked.connect(self.toggle_advanced_settings)

    def visible_summary_text(self) -> str:
        return "\n".join(self._summary_parts)

    def advanced_settings_visible(self) -> bool:
        return not self.advanced_container.isHidden()

    def toggle_advanced_settings(self) -> None:
        show = self.advanced_container.isHidden()
        self.advanced_container.setVisible(show)
        self.toggle_advanced_button.setText("隐藏开发者设置" if show else "显示开发者设置")


def _preset_card(title: str, description: str) -> QFrame:
    card = QFrame()
    card.setStyleSheet(CARD_STYLE)
    layout = QVBoxLayout()
    layout.setContentsMargins(16, 16, 16, 16)
    name = QLabel(title)
    name.setStyleSheet("font-size: 15px; font-weight: 700;")
    detail = QLabel(description)
    detail.setWordWrap(True)
    detail.setObjectName("SecondaryText")
    layout.addWidget(name)
    layout.addWidget(detail)
    card.setLayout(layout)
    return card
