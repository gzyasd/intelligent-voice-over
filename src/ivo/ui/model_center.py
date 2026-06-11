from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from ivo.core.model_inventory import (
    ModelCandidate,
    fetch_lm_studio_models,
    group_candidates_by_stage,
    scan_model_candidates,
    validate_stage_config,
)
from ivo.core.visual_model_config import (
    VisualModelConfig,
    VisualModelConfigStore,
    VisualStageConfig,
)
from ivo.ui.advanced_model_settings import AdvancedModelSettings
from ivo.ui.empty_states import EmptyStatePanel
from ivo.ui.model_center_components import ConfigSummaryCard, SERVICE_TYPE_LABELS, StageFlowEditor, StatusPill
from ivo.ui.theme import (
    mark_card,
    mark_heading3,
    mark_item_title,
    mark_primary_button,
    mark_secondary_button,
)
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
        self._applied_config_id = "local_quality_lmstudio_qwen_f5"
        self._editing_stage_id: str | None = None
        self._model_candidates: dict[str, list[ModelCandidate]] = {}
        self._lm_studio_models: list[str] = []
        self._unsaved_changes = False
        self._loading_form = False

        self.model_dir_edit = QLineEdit("models")
        self.model_dir_button = QPushButton("更换目录")
        self.scan_models_button = QPushButton("刷新目录")
        self.check_models_button = QPushButton("一键检查")
        self.current_config_status_label = QLabel("当前应用：本机高质量 · 已应用")
        self.current_config_status_label.setObjectName("SecondaryText")
        self.search_config_edit = QLineEdit()
        self.search_config_edit.setPlaceholderText("搜索配置、模型或服务")

        self.config_library_title = QLabel("配置库")
        mark_heading3(self.config_library_title)
        self.config_list = QListWidget()
        self.config_list.setMinimumWidth(220)
        self.preset_buttons: dict[str, QPushButton] = {}
        self.config_detail_title = QLabel("")
        self.config_summary_card = ConfigSummaryCard()
        mark_primary_button(self.config_summary_card.apply_button)
        self.apply_preset_button = self.config_summary_card.apply_button
        self.edit_config_button = self.config_summary_card.edit_button
        self.copy_config_button = self.config_summary_card.copy_button
        self.delete_config_button = self.config_summary_card.delete_button
        self.stage_flow = StageFlowEditor()
        self.status_label = QLabel("")
        self.status_label.setObjectName("SecondaryText")
        self.selected_preset_label = QLabel("")
        self.selected_preset_label.setObjectName("SecondaryText")
        self.selected_preset_detail_label = QLabel("")
        self.selected_preset_detail_label.setWordWrap(True)
        self.selected_preset_detail_label.setObjectName("SecondaryText")

        self.editor_drawer = QFrame()
        self.editor_drawer.setStyleSheet("")
        mark_card(self.editor_drawer)
        self.editor_drawer.setVisible(False)
        self.editor_tabs = QTabWidget()
        self.config_name_edit = QLineEdit()
        self.config_description_edit = QLineEdit()
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["快速预览", "高质量", "质量优先", "自定义"])
        self.prefer_gpu_check = QCheckBox("优先使用 GPU")
        self.content_type_edit = QLineEdit()
        self.content_type_edit.setPlaceholderText("例如：美剧、日剧、韩剧、通用")
        self.config_local_profiles_path_edit = QLineEdit()
        self.config_translation_profile_path_edit = QLineEdit()
        self.stage_table = QTableWidget(0, 0)
        self.stage_table.setVisible(False)
        self.stage_editor_header_label = QLabel("")
        mark_item_title(self.stage_editor_header_label)
        self.stage_editor_header_label.setStyleSheet("padding: 4px 0;")
        self.stage_enabled_checks: dict[str, QCheckBox] = {}
        self.stage_service_combos: dict[str, QComboBox] = {}
        self.stage_provider_edits: dict[str, QLineEdit] = {}
        self.stage_service_type_combo = QComboBox()
        for value, label in _SERVICE_TYPE_OPTIONS:
            self.stage_service_type_combo.addItem(label, value)
        self.stage_provider_edit = QLineEdit()
        self.stage_enabled_check = QCheckBox("启用此阶段")
        self.stage_local_fields = QGroupBox("本地模型")
        self.stage_model_combo = QComboBox()
        self.stage_model_path_edit = QLineEdit()
        self.stage_device_combo = QComboBox()
        self.stage_device_combo.addItems(["auto", "cuda", "cpu"])
        self.stage_precision_combo = QComboBox()
        self.stage_precision_combo.addItems(["auto", "float16", "int8"])
        self.stage_api_fields = QGroupBox("在线 API")
        self.stage_api_base_url_edit = QLineEdit()
        self.stage_api_model_combo = QComboBox()
        self.stage_api_model_edit = QLineEdit()
        self.load_lm_studio_models_button = QPushButton("读取 LM Studio 模型")
        self.test_stage_button = QPushButton("测试当前阶段")
        self.save_config_button = QPushButton("保存")
        self.save_apply_button = QPushButton("保存并应用")
        self.cancel_edit_button = QPushButton("放弃修改")
        self.new_config_button = QPushButton("新建配置")
        self.export_config_button = QPushButton("导出配置")
        self.import_config_button = QPushButton("导入配置")
        self.toggle_advanced_button = QPushButton("显示开发者设置")
        self.developer_settings_hint_label = QLabel("开发者源文件默认隐藏。普通用户通常不需要修改。")
        self.developer_settings_hint_label.setObjectName("SecondaryText")
        self.model_hint_panel = EmptyStatePanel(
            title="配置尚未检查",
            description="点击一键检查后，这里会按阶段提示模型、LM Studio 或在线 API 是否就绪。",
            action_text="一键检查此配置",
        )
        self.model_hint_panel.setVisible(False)
        self.validation_status_pill = StatusPill("尚未检查", "unchecked")
        self.validation_summary_label = QLabel("尚未检查。")
        self.validation_summary_label.setWordWrap(True)
        self.validation_summary_label.setObjectName("SecondaryText")
        self._validation_results: dict[str, dict[str, str]] = {}
        self.preset_combo = QComboBox()
        self._summary_parts: list[str] = [
            "配置库",
            "选择模型目录",
            "一键检查模型",
            "一键检查此配置",
            "应用此配置",
        ]

        self._build_layout()
        self._connect_signals()
        self.refresh_config_list()
        self.select_config(self._applied_config_id)

    def visible_summary_text(self) -> str:
        return "\n".join(self._summary_parts)

    def advanced_settings_visible(self) -> bool:
        return not self.advanced_container.isHidden()

    def config_library_summary(self) -> str:
        return "\n".join(self.config_list.item(row).text() for row in range(self.config_list.count()))

    def stage_flow_summary(self) -> str:
        return self.stage_flow.summary_text()

    def validation_summary_text(self) -> str:
        return self.validation_summary_label.text()

    def toggle_advanced_settings(self) -> None:
        show = self.advanced_container.isHidden()
        self.advanced_container.setVisible(show)
        self.toggle_advanced_button.setText("隐藏开发者设置" if show else "显示开发者设置")
        self.developer_settings_hint_label.setText(
            "开发者设置已展开，可在下方配置本地命令和在线 API。"
            if show
            else "开发者设置已隐藏。普通用户通常不需要修改。"
        )
        if show:
            self.editor_drawer.setVisible(True)
            self.editor_tabs.setCurrentWidget(self.advanced_tab)

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

    def refresh_model_candidates(self) -> None:
        self.sync_model_dir_to_advanced()
        candidates = scan_model_candidates(self._model_root())
        self._model_candidates = group_candidates_by_stage(candidates)
        if self._editing_stage_id:
            self._populate_stage_model_combo(self._editing_stage_id)
        total = sum(len(items) for items in self._model_candidates.values())
        self.status_label.setText(f"已刷新模型目录：发现 {total} 个可选模型。")

    def stage_model_choice_summary(self) -> str:
        lines: list[str] = []
        for stage, candidates in self._model_candidates.items():
            names = "、".join(candidate.name for candidate in candidates) or "无"
            lines.append(f"{_stage_label(stage)}：{names}")
        return "\n".join(lines)

    def load_lm_studio_models(self) -> None:
        base_url = self.stage_api_base_url_edit.text().strip() or "http://127.0.0.1:1995/v1"
        try:
            self._lm_studio_models = fetch_lm_studio_models(base_url)
        except Exception as exc:
            self._lm_studio_models = []
            self.status_label.setText(f"读取 LM Studio 模型失败：{exc}")
            return
        self._populate_api_model_combo()
        if self._lm_studio_models:
            self.status_label.setText(f"已读取 LM Studio 模型：{len(self._lm_studio_models)} 个。")
        else:
            self.status_label.setText("LM Studio 已响应，但没有返回可用模型。")

    def test_current_stage(self) -> None:
        if not self._editing_stage_id:
            self.status_label.setText("请先选择一个阶段再测试。")
            return
        stage = self._current_stage_config_from_form()
        result = validate_stage_config(
            stage,
            self._model_root(),
            lm_studio_models=self._lm_studio_models if stage.service_type == "http" else None,
        )
        self.show_stage_validation_result(
            result.stage,
            provider=result.provider,
            status=result.status,
            message=result.message,
        )
        self.status_label.setText(f"{stage.label} 阶段测试完成：{_validation_text(result.status)}。")

    def has_unsaved_changes(self) -> bool:
        return self._unsaved_changes

    def mark_unsaved_changes(self) -> None:
        if self._loading_form:
            return
        if not self._current_config_id:
            return
        try:
            current = self.config_store.get(self.current_config_id())
        except KeyError:
            return
        if current.builtin:
            return
        self._unsaved_changes = True
        self.status_label.setText("有未保存修改。")
        self.save_apply_button.setText("保存未保存修改并应用")

    def browse_export_current_config(self) -> None:
        path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出模型配置",
            f"{self.current_config_display_name()}.json",
            "JSON 配置 (*.json)",
        )
        if path:
            self.export_current_config(Path(path))

    def browse_import_config(self) -> None:
        path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "导入模型配置",
            "",
            "JSON 配置 (*.json)",
        )
        if path:
            self.import_config(Path(path))

    def export_current_config(self, path: Path) -> Path:
        config = self.config_store.get(self.current_config_id())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(config.model_dump_json(indent=2), encoding="utf-8")
        self.status_label.setText(f"配置已导出：{path}")
        return path

    def import_config(self, path: Path) -> VisualModelConfig | None:
        if not path.is_file():
            self.status_label.setText(f"没有找到配置文件：{path}")
            return None
        try:
            imported = VisualModelConfig.model_validate_json(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError) as exc:
            self.status_label.setText(f"导入失败：{exc}")
            return None
        imported = imported.model_copy(
            update={
                "id": f"custom-{uuid4().hex[:12]}",
                "builtin": False,
            },
            deep=True,
        )
        self.config_store.save_custom(imported)
        self.refresh_config_list()
        self.select_config(imported.id)
        self.status_label.setText(f"已导入配置：{imported.display_name}")
        return imported

    def refresh_config_list(self) -> None:
        self.config_list.blockSignals(True)
        self.config_list.clear()
        self.preset_combo.clear()
        self.preset_buttons.clear()
        self.config_list.addItem(_section_item("推荐方案"))
        for config in self.config_store.list_all():
            if config.builtin:
                self._add_config_item(config)
                self._summary_parts.extend([config.display_name, config.description])
                self.preset_combo.addItem(config.display_name, config.id)
                button = QPushButton(config.display_name)
                button.clicked.connect(
                    lambda _checked=False, config_id=config.id: self.select_config(config_id)
                )
                self.preset_buttons[config.id] = button
        self.config_list.addItem(_section_item("我的配置"))
        for config in self.config_store.list_all():
            if not config.builtin:
                self._add_config_item(config)
        self.config_list.blockSignals(False)

    def config_ids(self) -> list[str]:
        ids: list[str] = []
        for row in range(self.config_list.count()):
            raw_id = self.config_list.item(row).data(Qt.ItemDataRole.UserRole)
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

    def selected_preset_id(self) -> str:
        return self.current_config_id()

    def select_preset(self, preset_id: str) -> None:
        self.select_config(preset_id)

    def apply_selected_preset(self) -> None:
        raw_id = self.preset_combo.currentData()
        if isinstance(raw_id, str):
            self.select_config(raw_id)

    def new_custom_config(self) -> VisualModelConfig:
        config = self.config_store.create_blank_config()
        self.refresh_config_list()
        self.select_config(config.id)
        self.open_editor()
        self.status_label.setText("已新增配置，请填写表单后保存。")
        return config

    def copy_current_config(self) -> VisualModelConfig:
        source_id = self.current_config_id()
        source = self.config_store.get(source_id)
        config = self.config_store.copy_config(source_id, display_name=f"{source.display_name} 副本")
        self.refresh_config_list()
        self.select_config(config.id)
        self.open_editor()
        self.status_label.setText("已复制为我的配置，可以直接编辑。")
        return config

    def edit_current_config(self) -> None:
        current = self.config_store.get(self.current_config_id())
        if current.builtin:
            self.copy_current_config()
            self.status_label.setText("已复制推荐方案，可以开始编辑。")
            return
        self.open_editor()

    def open_editor(self) -> None:
        self.editor_drawer.setVisible(True)
        self.editor_tabs.setCurrentIndex(0)

    def open_stage_editor(self, stage_id: str) -> None:
        config = self.config_store.get(self.current_config_id())
        stage = next(stage for stage in config.stages if stage.stage == stage_id)
        self._loading_form = True
        self._editing_stage_id = stage_id
        # 更新编辑器标题，明确显示正在编辑的阶段
        self.stage_editor_header_label.setText(f"正在编辑：{stage.label}")
        # 高亮显示左侧对应的阶段卡片
        self.stage_flow.highlight_stage(stage_id)
        self.editor_drawer.setVisible(True)
        self.editor_tabs.setCurrentWidget(self.stage_tab)
        self.stage_enabled_check.setChecked(stage.enabled)
        _set_combo_data(self.stage_service_type_combo, stage.service_type)
        self.stage_provider_edit.setText(stage.provider_name)
        self.stage_model_path_edit.setText(stage.model_path)
        _set_combo_text(self.stage_device_combo, stage.device)
        _set_combo_text(self.stage_precision_combo, stage.precision)
        self.stage_api_base_url_edit.setText(stage.api_base_url)
        self.stage_api_model_edit.setText(stage.api_model)
        self._populate_stage_model_combo(stage_id)
        self._populate_api_model_combo()
        self._sync_stage_editor_mode()
        self._loading_form = False

    def save_current_config(self) -> VisualModelConfig | None:
        current = self.config_store.get(self.current_config_id())
        if current.builtin:
            self.status_label.setText("内置配置不能直接修改，请先点击“复制为我的配置”。")
            return None
        updated = current.model_copy(
            update={
                "display_name": self.config_name_edit.text().strip() or current.display_name,
                "description": self.config_description_edit.text().strip(),
                "quality_label": self.quality_combo.currentText(),
                "prefer_gpu": self.prefer_gpu_check.isChecked(),
                "content_types": _split_content_types(self.content_type_edit.text()),
                "local_profiles_path": self.config_local_profiles_path_edit.text().strip(),
                "translation_profile_path": self.config_translation_profile_path_edit.text().strip(),
                "stages": self._stage_configs_from_editor(current.stages),
            }
        )
        self.config_store.save_custom(updated)
        self.refresh_config_list()
        self.select_config(updated.id)
        self._unsaved_changes = False
        self.save_apply_button.setText("保存并应用")
        self.status_label.setText(f"配置已保存：{updated.display_name}")
        return updated

    def delete_current_config(self) -> None:
        current = self.config_store.get(self.current_config_id())
        if current.builtin:
            self.status_label.setText("内置配置不能删除。")
            return
        self.config_store.delete_custom(current.id)
        self.refresh_config_list()
        self.select_config(self._applied_config_id if self._applied_config_id in self.config_ids() else "local_quality_lmstudio_qwen_f5")
        self.status_label.setText(f"已删除配置：{current.display_name}")

    def apply_current_preset(self) -> str:
        saved = self.save_current_config() if self._has_unsaved_custom_changes() else None
        config_id = saved.id if saved is not None else self.current_config_id()
        config = self.config_store.get(config_id)
        self._applied_config_id = config_id
        self.sync_model_dir_to_advanced()
        self._load_config(config)
        self.status_label.setText(f"已应用方案：{config.display_name}")
        self.preset_applied.emit(config_id)
        return config_id

    def check_models(self) -> None:
        self.sync_model_dir_to_advanced()
        self.refresh_model_candidates()
        self.advanced_settings.refresh_model_diagnostics()
        self.advanced_settings.check_local_readiness()
        config = self.config_store.get(self.current_config_id())
        results = [
            validate_stage_config(
                stage,
                self._model_root(),
                lm_studio_models=self._lm_studio_models if stage.service_type == "http" else None,
            )
            for stage in config.stages
            if stage.enabled
        ]
        self.show_validation_results(
            [
                {
                    "stage": result.stage,
                    "provider": result.provider,
                    "status": result.status,
                    "message": result.message,
                }
                for result in results
            ]
        )
        self.model_hint_panel.setVisible(False)

    def show_validation_results(self, results: list[dict[str, str]]) -> None:
        self._validation_results = {
            result.get("stage", ""): {
                "provider": result.get("provider", ""),
                "status": result.get("status", "unchecked"),
                "message": result.get("message", ""),
            }
            for result in results
            if result.get("stage")
        }
        self._refresh_validation_summary()

    def show_stage_validation_result(
        self,
        stage: str,
        *,
        provider: str,
        status: str,
        message: str,
    ) -> None:
        self._validation_results[stage] = {
            "provider": provider,
            "status": status,
            "message": message,
        }
        self._refresh_validation_summary()

    def show_missing_model_hint(self, stage: str, model_name: str, expected_path: str) -> None:
        self.validation_status_pill.set_status("缺少模型", "missing")
        self.model_hint_panel.title_label.setText(f"没有找到 {model_name} 模型")
        self.model_hint_panel.description_label.setText(
            f"{stage} 阶段需要 {model_name}。请把模型放到 {expected_path}，"
            "或在模型中心选择已经下载好的模型目录。"
        )
        self.model_hint_panel.action_button.setText("重新检查模型")
        self.model_hint_panel.setVisible(True)

    def _refresh_validation_summary(self) -> None:
        if not self._validation_results:
            self.validation_status_pill.set_status("尚未检查", "unchecked")
            self.validation_summary_label.setText("尚未检查。")
            return
        lines: list[str] = []
        has_problem = False
        for stage_id, result in self._validation_results.items():
            status = result.get("status", "unchecked")
            if status in {"missing", "failed"}:
                has_problem = True
            stage_label = _stage_label(stage_id)
            provider = result.get("provider", "") or "未选择"
            message = result.get("message", "") or "没有更多信息"
            lines.append(f"{stage_label}：{_validation_text(status)} · {provider} · {message}")
        self.validation_summary_label.setText("\n".join(lines))
        self.validation_status_pill.set_status(
            "需要处理" if has_problem else "已就绪",
            "warning" if has_problem else "ready",
        )

    def _build_layout(self) -> None:
        root = QVBoxLayout()
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)
        title = QLabel("模型中心")
        title.setObjectName("PageTitle")
        subtitle = QLabel("管理推荐方案和我的配置。普通模式不需要编辑源文件。")
        subtitle.setObjectName("SecondaryText")
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addWidget(self._build_top_bar())

        body = QGridLayout()
        body.setColumnStretch(0, 1)
        body.setColumnStretch(1, 3)
        body.setColumnStretch(2, 3)
        body.addWidget(self._build_library_panel(), 0, 0)
        body.addWidget(self._build_detail_panel(), 0, 1)
        body.addWidget(self._build_editor_drawer(), 0, 2)
        root.addLayout(body)
        self.setLayout(root)

    def _build_top_bar(self) -> QWidget:
        bar = QFrame()
        bar.setStyleSheet("")
        mark_card(bar)
        outer = QVBoxLayout()
        outer.setContentsMargins(14, 10, 14, 10)
        outer.setSpacing(8)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("模型目录"))
        row1.addWidget(self.model_dir_edit, 3)
        self.model_dir_button.setStyleSheet("")
        mark_secondary_button(self.model_dir_button)
        self.scan_models_button.setStyleSheet("")
        mark_secondary_button(self.scan_models_button)
        row1.addWidget(self.model_dir_button)
        row1.addWidget(self.scan_models_button)

        row2 = QHBoxLayout()
        self.check_models_button.setStyleSheet("")
        mark_primary_button(self.check_models_button)
        row2.addWidget(self.check_models_button)
        row2.addWidget(self.current_config_status_label)
        row2.addStretch()
        row2.addWidget(self.search_config_edit, 2)

        outer.addLayout(row1)
        outer.addLayout(row2)
        bar.setLayout(outer)
        return bar

    def _build_library_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet("")
        mark_card(panel)
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        layout.addWidget(self.config_library_title)
        self.new_config_button.setStyleSheet("")
        mark_primary_button(self.new_config_button)
        self.import_config_button.setStyleSheet("")
        mark_secondary_button(self.import_config_button)
        layout.addWidget(self.new_config_button)
        layout.addWidget(self.import_config_button)
        layout.addWidget(self.config_list)
        panel.setLayout(layout)
        return panel

    def _build_detail_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        mark_heading3(self.config_detail_title)
        layout.addWidget(self.config_detail_title)
        layout.addWidget(self.config_summary_card)
        stage_title = QLabel("阶段流程")
        mark_heading3(stage_title)
        layout.addWidget(stage_title)
        layout.addWidget(self.stage_flow)
        validation = QFrame()
        validation.setStyleSheet("")
        mark_card(validation)
        validation_layout = QVBoxLayout()
        validation_layout.setContentsMargins(14, 14, 14, 14)
        validation_header = QHBoxLayout()
        validation_header.addWidget(QLabel("校验中心"))
        validation_header.addStretch()
        validation_header.addWidget(self.validation_status_pill)
        validation_layout.addLayout(validation_header)
        validation_layout.addWidget(self.validation_summary_label)
        validation_layout.addWidget(self.model_hint_panel)
        validation.setLayout(validation_layout)
        layout.addWidget(validation)
        layout.addWidget(self.selected_preset_label)
        layout.addWidget(self.selected_preset_detail_label)
        layout.addWidget(self.status_label)
        panel.setLayout(layout)
        return panel

    def _build_editor_drawer(self) -> QWidget:
        layout = QVBoxLayout()
        layout.setContentsMargins(14, 14, 14, 14)
        drawer_title = QLabel("编辑配置")
        mark_heading3(drawer_title)
        layout.addWidget(drawer_title)
        self.editor_tabs.addTab(self._build_basic_tab(), "基础信息")
        self.stage_tab = self._build_stage_tab()
        self.editor_tabs.addTab(self.stage_tab, "阶段设置")
        self.advanced_tab = self._build_advanced_tab()
        self.editor_tabs.addTab(self.advanced_tab, "高级源文件")
        layout.addWidget(self.editor_tabs)
        actions = QHBoxLayout()
        self.save_config_button.setStyleSheet("")
        mark_primary_button(self.save_config_button)
        self.save_apply_button.setStyleSheet("")
        mark_primary_button(self.save_apply_button)
        self.cancel_edit_button.setStyleSheet("")
        mark_secondary_button(self.cancel_edit_button)
        actions.addWidget(self.save_config_button)
        actions.addWidget(self.save_apply_button)
        self.export_config_button.setStyleSheet("")
        mark_secondary_button(self.export_config_button)
        actions.addWidget(self.export_config_button)
        actions.addWidget(self.cancel_edit_button)
        layout.addLayout(actions)
        self.editor_drawer.setLayout(layout)
        return self.editor_drawer

    def _build_basic_tab(self) -> QWidget:
        tab = QWidget()
        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(12, 12, 12, 12)
        form.addRow("配置名称", self.config_name_edit)
        form.addRow("配置说明", self.config_description_edit)
        form.addRow("质量偏好", self.quality_combo)
        form.addRow("硬件偏好", self.prefer_gpu_check)
        form.addRow("内容类型", self.content_type_edit)
        tab.setLayout(form)
        return tab

    def _build_stage_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()
        # 阶段编辑器标题，显示正在编辑的阶段名称
        layout.addWidget(self.stage_editor_header_label)
        form = QFormLayout()
        form.addRow("运行方式", self.stage_service_type_combo)
        form.addRow("模型 / 服务名称", self.stage_provider_edit)
        form.addRow("", self.stage_enabled_check)
        layout.addLayout(form)

        local_form = QFormLayout()
        self.stage_model_path_edit.setPlaceholderText("默认跟随全局模型目录")
        self.stage_model_combo.addItem("手动指定或跟随默认目录", "")
        local_form.addRow("已发现模型", self.stage_model_combo)
        local_form.addRow("模型位置", self.stage_model_path_edit)
        local_form.addRow("推理设备", self.stage_device_combo)
        local_form.addRow("精度", self.stage_precision_combo)
        self.stage_local_fields.setLayout(local_form)
        api_form = QFormLayout()
        self.stage_api_base_url_edit.setPlaceholderText("例如：http://127.0.0.1:1995/v1")
        self.stage_api_model_edit.setPlaceholderText("例如：Qwen3.6-35B-A3B")
        api_form.addRow("API 地址", self.stage_api_base_url_edit)
        api_form.addRow("", self.load_lm_studio_models_button)
        api_form.addRow("LM Studio 模型", self.stage_api_model_combo)
        api_form.addRow("模型名称", self.stage_api_model_edit)
        self.stage_api_fields.setLayout(api_form)
        layout.addWidget(self.stage_local_fields)
        layout.addWidget(self.stage_api_fields)
        self.test_stage_button.setStyleSheet("")
        mark_secondary_button(self.test_stage_button)
        layout.addWidget(self.test_stage_button)
        layout.addWidget(self.stage_table)
        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _build_advanced_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.toggle_advanced_button)
        layout.addWidget(self.developer_settings_hint_label)
        advanced_layout = QVBoxLayout()
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        advanced_layout.addWidget(self.advanced_settings)
        self.advanced_container.setLayout(advanced_layout)
        layout.addWidget(self.advanced_container)
        source_form = QFormLayout()
        source_form.addRow("本地流程源文件", self.config_local_profiles_path_edit)
        source_form.addRow("翻译服务源文件", self.config_translation_profile_path_edit)
        layout.addLayout(source_form)
        tab.setLayout(layout)
        return tab

    def _connect_signals(self) -> None:
        self.model_dir_button.clicked.connect(lambda: self.browse_model_dir())
        self.scan_models_button.clicked.connect(self.refresh_model_candidates)
        self.check_models_button.clicked.connect(lambda: self.check_models())
        self.model_hint_panel.action_button.clicked.connect(lambda: self.check_models())
        self.config_list.currentRowChanged.connect(self._handle_config_selection_changed)
        self.new_config_button.clicked.connect(self.new_custom_config)
        self.config_summary_card.apply_requested.connect(self.apply_current_preset)
        self.config_summary_card.edit_requested.connect(self.edit_current_config)
        self.config_summary_card.copy_requested.connect(self.copy_current_config)
        self.config_summary_card.delete_requested.connect(self.delete_current_config)
        self.save_config_button.clicked.connect(self.save_current_config)
        self.save_apply_button.clicked.connect(self.apply_current_preset)
        self.cancel_edit_button.clicked.connect(lambda: self.editor_drawer.setVisible(False))
        self.stage_flow.stage_edit_requested.connect(self.open_stage_editor)
        self.stage_service_type_combo.currentIndexChanged.connect(lambda _index: self._sync_stage_editor_mode())
        self.stage_model_combo.currentIndexChanged.connect(lambda _index: self._apply_selected_model_candidate())
        self.stage_api_model_combo.currentIndexChanged.connect(lambda _index: self._apply_selected_api_model())
        self.load_lm_studio_models_button.clicked.connect(self.load_lm_studio_models)
        self.test_stage_button.clicked.connect(self.test_current_stage)
        self.export_config_button.clicked.connect(self.browse_export_current_config)
        self.import_config_button.clicked.connect(self.browse_import_config)
        self.toggle_advanced_button.clicked.connect(self.toggle_advanced_settings)
        self.preset_combo.currentIndexChanged.connect(lambda _index: self.apply_selected_preset())
        for line_edit in (
            self.config_name_edit,
            self.config_description_edit,
            self.content_type_edit,
            self.config_local_profiles_path_edit,
            self.config_translation_profile_path_edit,
            self.stage_provider_edit,
            self.stage_model_path_edit,
            self.stage_api_base_url_edit,
            self.stage_api_model_edit,
        ):
            line_edit.textChanged.connect(lambda _text: self.mark_unsaved_changes())
        self.quality_combo.currentIndexChanged.connect(lambda _index: self.mark_unsaved_changes())
        self.prefer_gpu_check.toggled.connect(lambda _checked: self.mark_unsaved_changes())
        self.stage_enabled_check.toggled.connect(lambda _checked: self.mark_unsaved_changes())
        self.stage_service_type_combo.currentIndexChanged.connect(lambda _index: self.mark_unsaved_changes())
        self.stage_device_combo.currentIndexChanged.connect(lambda _index: self.mark_unsaved_changes())
        self.stage_precision_combo.currentIndexChanged.connect(lambda _index: self.mark_unsaved_changes())

    def _add_config_item(self, config: VisualModelConfig) -> None:
        prefix = "推荐" if config.builtin else "我的"
        applied = " · 已应用" if config.id == self._applied_config_id else ""
        tags = " · ".join(config.tags[:2] or [config.quality_label])
        item = QListWidgetItem(f"{prefix} · {config.display_name}{applied}\n{tags}")
        item.setData(Qt.ItemDataRole.UserRole, config.id)
        self.config_list.addItem(item)

    def _handle_config_selection_changed(self, row: int) -> None:
        if row < 0:
            return
        item = self.config_list.item(row)
        raw_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(raw_id, str):
            self._load_config(self.config_store.get(raw_id))

    def _load_config(self, config: VisualModelConfig) -> None:
        self._loading_form = True
        self._current_config_id = config.id
        self.config_name_edit.setText(config.display_name)
        self.config_description_edit.setText(config.description)
        _set_combo_text(self.quality_combo, config.quality_label)
        self.prefer_gpu_check.setChecked(config.prefer_gpu)
        self.content_type_edit.setText("、".join(config.content_types))
        self.config_local_profiles_path_edit.setText(config.local_profiles_path)
        self.config_translation_profile_path_edit.setText(config.translation_profile_path)
        self.config_detail_title.setText(config.display_name)
        self.config_summary_card.set_config(config, applied=config.id == self._applied_config_id)
        self.selected_preset_label.setText(f"当前方案：{config.display_name}")
        self.selected_preset_detail_label.setText(_config_detail_text(config))
        self.stage_flow.set_stages(config.stages)
        self.status_label.setText("方案已选择，可检查后应用。")
        self.advanced_settings.local_command_profiles_path_edit.setText(config.local_profiles_path)
        self.advanced_settings.translation_profile_path_edit.setText(config.translation_profile_path)
        self.current_config_status_label.setText(
            f"当前应用：{self.config_store.get(self._applied_config_id).display_name} · 已应用"
            if self._applied_config_id in self.config_ids()
            else "当前应用：尚未选择"
        )
        self._populate_compat_stage_controls(config.stages)
        self._sync_preset_combo(config.id)
        self._unsaved_changes = False
        self.save_apply_button.setText("保存并应用")
        self._loading_form = False

    def _populate_compat_stage_controls(self, stages: list[VisualStageConfig]) -> None:
        self.stage_enabled_checks.clear()
        self.stage_service_combos.clear()
        self.stage_provider_edits.clear()
        for stage in stages:
            enabled = QCheckBox()
            enabled.setChecked(stage.enabled)
            service = QComboBox()
            for value, label in _SERVICE_TYPE_OPTIONS:
                service.addItem(label, value)
            _set_combo_data(service, stage.service_type)
            provider = QLineEdit(stage.provider_name)
            self.stage_enabled_checks[stage.stage] = enabled
            self.stage_service_combos[stage.stage] = service
            self.stage_provider_edits[stage.stage] = provider

    def _stage_configs_from_editor(
        self,
        stages: list[VisualStageConfig],
    ) -> list[VisualStageConfig]:
        updated: list[VisualStageConfig] = []
        for stage in stages:
            changes: dict[str, object] = {}
            compat_enabled = self.stage_enabled_checks.get(stage.stage)
            compat_service = self.stage_service_combos.get(stage.stage)
            compat_provider = self.stage_provider_edits.get(stage.stage)
            if compat_enabled is not None:
                changes["enabled"] = compat_enabled.isChecked()
            if compat_service is not None:
                raw_service = compat_service.currentData()
                changes["service_type"] = raw_service if isinstance(raw_service, str) else "local"
            if compat_provider is not None:
                changes["provider_name"] = compat_provider.text().strip()
            if stage.stage == self._editing_stage_id:
                raw_service = self.stage_service_type_combo.currentData()
                changes.update(
                    {
                        "enabled": self.stage_enabled_check.isChecked(),
                        "service_type": raw_service if isinstance(raw_service, str) else "local",
                        "provider_name": self.stage_provider_edit.text().strip(),
                        "model_path": self.stage_model_path_edit.text().strip(),
                        "device": self.stage_device_combo.currentText(),
                        "precision": self.stage_precision_combo.currentText(),
                        "api_base_url": self.stage_api_base_url_edit.text().strip(),
                        "api_model": self.stage_api_model_edit.text().strip(),
                        "validation_status": "draft",
                        "validation_message": "已修改，建议重新检查",
                    }
                )
            updated.append(stage.model_copy(update=changes))
        return updated

    def _sync_stage_editor_mode(self) -> None:
        is_api = self.stage_service_type_combo.currentData() == "http"
        self.stage_local_fields.setVisible(not is_api)
        self.stage_api_fields.setVisible(is_api)

    def _has_unsaved_custom_changes(self) -> bool:
        current = self.config_store.get(self.current_config_id())
        return not current.builtin and self._unsaved_changes

    def _model_root(self) -> Path:
        return Path(self.model_dir_edit.text().strip() or "models").expanduser()

    def _populate_stage_model_combo(self, stage_id: str) -> None:
        self.stage_model_combo.blockSignals(True)
        self.stage_model_combo.clear()
        self.stage_model_combo.addItem("手动指定或跟随默认目录", "")
        for candidate in self._model_candidates.get(stage_id, []):
            state = "已找到" if candidate.ready else "推荐"
            self.stage_model_combo.addItem(
                f"{candidate.name} · {state}",
                str(candidate.path),
            )
        current_path = self.stage_model_path_edit.text().strip()
        if current_path:
            index = self.stage_model_combo.findData(current_path)
            if index < 0:
                index = self.stage_model_combo.findData(str((self._model_root() / current_path).resolve()))
            if index >= 0:
                self.stage_model_combo.setCurrentIndex(index)
        self.stage_model_combo.blockSignals(False)

    def _apply_selected_model_candidate(self) -> None:
        raw_path = self.stage_model_combo.currentData()
        if not isinstance(raw_path, str) or not raw_path:
            return
        try:
            path_text = str(Path(raw_path).resolve().relative_to(self._model_root().resolve()))
        except ValueError:
            path_text = raw_path
        self.stage_model_path_edit.setText(path_text)
        label = self.stage_model_combo.currentText().split(" · ", maxsplit=1)[0]
        if label:
            self.stage_provider_edit.setText(label)
        self.mark_unsaved_changes()

    def _populate_api_model_combo(self) -> None:
        self.stage_api_model_combo.blockSignals(True)
        self.stage_api_model_combo.clear()
        for model_name in self._lm_studio_models:
            self.stage_api_model_combo.addItem(model_name)
        current_model = self.stage_api_model_edit.text().strip()
        if current_model:
            index = self.stage_api_model_combo.findText(current_model)
            if index >= 0:
                self.stage_api_model_combo.setCurrentIndex(index)
            else:
                # 当前配置的模型不在已加载列表中，添加到下拉框以便用户能看到
                self.stage_api_model_combo.addItem(f"{current_model}（未连接）")
                self.stage_api_model_combo.setCurrentIndex(self.stage_api_model_combo.count() - 1)
        self.stage_api_model_combo.blockSignals(False)

    def _apply_selected_api_model(self) -> None:
        model_name = self.stage_api_model_combo.currentText().strip()
        if not model_name:
            return
        self.stage_api_model_edit.setText(model_name)
        self.stage_provider_edit.setText("LM Studio")
        self.mark_unsaved_changes()

    def _current_stage_config_from_form(self) -> VisualStageConfig:
        if not self._editing_stage_id:
            raise RuntimeError("当前没有正在编辑的阶段")
        config = self.config_store.get(self.current_config_id())
        current_stage = next(stage for stage in config.stages if stage.stage == self._editing_stage_id)
        raw_service = self.stage_service_type_combo.currentData()
        return current_stage.model_copy(
            update={
                "enabled": self.stage_enabled_check.isChecked(),
                "service_type": raw_service if isinstance(raw_service, str) else "local",
                "provider_name": self.stage_provider_edit.text().strip(),
                "model_path": self.stage_model_path_edit.text().strip(),
                "device": self.stage_device_combo.currentText(),
                "precision": self.stage_precision_combo.currentText(),
                "api_base_url": self.stage_api_base_url_edit.text().strip(),
                "api_model": self.stage_api_model_edit.text().strip(),
            }
        )

    def _sync_preset_combo(self, config_id: str) -> None:
        for index in range(self.preset_combo.count()):
            if self.preset_combo.itemData(index) == config_id:
                self.preset_combo.blockSignals(True)
                self.preset_combo.setCurrentIndex(index)
                self.preset_combo.blockSignals(False)
                return
        self.preset_combo.blockSignals(True)
        self.preset_combo.setCurrentIndex(-1)
        self.preset_combo.blockSignals(False)


