"""Scheme management page with left-right split layout."""

from __future__ import annotations

import uuid
from typing import cast

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ivo.model_services.provider_config import (
    DubbingScheme,
    SchemeStageBinding,
    StageProviderConfig,
)
from ivo.model_services.provider_store import ProviderStore
from ivo.model_services.stages import STAGE_LABELS, STAGE_NAMES, StageName
from ivo.workspace_paths import default_config_dir
from ivo.ui.theme import (
    mark_card,
    mark_compact_button,
    mark_danger_button,
    mark_heading3,
    mark_item_title,
    mark_link_button,
    mark_primary_button,
    mark_scheme_list_item,
    mark_scheme_list_panel,
    mark_secondary_button,
    mark_status_danger,
    mark_status_dot,
    mark_status_success,
    mark_status_warning,
    mark_sub_text,
)


_STAGE_ICONS = {
    "separation": "🔊",
    "asr": "🗣",
    "diarization": "👤",
    "translation": "🌐",
    "tts": "🔈",
}


def _effective_validation_status(config: StageProviderConfig) -> str:
    """Return the effective validation status for a config."""
    if config.kind == "local":
        if config.last_validation_status == "failed":
            return "failed"
        return "ready"
    return config.last_validation_status


class _ServiceSelectionDialog(QDialog):
    """Dialog for selecting a configured service for a scheme stage."""

    def __init__(
        self,
        *,
        stage: StageName,
        store: ProviderStore,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._stage = stage
        self._store = store
        self._selected_config_id: str | None = None
        self.setWindowTitle(f"选择 {STAGE_LABELS.get(stage, stage)} 服务")
        self.setFixedWidth(480)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        configs = [
            c for c in self._store.load_stage_configs() if c.stage == self._stage
        ]

        self._list = QListWidget()
        if not configs:
            placeholder = QListWidgetItem(
                '请先在"模型服务"页配置该阶段的服务'
            )
            placeholder.setFlags(placeholder.flags() & ~Qt.ItemFlag(0x01))
            self._list.addItem(placeholder)
        else:
            sorted_configs = sorted(
                configs,
                key=lambda c: (_effective_validation_status(c) != "ready", c.display_name),
            )
            for config in sorted_configs:
                status_icon = "✓" if _effective_validation_status(config) == "ready" else "●"
                text = f"{status_icon} {config.display_name}（{config.provider_key} - {config.model_name or config.protocol}）"
                item = QListWidgetItem(text)
                item.setData(0x0100, config.id)
                self._list.addItem(item)

        layout.addWidget(self._list)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def _on_accept(self) -> None:
        current = self._list.currentItem()
        if current:
            config_id = current.data(0x0100)
            if isinstance(config_id, str):
                self._selected_config_id = config_id
                self.accept()
                return
        self.reject()

    def selected_config_id(self) -> str | None:
        return self._selected_config_id


class _StageRow(QFrame):
    """A single stage row in the scheme content area."""

    select_requested = Signal(str)  # stage name
    jump_to_services = Signal(str)  # stage name

    def __init__(self, stage: StageName, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.stage = stage
        self._config_id: str | None = None
        self._config_display: str = ""
        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet("")
        mark_card(self)
        layout = QHBoxLayout()
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)

        icon = _STAGE_ICONS.get(self.stage, "📦")
        label = STAGE_LABELS.get(self.stage, self.stage)
        name_label = QLabel(f"{icon}  {label}")
        mark_item_title(name_label)
        name_label.setMinimumWidth(140)
        layout.addWidget(name_label)

        self._service_label = QLabel("未配置")
        self._service_label.setMinimumWidth(1)
        mark_sub_text(self._service_label)
        layout.addWidget(self._service_label, 1)

        self._status_dot = QLabel("○")
        mark_status_dot(self._status_dot, "unchecked")
        layout.addWidget(self._status_dot)

        self._select_button = QPushButton("选择")
        self._select_button.setStyleSheet("")
        mark_secondary_button(self._select_button)
        self._select_button.setFixedHeight(32)
        self._select_button.clicked.connect(lambda: self.select_requested.emit(self.stage))
        layout.addWidget(self._select_button)

        self._jump_button = QPushButton("模型服务 >")
        self._jump_button.setStyleSheet("")
        mark_link_button(self._jump_button)
        self._jump_button.setFixedHeight(32)
        self._jump_button.clicked.connect(lambda: self.jump_to_services.emit(self.stage))
        self._jump_button.setToolTip("跳转到模型服务页配置该阶段的服务")
        layout.addWidget(self._jump_button)

        self.setLayout(layout)

    def set_config(self, config: StageProviderConfig | None) -> None:
        if config:
            self._config_id = config.id
            self._config_display = (
                f"{config.display_name}（{config.provider_key} - {config.model_name or config.protocol}）"
            )
            self._service_label.setText(self._config_display)
            self._service_label.setStyleSheet("")

            status = _effective_validation_status(config)
            dot_status = status if status in ("ready", "danger", "warning") else "unchecked"
            if status == "failed":
                dot_status = "danger"
            self._status_dot.setText("●")
            mark_status_dot(self._status_dot, dot_status)
            tooltips = {"ready": "已验证", "danger": "验证失败", "unchecked": "未验证", "warning": "未验证"}
            self._status_dot.setToolTip(tooltips.get(dot_status, "未验证"))

            self._select_button.setText("更换")
        else:
            self._config_id = None
            self._config_display = ""
            self._service_label.setText("未配置")
            mark_sub_text(self._service_label)
            self._status_dot.setText("○")
            mark_status_dot(self._status_dot, "unchecked")
            self._select_button.setText("选择")

    def config_id(self) -> str | None:
        return self._config_id


class SchemeManagementPage(QWidget):
    """Page for managing dubbing schemes with left-right split layout."""

    scheme_changed = Signal()
    jump_to_services = Signal(str)  # stage name

    def __init__(
        self,
        *,
        store: ProviderStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store or ProviderStore(default_config_dir())
        self._current_scheme: DubbingScheme | None = None
        self._stage_rows: dict[StageName, _StageRow] = {}
        self._scheme_buttons: dict[str, QPushButton] = {}
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._build_ui()
        self._load_schemes()

    def _build_ui(self) -> None:
        outer = QHBoxLayout()
        outer.setContentsMargins(28, 28, 28, 28)
        outer.setSpacing(16)

        # ── Left panel: scheme list ──
        left_panel = QFrame()
        left_panel.setStyleSheet("")
        mark_scheme_list_panel(left_panel)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(4)

        left_panel.setFixedWidth(220)

        # Scroll area for scheme list
        self._list_container = QVBoxLayout()
        self._list_container.setSpacing(2)
        self._list_container.setAlignment(Qt.AlignmentFlag.AlignTop)
        left_layout.addLayout(self._list_container)

        left_layout.addStretch()

        # New scheme button at bottom
        self._new_scheme_button = QPushButton("+ 新建方案")
        self._new_scheme_button.setStyleSheet("")
        mark_primary_button(self._new_scheme_button)
        self._new_scheme_button.clicked.connect(self._on_new_scheme)
        left_layout.addWidget(self._new_scheme_button)

        left_panel.setLayout(left_layout)
        outer.addWidget(left_panel, 0)

        # ── Right panel: scheme detail ──
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)

        right_content = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)

        # Title
        title = QLabel("方案管理")
        title.setObjectName("PageTitle")
        right_layout.addWidget(title)

        # Scheme info card
        info_card = QFrame()
        info_card.setStyleSheet("")
        mark_card(info_card)
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(18, 14, 18, 14)
        info_layout.setSpacing(12)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("方案名称")
        self._title_edit.textChanged.connect(self._mark_scheme_modified)
        info_layout.addWidget(self._title_edit, 1)

        self._copy_scheme_button = QPushButton("复制")
        self._copy_scheme_button.setStyleSheet("")
        mark_compact_button(self._copy_scheme_button)
        self._copy_scheme_button.clicked.connect(self._on_copy_scheme)
        info_layout.addWidget(self._copy_scheme_button)

        self._delete_scheme_button = QPushButton("删除")
        self._delete_scheme_button.setStyleSheet("")
        mark_danger_button(self._delete_scheme_button)
        self._delete_scheme_button.clicked.connect(self._on_delete_scheme)
        info_layout.addWidget(self._delete_scheme_button)

        info_card.setLayout(info_layout)
        right_layout.addWidget(info_card)

        # Stage config card
        stage_card = QFrame()
        stage_card.setStyleSheet("")
        mark_card(stage_card)
        stage_layout = QVBoxLayout()
        stage_layout.setContentsMargins(18, 18, 18, 18)
        stage_layout.setSpacing(10)

        stages_title = QLabel("阶段配置")
        mark_heading3(stages_title)
        stage_layout.addWidget(stages_title)

        for stage in STAGE_NAMES:
            row = _StageRow(stage)
            row.select_requested.connect(self._on_select_service)
            row.jump_to_services.connect(self.jump_to_services.emit)
            self._stage_rows[stage] = row
            stage_layout.addWidget(row)

        stage_card.setLayout(stage_layout)
        right_layout.addWidget(stage_card)

        # Validation status + action bar
        actions = QHBoxLayout()
        self._validate_button = QPushButton("验证方案")
        self._validate_button.setStyleSheet("")
        mark_secondary_button(self._validate_button)
        self._validate_button.clicked.connect(self._on_validate)
        actions.addWidget(self._validate_button)

        self._set_default_button = QPushButton("设为默认")
        self._set_default_button.setStyleSheet("")
        mark_primary_button(self._set_default_button)
        self._set_default_button.clicked.connect(self._on_set_default)
        actions.addWidget(self._set_default_button)

        actions.addStretch()
        self._status_label = QLabel("")
        self._status_label.setObjectName("SecondaryText")
        actions.addWidget(self._status_label)

        right_layout.addLayout(actions)
        right_layout.addStretch()

        right_content.setLayout(right_layout)
        right_scroll.setWidget(right_content)
        outer.addWidget(right_scroll, 1)

        self.setLayout(outer)

    def _load_schemes(self) -> None:
        """Load all schemes into the left panel list."""
        # Clear existing buttons
        for btn in self._scheme_buttons.values():
            self._button_group.removeButton(btn)
            self._list_container.removeWidget(btn)
            btn.deleteLater()
        self._scheme_buttons.clear()

        schemes = self._store.load_schemes()

        if not schemes:
            default = DubbingScheme(
                id="default-mock",
                display_name="全自动 Mock 预览",
                description="使用 mock 适配器进行预览",
                bindings=[],
            )
            self._store.save_scheme(default)
            schemes = [default]

        default_id = self._store.load_default_scheme_id()

        for scheme in schemes:
            is_default = scheme.id == default_id
            btn = QPushButton(scheme.display_name)
            btn.setStyleSheet("")
            mark_scheme_list_item(btn)
            btn.setCheckable(True)
            btn.setToolTip(f"{scheme.display_name}{' (默认)' if is_default else ''}")
            btn.clicked.connect(lambda checked, sid=scheme.id: self._on_scheme_clicked(sid))
            self._button_group.addButton(btn)
            self._list_container.addWidget(btn)
            self._scheme_buttons[scheme.id] = btn

        # Select first scheme
        if schemes:
            self._select_scheme(schemes[0].id)

    def _select_scheme(self, scheme_id: str) -> None:
        """Select a scheme by id and update the right panel."""
        scheme = self._store.get_scheme(scheme_id)
        if scheme is None:
            return
        self._current_scheme = scheme

        # Update button checked state
        btn = self._scheme_buttons.get(scheme_id)
        if btn:
            btn.setChecked(True)

        # Update right panel
        self._title_edit.blockSignals(True)
        self._title_edit.setText(scheme.display_name)
        self._title_edit.blockSignals(False)
        self._load_stage_bindings(scheme)

    def _on_scheme_clicked(self, scheme_id: str) -> None:
        self._select_scheme(scheme_id)

    def _load_stage_bindings(self, scheme: DubbingScheme) -> None:
        """Load stage bindings into the UI."""
        binding_map: dict[str, str] = {}
        for binding in scheme.bindings:
            binding_map[binding.stage] = binding.stage_config_id

        for stage, row in self._stage_rows.items():
            config_id = binding_map.get(stage)
            if config_id:
                config = self._store.get_stage_config(config_id)
                row.set_config(config)
            else:
                row.set_config(None)

    def _on_select_service(self, stage: str) -> None:
        """Open service selection dialog for a stage."""
        stage_name = cast(StageName, stage)
        dialog = _ServiceSelectionDialog(
            stage=stage_name,
            store=self._store,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config_id = dialog.selected_config_id()
            if config_id:
                self._update_stage_binding(stage_name, config_id)

    def _update_stage_binding(self, stage: str, config_id: str) -> None:
        """Update the binding for a stage in the current scheme."""
        if self._current_scheme is None:
            return
        stage_name = cast(StageName, stage)

        config = self._store.get_stage_config(config_id)
        self._stage_rows[stage_name].set_config(config)

        new_bindings = [
            b for b in self._current_scheme.bindings if b.stage != stage_name
        ]
        new_bindings.append(SchemeStageBinding(stage=stage_name, stage_config_id=config_id))
        self._current_scheme = self._current_scheme.model_copy(
            update={"bindings": new_bindings}
        )
        self._store.save_scheme(self._current_scheme)
        self.scheme_changed.emit()

    def _on_new_scheme(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("新建方案")
        dialog.setFixedWidth(400)
        dlg_layout = QVBoxLayout()
        dlg_layout.setContentsMargins(18, 18, 18, 18)

        form = QFormLayout()
        name_edit = QLineEdit()
        name_edit.setPlaceholderText("方案名称")
        form.addRow("方案名称", name_edit)
        lang_combo = QComboBox()
        lang_combo.addItems(["英语", "日语", "韩语"])
        form.addRow("源语言", lang_combo)
        dlg_layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dlg_layout.addWidget(buttons)
        dialog.setLayout(dlg_layout)

        if dialog.exec() == QDialog.DialogCode.Accepted and name_edit.text().strip():
            scheme_id = str(uuid.uuid4())[:8]
            scheme = DubbingScheme(
                id=scheme_id,
                display_name=name_edit.text().strip(),
                bindings=[],
            )
            self._store.save_scheme(scheme)
            self._load_schemes()
            self._select_scheme(scheme_id)

    def _on_copy_scheme(self) -> None:
        if self._current_scheme is None:
            return
        copy_id = str(uuid.uuid4())[:8]
        copy = self._current_scheme.model_copy(
            update={
                "id": copy_id,
                "display_name": f"{self._current_scheme.display_name} 副本",
            },
            deep=True,
        )
        self._store.save_scheme(copy)
        self._load_schemes()
        self._select_scheme(copy_id)

    def _on_delete_scheme(self) -> None:
        if self._current_scheme is None:
            return
        if self._current_scheme.id == "default-mock":
            QMessageBox.warning(self, "无法删除", "默认方案不能删除。")
            return
        result = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除方案「{self._current_scheme.display_name}」吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self._store.delete_scheme(self._current_scheme.id)
            self._load_schemes()

    def _on_validate(self) -> None:
        if self._current_scheme is None:
            return
        from ivo.model_services.provider_registry import ProviderRegistry

        registry = ProviderRegistry()
        missing: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []
        for stage in STAGE_NAMES:
            row = self._stage_rows[stage]
            cid = row.config_id()
            label = STAGE_LABELS.get(stage, stage)
            if not cid:
                missing.append(label)
                continue
            config = self._store.get_stage_config(cid)
            if config is None:
                missing.append(label)
                continue
            if config.kind == "api":
                entry = registry.get(config.provider_key)
                api_key_required = False
                if entry:
                    api_key_required = any(
                        f.name == "api_key" and f.required
                        for f in entry.config_fields
                    )
                if config.account_id:
                    account = self._store.get_account(config.account_id)
                    if account is None:
                        warnings.append(f"{label}: 账号不存在")
                    elif account.api_key_ref is None and api_key_required:
                        warnings.append(f"{label}: 未保存 API Key")
                if config.last_validation_status == "failed":
                    warnings.append(f"{label}: 上次验证失败")
                elif config.last_validation_status == "unchecked":
                    if api_key_required:
                        warnings.append(
                            f"{label}: 尚未进行连接测试，请先点击「测试连接」验证"
                        )
                elif config.last_validation_status not in ("ready",):
                    warnings.append(f"{label}: 验证状态异常 ({config.last_validation_status})")

        if not missing and not errors:
            try:
                from ivo.model_services.adapter_factory import (
                    ProviderAdapterFactory,
                    _LOCAL_COMMAND_TEMPLATES,
                )
                from ivo.model_services.secret_store import SecretStore

                secret_store = SecretStore(default_config_dir())
                factory = ProviderAdapterFactory(
                    registry=registry,
                    provider_store=self._store,
                    secret_store=secret_store,
                )
                for binding in self._current_scheme.bindings:
                    config = self._store.get_stage_config(binding.stage_config_id)
                    if config is None:
                        continue
                    label = STAGE_LABELS.get(binding.stage, binding.stage)
                    factory.create(config)
                    if config.kind == "local":
                        template = _LOCAL_COMMAND_TEMPLATES.get(config.provider_key)
                        if template is None:
                            warnings.append(
                                f"{label}: 本地模型 '{config.provider_key}' 缺少内置命令模板"
                            )
                        elif not template.get("command"):
                            warnings.append(
                                f"{label}: 本地模型 '{config.provider_key}' 的命令模板为空"
                            )
            except NotImplementedError as exc:
                errors.append(f"编译失败: {exc}")
            except Exception as exc:
                warnings.append(f"编译检查异常: {exc}")

        if errors:
            self._status_label.setText("❌ " + " | ".join(errors))
            mark_status_danger(self._status_label)
        elif missing:
            self._status_label.setText(
                f"未配置的阶段：{'、'.join(missing)}"
            )
            mark_status_danger(self._status_label)
        elif warnings:
            self._status_label.setText("⚠ " + " | ".join(warnings))
            mark_status_warning(self._status_label)
        else:
            self._status_label.setText("方案验证通过，所有服务已配置且可用")
            mark_status_success(self._status_label)

    def _on_set_default(self) -> None:
        if self._current_scheme is None:
            self._status_label.setText("请先选择一个方案")
            mark_status_danger(self._status_label)
            return
        try:
            self._store.save_default_scheme_id(self._current_scheme.id)
            self._status_label.setText(
                f"✓ 已将「{self._current_scheme.display_name}」设为默认方案"
            )
            mark_status_success(self._status_label)
            self._status_label.setStyleSheet("font-weight: 600;")
            # Refresh list to update default badge
            current_id = self._current_scheme.id
            self._load_schemes()
            self._select_scheme(current_id)
        except Exception as exc:
            self._status_label.setText(f"设置失败：{exc}")
            mark_status_danger(self._status_label)

    def _mark_scheme_modified(self, *_args: object) -> None:
        """Auto-save scheme when title changes."""
        if self._current_scheme is None:
            return
        title = self._title_edit.text().strip()
        if title and title != self._current_scheme.display_name:
            self._current_scheme = self._current_scheme.model_copy(
                update={"display_name": title}
            )
            self._store.save_scheme(self._current_scheme)
            # Update button text
            btn = self._scheme_buttons.get(self._current_scheme.id)
            if btn:
                btn.setText(title)
                default_id = self._store.load_default_scheme_id()
                btn.setToolTip(f"{title}{' (默认)' if self._current_scheme.id == default_id else ''}")
            self.scheme_changed.emit()

    def current_scheme(self) -> DubbingScheme | None:
        return self._current_scheme

    def refresh(self) -> None:
        """Reload schemes from store."""
        current_id = self._current_scheme.id if self._current_scheme else None
        self._load_schemes()
        if current_id and current_id in self._scheme_buttons:
            self._select_scheme(current_id)
