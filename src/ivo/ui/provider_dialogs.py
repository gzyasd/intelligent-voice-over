"""Provider configuration dialog for adding/editing vendor services."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ivo.model_services.provider_registry import ConfigField, ProviderRegistry, ProviderRegistryEntry
from ivo.ui.theme import (
    mark_error_border,
    mark_icon_button,
    mark_secondary_button,
    mark_status_danger,
    mark_status_success,
    mark_warning_text,
)


class ProviderConfigDialog(QDialog):
    """Dialog for adding or editing a provider configuration."""

    config_saved = Signal(dict)

    def __init__(
        self,
        *,
        stage: str,
        registry: ProviderRegistry | None = None,
        existing_values: dict[str, str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("添加供应商" if not existing_values else "编辑供应商")
        self.setMinimumWidth(480)

        self._stage = stage
        self._registry = registry or ProviderRegistry()
        self._existing = existing_values or {}
        self._field_widgets: dict[str, QWidget] = {}

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        # Provider selector – use registry entries only (local models are entries with requires_api_key=False)
        self.provider_combo = QComboBox()
        entries = self._registry.list_for_stage(self._stage)
        for entry in entries:
            if entry.mvp_enabled:
                self.provider_combo.addItem(entry.display_name, entry.provider_id)

        # Pre-select provider from existing values (edit mode) – before signal connection
        existing_provider_id = self._existing.get("provider_id")
        if existing_provider_id:
            for i in range(self.provider_combo.count()):
                if self.provider_combo.itemData(i) == existing_provider_id:
                    self.provider_combo.setCurrentIndex(i)
                    break

        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)

        form = QFormLayout()
        form.setSpacing(8)
        form.addRow("供应商", self.provider_combo)

        # Dynamic config area
        self._config_form = QFormLayout()
        self._config_form.setSpacing(8)

        # Display name (always present)
        self.display_name_edit = QLineEdit()
        self.display_name_edit.setPlaceholderText("如：公司账号 / 个人账号")
        self.display_name_edit.setText(self._existing.get("display_name", ""))
        form.addRow("配置名称", self.display_name_edit)

        layout.addLayout(form)

        # Cloud upload warning
        self._cloud_warning = QLabel("⚠ 使用云端供应商会上传音频文件到第三方服务")
        self._cloud_warning.setWordWrap(True)
        mark_warning_text(self._cloud_warning)
        self._cloud_warning.hide()
        layout.addWidget(self._cloud_warning)

        layout.addLayout(self._config_form)

        # Local model path (hidden by default)
        self._local_path_edit: QLineEdit | None = None
        self._local_browse_btn: QPushButton | None = None

        # Test connection button
        self.test_button = QPushButton("测试连接")
        self.test_button.setStyleSheet("")
        mark_secondary_button(self.test_button)
        self.test_button.setEnabled(False)
        self.test_button.clicked.connect(self._on_test_connection)
        self.test_result_label = QLabel("")
        layout.addWidget(self.test_button)
        layout.addWidget(self.test_result_label)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        self._button_box = button_box
        layout.addWidget(button_box)

        self.setLayout(layout)

        # Initialize fields for the selected provider
        if self.provider_combo.count() > 0:
            self._on_provider_changed(self.provider_combo.currentIndex())

    def _clear_config_form(self) -> None:
        while self._config_form.count():
            item = self._config_form.takeAt(0)
            if item is None:
                break
            w = item.widget()
            if w is not None:
                w.deleteLater()
            else:
                sub = item.layout()
                if sub is not None:
                    while sub.count():
                        child = sub.takeAt(0)
                        if child is not None:
                            cw = child.widget()
                            if cw is not None:
                                cw.deleteLater()
        self._field_widgets.clear()
        self._local_path_edit = None
        self._local_browse_btn = None

    def _is_local_provider(self, provider_id: str | None) -> bool:
        """Check if a provider is local (no API key required) via registry."""
        if not provider_id:
            return False
        entry = self._registry.get(provider_id)
        return entry is not None and not entry.requires_api_key

    def _on_provider_changed(self, index: int) -> None:
        self._clear_config_form()
        provider_id = self.provider_combo.currentData()

        if provider_id:
            entry = self._registry.get(provider_id)
            if entry and not entry.requires_api_key:
                self._cloud_warning.hide()
                self._build_local_fields(entry)
            elif entry:
                self._cloud_warning.show()
                self._build_cloud_fields(entry)
            else:
                self._cloud_warning.hide()

        self._update_test_button_enabled()

    def _build_cloud_fields(self, entry: ProviderRegistryEntry) -> None:
        """Build form fields from provider's stage-specific config fields."""
        for field_def in self._registry.get_config_fields(entry.provider_id, self._stage):
            widget = self._create_field_widget(field_def)
            self._field_widgets[field_def.name] = widget
            self._config_form.addRow(field_def.display_name, widget)

            # Pre-fill existing values
            if field_def.name in self._existing:
                if isinstance(widget, QLineEdit):
                    widget.setText(str(self._existing[field_def.name]))
                elif isinstance(widget, QComboBox):
                    widget.setCurrentText(str(self._existing[field_def.name]))

            # Connect change signals
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda _: self._update_test_button_enabled())
            elif isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(lambda _: self._update_test_button_enabled())

        self.test_button.show()

    def _build_local_fields(self, entry: ProviderRegistryEntry) -> None:
        """Build local model configuration fields from registry entry."""
        for field_def in self._registry.get_config_fields(entry.provider_id, self._stage):
            # Special handling for local_model_path: add browse button inline
            if field_def.name == "local_model_path":
                path_edit = QLineEdit()
                if field_def.placeholder:
                    path_edit.setPlaceholderText(field_def.placeholder)
                if field_def.default:
                    path_edit.setText(field_def.default)
                if field_def.name in self._existing:
                    path_edit.setText(str(self._existing[field_def.name]))
                self._local_path_edit = path_edit

                browse_btn = QPushButton("浏览...")
                browse_btn.setStyleSheet("")
                mark_secondary_button(browse_btn)
                browse_btn.clicked.connect(self._browse_local_model)
                self._local_browse_btn = browse_btn

                row = QHBoxLayout()
                row.addWidget(path_edit, 1)
                row.addWidget(browse_btn)
                self._config_form.addRow(field_def.display_name, row)
                continue

            widget = self._create_field_widget(field_def)
            self._field_widgets[field_def.name] = widget
            self._config_form.addRow(field_def.display_name, widget)

            # Pre-fill existing values
            if field_def.name in self._existing:
                if isinstance(widget, QLineEdit):
                    widget.setText(str(self._existing[field_def.name]))
                elif isinstance(widget, QComboBox):
                    widget.setCurrentText(str(self._existing[field_def.name]))

        self.test_button.hide()

    def _create_field_widget(self, field_def: ConfigField) -> QWidget:
        """Create a form widget from a ConfigField definition."""
        if field_def.field_type == "api_key":
            return self._create_api_key_field(field_def)
        elif field_def.field_type == "select" and field_def.options:
            combo = QComboBox()
            combo.addItems(list(field_def.options))
            if field_def.default:
                combo.setCurrentText(field_def.default)
            return combo
        else:
            edit = QLineEdit()
            if field_def.placeholder:
                edit.setPlaceholderText(field_def.placeholder)
            if field_def.default:
                edit.setText(field_def.default)
            return edit

    def _create_api_key_field(self, field_def: ConfigField) -> QWidget:
        """Create an API key field with show/hide toggle."""
        container = QWidget()
        h_layout = QHBoxLayout()
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(4)

        edit = QLineEdit()
        edit.setEchoMode(QLineEdit.EchoMode.Password)
        edit.setPlaceholderText(field_def.placeholder or "输入 API Key")
        edit.setObjectName(f"api_key_{field_def.name}")

        toggle_btn = QPushButton("👁")
        toggle_btn.setAccessibleName("切换API Key可见性")
        toggle_btn.setToolTip("显示或隐藏 API Key")
        toggle_btn.setFixedSize(32, 32)
        toggle_btn.setStyleSheet("")
        mark_icon_button(toggle_btn)

        def toggle_visibility() -> None:
            if edit.echoMode() == QLineEdit.EchoMode.Password:
                edit.setEchoMode(QLineEdit.EchoMode.Normal)
                toggle_btn.setText("🔒")
            else:
                edit.setEchoMode(QLineEdit.EchoMode.Password)
                toggle_btn.setText("👁")

        toggle_btn.clicked.connect(toggle_visibility)
        h_layout.addWidget(edit, 1)
        h_layout.addWidget(toggle_btn)
        container.setLayout(h_layout)
        # Store reference to edit for value retrieval
        container.setProperty("_edit", edit)
        return container

    def _browse_local_model(self) -> None:
        if self._local_path_edit is None:
            return
        path = QFileDialog.getExistingDirectory(
            self, "选择模型目录", self._local_path_edit.text() or "models"
        )
        if path:
            self._local_path_edit.setText(path)

    def _get_api_key_edit(self, widget: QWidget) -> QLineEdit | None:
        """Extract QLineEdit from api key container widget."""
        edit = widget.property("_edit")
        if isinstance(edit, QLineEdit):
            return edit
        return None

    def _get_field_value(self, name: str, widget: QWidget) -> str:
        """Get the string value from a field widget."""
        if isinstance(widget, QLineEdit):
            return widget.text().strip()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        else:
            edit = self._get_api_key_edit(widget)
            if edit:
                return edit.text().strip()
        return ""

    def _required_fields_are_filled(self) -> bool:
        """Check whether all required fields for the selected provider are filled."""
        provider_id = self.provider_combo.currentData()
        if self._is_local_provider(provider_id):
            return True  # Local doesn't need connection testing.
        entry = self._registry.get(provider_id) if provider_id else None
        if entry is None:
            return False
        has_required_field = False
        for field_def in self._registry.get_config_fields(entry.provider_id, self._stage):
            if not field_def.required:
                continue
            has_required_field = True
            widget = self._field_widgets.get(field_def.name)
            if widget is None:
                return False
            if not self._get_field_value(field_def.name, widget):
                return False
        return has_required_field or bool(entry.protocols)

    def _update_test_button_enabled(self) -> None:
        self.test_button.setEnabled(self._required_fields_are_filled())

    def _on_test_connection(self) -> None:
        """Run credential validation via the provider adapter and update UI."""
        provider_id = self.provider_combo.currentData()
        if not provider_id or self._is_local_provider(provider_id):
            self.test_result_label.setText("本地部署无需测试连接")
            return

        entry = self._registry.get(provider_id)
        if entry is None:
            self.test_result_label.setText("未找到供应商注册信息")
            return

        api_key = self.api_key()
        api_key_required = any(
            field_def.field_type == "api_key" and field_def.required
            for field_def in self._registry.get_config_fields(entry.provider_id, self._stage)
        )
        if api_key_required and not api_key:
            self.test_result_label.setText("请先填写 API Key")
            return

        self.test_button.setEnabled(False)
        self.test_result_label.setText("正在验证…")
        try:
            from ivo.model_services.validators import create_validator

            values = self.values()
            # Translation providers ask for the full request endpoint. Other
            # providers still use a base URL.
            base_url = str(values.get("request_url") or values.get("base_url") or "")
            if not base_url and entry.default_base_url:
                base_url = entry.default_base_url

            validator = create_validator(
                provider_id=provider_id,
                stage=self._stage,
                api_key=api_key,
                base_url=base_url,
            )
            result = validator.validate_credentials()
            if result.ok:
                self.test_result_label.setText(f"✓ 连接成功 ({result.latency_ms}ms)")
                mark_status_success(self.test_result_label)
            else:
                self.test_result_label.setText(
                    f"✗ {result.error_code}: {result.error_message or '验证失败'}"
                )
                mark_status_danger(self.test_result_label)
        except Exception as exc:
            self.test_result_label.setText(f"✗ 异常: {exc}")
            mark_status_danger(self.test_result_label)
        finally:
            self.test_button.setEnabled(True)

    def values(self) -> dict[str, object]:
        """Return all configured field values as a dict."""
        provider_id = self.provider_combo.currentData()
        result: dict[str, object] = {
            "display_name": self.display_name_edit.text().strip(),
            "stage": self._stage,
            "provider_id": provider_id,
        }
        is_local = self._is_local_provider(provider_id)
        result["kind"] = "local" if is_local else "api"

        for name, widget in self._field_widgets.items():
            result[name] = self._get_field_value(name, widget)

        # local_model_path is removed from _field_widgets when browse button is added
        if self._local_path_edit and "local_model_path" not in result:
            result["local_model_path"] = self._local_path_edit.text().strip()

        return result

    def _on_accept(self) -> None:
        if not self.display_name_edit.text().strip():
            mark_error_border(self.display_name_edit)
            return
        values = self.values()
        self.config_saved.emit(values)
        self.accept()

    def display_name(self) -> str:
        return self.display_name_edit.text().strip()

    def api_key(self) -> str:
        """Return the first API key field value found."""
        provider_id = self.provider_combo.currentData()
        if self._is_local_provider(provider_id):
            return ""
        entry = self._registry.get(provider_id) if provider_id else None
        if entry is None:
            return ""
        for field_def in self._registry.get_config_fields(entry.provider_id, self._stage):
            if field_def.field_type == "api_key":
                widget = self._field_widgets.get(field_def.name)
                if widget:
                    return self._get_field_value(field_def.name, widget)
        return ""

    def is_local(self) -> bool:
        return self._is_local_provider(self.provider_combo.currentData())