def _section_item(text: str) -> QListWidgetItem:
    item = QListWidgetItem(text)
    item.setFlags(Qt.ItemFlag.NoItemFlags)
    item.setForeground(Qt.GlobalColor.gray)
    return item


def _set_combo_data(combo: QComboBox, value: str) -> None:
    index = combo.findData(value)
    combo.setCurrentIndex(index if index >= 0 else 0)


def _set_combo_text(combo: QComboBox, value: str) -> None:
    index = combo.findText(value)
    combo.setCurrentIndex(index if index >= 0 else 0)


def _split_content_types(text: str) -> list[str]:
    parts = [part.strip() for part in text.replace(",", "、").split("、")]
    return [part for part in parts if part] or ["通用"]


def _config_detail_text(config: VisualModelConfig) -> str:
    enabled_stages = "、".join(stage.label for stage in config.stages if stage.enabled)
    if not enabled_stages:
        enabled_stages = "尚未配置阶段"
    recommended_models = "、".join(config.recommended_models) or "按所选阶段配置"
    stage_summary = "；".join(
        f"{stage.label}：{SERVICE_TYPE_LABELS.get(stage.service_type, stage.service_type)}"
        for stage in config.stages
    )
    return (
        f"启用阶段：{enabled_stages}。\n"
        f"阶段服务：{stage_summary}。\n"
        f"需要模型：{recommended_models}。"
    )


def _stage_label(stage: str) -> str:
    labels = {
        "separation": "人声分离",
        "asr": "语音识别",
        "diarization": "说话人识别",
        "translation": "翻译",
        "tts": "语音合成",
    }
    return labels.get(stage, stage)


def _validation_text(status: str) -> str:
    return {
        "ready": "可用",
        "warning": "需检查",
        "missing": "缺少模型",
        "failed": "不可用",
        "unchecked": "尚未检查",
    }.get(status, "尚未检查")
