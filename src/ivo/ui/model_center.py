from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ivo.core.model_presets import builtin_model_presets, get_model_preset
from ivo.ui.advanced_model_settings import AdvancedModelSettings
from ivo.ui.empty_states import EmptyStatePanel
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
        self.model_hint_panel = EmptyStatePanel(
            title="模型目录尚未检查",
            description="请选择模型目录后点击一键检查。缺少模型时，这里会告诉你应该放到哪个文件夹。",
            action_text="一键检查模型",
        )
        self.model_hint_panel.setVisible(False)
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
        layout.addWidget(self.model_hint_panel)
        layout.addWidget(self.toggle_advanced_button)
        self._summary_parts.extend(["选择模型目录", "一键检查模型"])

        advanced_layout = QVBoxLayout()
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.addWidget(self.advanced_settings)
        self.advanced_container.setLayout(advanced_layout)
        layout.addWidget(self.advanced_container)
        layout.addStretch()
        self.setLayout(layout)
        self.model_dir_button.clicked.connect(lambda: self.browse_model_dir())
        self.check_models_button.clicked.connect(lambda: self.check_models())
        self.model_hint_panel.action_button.clicked.connect(lambda: self.check_models())
        self.preset_combo.currentIndexChanged.connect(lambda _index: self.apply_selected_preset())
        self.toggle_advanced_button.clicked.connect(self.toggle_advanced_settings)
        self.apply_selected_preset()

    def visible_summary_text(self) -> str:
        return "\n".join(self._summary_parts)

    def advanced_settings_visible(self) -> bool:
        return not self.advanced_container.isHidden()

    def toggle_advanced_settings(self) -> None:
        show = self.advanced_container.isHidden()
        self.advanced_container.setVisible(show)
        self.toggle_advanced_button.setText("隐藏开发者设置" if show else "显示开发者设置")

    def browse_model_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "选择模型目录",
            self.model_dir_edit.text().strip() or "models",
        )
        if not path:
            return
        self.model_dir_edit.setText(path)
        self.sync_model_dir_to_advanced()

    def sync_model_dir_to_advanced(self) -> None:
        self.advanced_settings.local_model_path_edit.setText(
            self.model_dir_edit.text().strip() or "models"
        )

    def select_preset(self, preset_id: str) -> None:
        for index in range(self.preset_combo.count()):
            if self.preset_combo.itemData(index) == preset_id:
                self.preset_combo.setCurrentIndex(index)
                self.apply_selected_preset()
                return
        raise KeyError(preset_id)

    def apply_selected_preset(self) -> None:
        preset_id = self.preset_combo.currentData()
        if not isinstance(preset_id, str):
            return
        preset = get_model_preset(preset_id)
        self.advanced_settings.local_command_profiles_path_edit.setText(
            preset.local_profiles_path
        )
        self.advanced_settings.translation_profile_path_edit.setText(
            preset.translation_profile_path
        )

    def check_models(self) -> None:
        self.sync_model_dir_to_advanced()
        self.advanced_settings.refresh_model_diagnostics()
        self.advanced_settings.check_local_readiness()

    def show_missing_model_hint(self, stage: str, model_name: str, expected_path: str) -> None:
        self.model_hint_panel.title_label.setText(f"没有找到 {model_name} 模型")
        self.model_hint_panel.description_label.setText(
            f"{stage} 阶段需要 {model_name}。请把模型放到 {expected_path}，"
            "或在模型中心选择已经下载好的模型目录。"
        )
        self.model_hint_panel.action_button.setText("重新检查模型")
        self.model_hint_panel.setVisible(True)


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
