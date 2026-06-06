from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ivo.core.model_presets import builtin_model_presets
from ivo.core.visual_model_config import (
    VisualModelConfig,
    VisualModelConfigStore,
    VisualStageConfig,
)
from ivo.ui.advanced_model_settings import AdvancedModelSettings
from ivo.ui.empty_states import EmptyStatePanel
from ivo.ui.theme import CARD_STYLE, PRIMARY_BUTTON_STYLE, SECONDARY_BUTTON_STYLE
from ivo.workspace_paths import default_work_dir


_SERVICE_TYPE_OPTIONS = [
    ("local", "本地模型"),
    ("http", "在线 API"),
    ("disabled", "跳过"),
]


class ModelCenter(QWidget):
    preset_applied = Signal(str)

    def __init__(
        self,
        *,
        config_store_path: Path | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.config_store = VisualModelConfigStore(
            config_store_path or default_work_dir() / "model-configs.json"
        )
        self.advanced_settings = AdvancedModelSettings()
        self.advanced_container = QWidget()
        self.advanced_container.setVisible(False)
        self._current_config_id = ""

        self.model_dir_edit = QLineEdit("models")
        self.model_dir_button = QPushButton("选择模型目录")
        self.check_models_button = QPushButton("一键检查模型")
        self.toggle_advanced_button = QPushButton("显示开发者设置")
        self.preset_combo = QComboBox()
        self.preset_buttons: dict[str, QPushButton] = {}
        self.preset_button_group = QButtonGroup(self)
        self.preset_button_group.setExclusive(True)
        self.selected_preset_label = QLabel("")
        self.selected_preset_label.setObjectName("SecondaryText")
        self.selected_preset_detail_label = QLabel("")
        self.selected_preset_detail_label.setWordWrap(True)
        self.selected_preset_detail_label.setObjectName("SecondaryText")
        self.apply_preset_button = QPushButton("应用当前方案")
        self.status_label = QLabel("")
        self.status_label.setObjectName("SecondaryText")
        self.config_list = QListWidget()
        self.config_name_edit = QLineEdit()
        self.config_description_edit = QLineEdit()
        self.config_local_profiles_path_edit = QLineEdit()
        self.config_translation_profile_path_edit = QLineEdit()
        self.stage_table = QTableWidget(0, 4)
        self.stage_enabled_checks: dict[str, QCheckBox] = {}
        self.stage_service_combos: dict[str, QComboBox] = {}
        self.stage_provider_edits: dict[str, QLineEdit] = {}
        self.new_config_button = QPushButton("新增配置")
        self.copy_config_button = QPushButton("复制为我的配置")
        self.save_config_button = QPushButton("保存配置")
        self.delete_config_button = QPushButton("删除配置")
        self.developer_settings_hint_label = QLabel("开发者设置默认隐藏。普通用户通常不需要修改。")
        self.developer_settings_hint_label.setObjectName("SecondaryText")
        self.model_hint_panel = EmptyStatePanel(
            title="模型目录尚未检查",
            description="请选择模型目录后点击一键检查。缺少模型时，这里会告诉你应该放到哪个文件夹。",
            action_text="一键检查模型",
        )
        self.model_hint_panel.setVisible(False)
        self._summary_parts: list[str] = []
        self._configure_stage_table()

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
            button = _preset_button(preset.display_name, preset.description)
            button.clicked.connect(
                lambda _checked=False, preset_id=preset.id: self.select_preset(preset_id)
            )
            self.preset_buttons[preset.id] = button
            self.preset_button_group.addButton(button)
            layout.addWidget(button)
            self._summary_parts.extend([preset.display_name, preset.description])

        self.model_dir_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.check_models_button.setStyleSheet(PRIMARY_BUTTON_STYLE)
        self.toggle_advanced_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        self.apply_preset_button.setStyleSheet(SECONDARY_BUTTON_STYLE)
        layout.addWidget(self.selected_preset_label)
        layout.addWidget(self.selected_preset_detail_label)
        layout.addWidget(self.apply_preset_button)
        layout.addWidget(self.status_label)
        layout.addWidget(QLabel("我的配置"))
        layout.addWidget(self.config_list)
        config_form = QFormLayout()
        config_form.addRow("配置名称", self.config_name_edit)
        config_form.addRow("说明", self.config_description_edit)
        config_form.addRow("本地流程配置", self.config_local_profiles_path_edit)
        config_form.addRow("翻译服务配置", self.config_translation_profile_path_edit)
        layout.addLayout(config_form)
        stage_title = QLabel("阶段可视化配置")
        stage_title.setStyleSheet("font-weight: 700;")
        stage_hint = QLabel("可以为每个阶段选择本地模型、在线 API 或跳过。保存后会成为“我的配置”。")
        stage_hint.setObjectName("SecondaryText")
        stage_hint.setWordWrap(True)
        layout.addWidget(stage_title)
        layout.addWidget(stage_hint)
        layout.addWidget(self.stage_table)
        layout.addWidget(self.new_config_button)
        layout.addWidget(self.copy_config_button)
        layout.addWidget(self.save_config_button)
        layout.addWidget(self.delete_config_button)
        layout.addWidget(QLabel("模型目录"))
        layout.addWidget(self.model_dir_edit)
        layout.addWidget(self.model_dir_button)
        layout.addWidget(self.check_models_button)
        layout.addWidget(self.model_hint_panel)
        layout.addWidget(self.toggle_advanced_button)
        layout.addWidget(self.developer_settings_hint_label)
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
        self.apply_preset_button.clicked.connect(self.apply_current_preset)
        self.config_list.currentRowChanged.connect(self._handle_config_selection_changed)
        self.new_config_button.clicked.connect(self.new_custom_config)
        self.copy_config_button.clicked.connect(self.copy_current_config)
        self.save_config_button.clicked.connect(self.save_current_config)
        self.delete_config_button.clicked.connect(self.delete_current_config)
        self.toggle_advanced_button.clicked.connect(self.toggle_advanced_settings)
        self.refresh_config_list()
        self.select_config("local_quality_lmstudio_qwen_f5")

    def visible_summary_text(self) -> str:
        return "\n".join(self._summary_parts)

    def advanced_settings_visible(self) -> bool:
        return not self.advanced_container.isHidden()

    def toggle_advanced_settings(self) -> None:
        show = self.advanced_container.isHidden()
        self.advanced_container.setVisible(show)
        self.toggle_advanced_button.setText("隐藏开发者设置" if show else "显示开发者设置")
        self.developer_settings_hint_label.setText(
            "开发者设置已展开，可在下方配置本地命令和在线 API。"
            if show
            else "开发者设置已隐藏。普通用户通常不需要修改。"
        )

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

    def _configure_stage_table(self) -> None:
        self.stage_table.setHorizontalHeaderLabels(["启用", "阶段", "运行方式", "模型 / 服务名称"])
        self.stage_table.verticalHeader().setVisible(False)
        self.stage_table.setAlternatingRowColors(True)
        self.stage_table.setMinimumHeight(210)
        header = self.stage_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

    def refresh_config_list(self) -> None:
        self.config_list.blockSignals(True)
        self.config_list.clear()
        for config in self.config_store.list_all():
            prefix = "内置" if config.builtin else "我的"
            item = QListWidgetItem(f"{prefix} · {config.display_name}")
            item.setData(Qt.ItemDataRole.UserRole, config.id)
            self.config_list.addItem(item)
        self.config_list.blockSignals(False)

    def config_ids(self) -> list[str]:
        ids: list[str] = []
        for row in range(self.config_list.count()):
            item = self.config_list.item(row)
            raw_id = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(raw_id, str):
                ids.append(raw_id)
        return ids

    def select_config(self, config_id: str) -> None:
        config = self.config_store.get(config_id)
        for row in range(self.config_list.count()):
            item = self.config_list.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == config_id:
                self.config_list.setCurrentRow(row)
                break
        self._load_config(config)

    def current_config_id(self) -> str:
        if not self._current_config_id:
            raise RuntimeError("当前没有选择模型配置")
        return self._current_config_id

    def current_config_display_name(self) -> str:
        return self.config_store.get(self.current_config_id()).display_name

    def new_custom_config(self) -> VisualModelConfig:
        config = self.config_store.create_blank_config()
        self.refresh_config_list()
        self.select_config(config.id)
        self.status_label.setText("已新增配置，请填写表单后保存。")
        return config

    def copy_current_config(self) -> VisualModelConfig:
        source_id = self.current_config_id()
        source = self.config_store.get(source_id)
        config = self.config_store.copy_config(source_id, display_name=f"{source.display_name} 副本")
        self.refresh_config_list()
        self.select_config(config.id)
        self.status_label.setText("已复制为我的配置，可以直接编辑。")
        return config

    def save_current_config(self) -> VisualModelConfig | None:
        current = self.config_store.get(self.current_config_id())
        if current.builtin:
            self.status_label.setText("内置配置不能直接修改，请先点击“复制为我的配置”。")
            return None
        updated = current.model_copy(
            update={
                "display_name": self.config_name_edit.text().strip() or current.display_name,
                "description": self.config_description_edit.text().strip(),
                "local_profiles_path": self.config_local_profiles_path_edit.text().strip(),
                "translation_profile_path": self.config_translation_profile_path_edit.text().strip(),
                "stages": self._stage_configs_from_table(),
            }
        )
        self.config_store.save_custom(updated)
        self.refresh_config_list()
        self.select_config(updated.id)
        self.status_label.setText(f"配置已保存：{updated.display_name}")
        return updated

    def delete_current_config(self) -> None:
        current = self.config_store.get(self.current_config_id())
        if current.builtin:
            self.status_label.setText("内置配置不能删除。")
            return
        self.config_store.delete_custom(current.id)
        self.refresh_config_list()
        self.select_config("local_quality_lmstudio_qwen_f5")
        self.status_label.setText(f"已删除配置：{current.display_name}")

    def select_preset(self, preset_id: str) -> None:
        self.select_config(preset_id)

    def selected_preset_id(self) -> str:
        return self.current_config_id()

    def apply_selected_preset(self) -> None:
        preset_id = self.preset_combo.currentData()
        if not isinstance(preset_id, str):
            return
        self.select_config(preset_id)

    def _handle_config_selection_changed(self, row: int) -> None:
        if row < 0:
            return
        item = self.config_list.item(row)
        raw_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(raw_id, str):
            self._load_config(self.config_store.get(raw_id))

    def _load_config(self, config: VisualModelConfig) -> None:
        self._current_config_id = config.id
        self.config_name_edit.setText(config.display_name)
        self.config_description_edit.setText(config.description)
        self.config_local_profiles_path_edit.setText(config.local_profiles_path)
        self.config_translation_profile_path_edit.setText(config.translation_profile_path)
        self.selected_preset_label.setText(f"当前方案：{config.display_name}")
        self.selected_preset_detail_label.setText(_config_detail_text(config))
        self.status_label.setText("方案已选择，点击“应用当前方案”可保存为默认方案。")
        self._populate_stage_table(config.stages)
        self.advanced_settings.local_command_profiles_path_edit.setText(
            config.local_profiles_path
        )
        self.advanced_settings.translation_profile_path_edit.setText(
            config.translation_profile_path
        )
        self._sync_builtin_preset_controls(config.id)

    def _sync_builtin_preset_controls(self, config_id: str) -> None:
        matched_combo = False
        for index in range(self.preset_combo.count()):
            if self.preset_combo.itemData(index) == config_id:
                self.preset_combo.blockSignals(True)
                self.preset_combo.setCurrentIndex(index)
                self.preset_combo.blockSignals(False)
                matched_combo = True
                break
        if not matched_combo:
            self.preset_combo.blockSignals(True)
            self.preset_combo.setCurrentIndex(-1)
            self.preset_combo.blockSignals(False)
        for preset_id, preset_button in self.preset_buttons.items():
            preset_button.setChecked(preset_id == config_id)

    def _populate_stage_table(self, stages: list[VisualStageConfig]) -> None:
        self.stage_enabled_checks.clear()
        self.stage_service_combos.clear()
        self.stage_provider_edits.clear()
        self.stage_table.setRowCount(0)
        for stage in stages:
            row = self.stage_table.rowCount()
            self.stage_table.insertRow(row)

            enabled_check = QCheckBox()
            enabled_check.setChecked(stage.enabled)
            self.stage_table.setCellWidget(row, 0, enabled_check)
            self.stage_enabled_checks[stage.stage] = enabled_check

            stage_item = QTableWidgetItem(stage.label)
            stage_item.setData(Qt.ItemDataRole.UserRole, stage.stage)
            stage_item.setFlags(stage_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.stage_table.setItem(row, 1, stage_item)

            service_combo = QComboBox()
            for value, label in _SERVICE_TYPE_OPTIONS:
                service_combo.addItem(label, value)
            _set_combo_data(service_combo, stage.service_type)
            self.stage_table.setCellWidget(row, 2, service_combo)
            self.stage_service_combos[stage.stage] = service_combo

            provider_edit = QLineEdit(stage.provider_name)
            provider_edit.setPlaceholderText("例如：F5-TTS、faster-whisper、LM Studio")
            self.stage_table.setCellWidget(row, 3, provider_edit)
            self.stage_provider_edits[stage.stage] = provider_edit

    def _stage_configs_from_table(self) -> list[VisualStageConfig]:
        stages: list[VisualStageConfig] = []
        for row in range(self.stage_table.rowCount()):
            stage_item = self.stage_table.item(row, 1)
            if stage_item is None:
                continue
            raw_stage = stage_item.data(Qt.ItemDataRole.UserRole)
            if not isinstance(raw_stage, str):
                continue
            service_combo = self.stage_service_combos[raw_stage]
            raw_service_type = service_combo.currentData()
            service_type = raw_service_type if isinstance(raw_service_type, str) else "local"
            stages.append(
                VisualStageConfig(
                    stage=raw_stage,
                    label=stage_item.text(),
                    service_type=service_type,
                    provider_name=self.stage_provider_edits[raw_stage].text().strip(),
                    enabled=self.stage_enabled_checks[raw_stage].isChecked(),
                )
            )
        return stages

    def apply_current_preset(self) -> str:
        config_id = self.current_config_id()
        config = self.config_store.get(config_id)
        self.sync_model_dir_to_advanced()
        self.status_label.setText(f"已应用方案：{config.display_name}")
        self.preset_applied.emit(config_id)
        return config_id

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


def _preset_button(title: str, description: str) -> QPushButton:
    button = QPushButton(f"{title}\n{description}")
    button.setCheckable(True)
    button.setMinimumHeight(86)
    button.setStyleSheet(
        """
        QPushButton {
            text-align: left;
            padding: 14px 18px;
            border: 1px solid #d1d5db;
            border-radius: 12px;
            background: #ffffff;
            color: #111827;
            font-size: 14px;
        }
        QPushButton:checked {
            border: 2px solid #007aff;
            background: #eef6ff;
            font-weight: 700;
        }
        QPushButton:hover {
            border-color: #007aff;
        }
        """
    )
    return button


def _set_combo_data(combo: QComboBox, value: str) -> None:
    index = combo.findData(value)
    combo.setCurrentIndex(index if index >= 0 else 0)


def _config_detail_text(config: VisualModelConfig) -> str:
    enabled_stages = "、".join(stage.label for stage in config.stages if stage.enabled)
    if not enabled_stages:
        enabled_stages = "尚未配置阶段"
    recommended_models = "、".join(config.recommended_models) or "按所选阶段配置"
    service_types = {
        "local": "本地模型",
        "http": "在线 API",
        "disabled": "跳过",
    }
    stage_summary = "；".join(
        f"{stage.label}：{service_types.get(stage.service_type, stage.service_type)}"
        for stage in config.stages
    )
    return (
        f"启用阶段：{enabled_stages}。\n"
        f"阶段服务：{stage_summary}。\n"
        f"需要模型：{recommended_models}。\n"
        f"本地流程配置：{config.local_profiles_path or '未填写'}"
        + (f"\n翻译服务配置：{config.translation_profile_path}" if config.translation_profile_path else "")
    )
