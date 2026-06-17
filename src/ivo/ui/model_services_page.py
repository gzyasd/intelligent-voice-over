"""Model services page with 5 stage cards and local model dependency management."""

from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ivo.model_services.local_models import (
    ALL_LOCAL_MODEL_SERVICES,
    DependencyStatus,
)
from ivo.model_services.provider_config import ProviderAccount, StageProviderConfig
from ivo.model_services.provider_registry import ProviderRegistry
from ivo.model_services.provider_store import ProviderStore
from ivo.model_services.secret_store import SecretStore
from ivo.model_services.stages import STAGE_LABELS, STAGE_NAMES, StageName
from ivo.core.user_settings import PYPI_MIRRORS, UserSettingsStore
from ivo.ui.provider_dialogs import ProviderConfigDialog
from ivo.workspace_paths import default_config_dir, default_user_settings_path
from ivo.ui.theme import (
    active_color,
    mark_compact_button,
    mark_danger_button,
    mark_heading2,
    mark_heading3,
    mark_item_title,
    mark_kind_badge,
    mark_link_button,
    mark_primary_button,
    mark_provider_item,
    mark_stage_list_item,
    mark_stage_panel,
    mark_status_dot,
    mark_sub_text,
)


# --- Sensitive field names that must NOT be stored in auth_fields ---
_SENSITIVE_KEYS = frozenset({
    "api_key", "apikey", "secret_key", "token", "license",
    "license_key", "hf_token", "password", "auth_token",
})


# Stage name → protocol keyword fragments for matching
_STAGE_PROTOCOL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "separation": ("separation", "separate"),
    "asr": ("asr", "transcribe"),
    "diarization": ("diarize", "diarization"),
    "translation": ("translation", "translate", "compatible"),
    "tts": ("tts", "synth"),
}

# Keys handled by dedicated StageProviderConfig fields – NOT saved in extra
# Also excludes _SENSITIVE_KEYS so api_key / hf_token etc. never land in plaintext JSON.
_EXTRA_EXCLUDE_KEYS = frozenset({
    "display_name", "stage", "provider_id", "kind",
    "local_model_path", "device", "model_name", "precision",
    *_SENSITIVE_KEYS,
})


# --- Status helpers ---
def _status_color(status: str) -> str:
    """Return the active theme colour for a provider validation status."""
    mapping = {
        "ready": "success",
        "unchecked": "warning",
        "failed": "danger",
        "missing": "danger",
    }
    return active_color(mapping.get(status, "text_secondary"))

_STATUS_LABELS = {
    "ready": "已验证",
    "unchecked": "未验证",
    "failed": "验证失败",
    "missing": "未就绪",
}

_STAGE_ICONS = {
    "separation": "🔊",
    "asr": "🗣",
    "diarization": "👤",
    "translation": "🌐",
    "tts": "🔈",
}

# Stages that have local model services
_LOCAL_STAGES = ["separation", "asr", "diarization", "tts"]


class _PipInstallWorker(QThread):
    """Background worker to run pip install / pip install --upgrade / --force-reinstall."""

    finished = Signal(str, bool, str)  # package_name, success, output

    def __init__(
        self,
        package_name: str,
        venv_python: Path,
        upgrade: bool = False,
        force_reinstall: bool = False,
        mirror_url: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._package_name = package_name
        self._venv_python = venv_python
        self._upgrade = upgrade
        self._force_reinstall = force_reinstall
        self._mirror_url = mirror_url

    def run(self) -> None:
        cmd = [str(self._venv_python), "-m", "pip", "install"]
        if self._mirror_url:
            cmd.extend(["-i", self._mirror_url])
        if self._upgrade:
            cmd.append("--upgrade")
        if self._force_reinstall:
            cmd.append("--force-reinstall")
        cmd.append(self._package_name)
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600
            )
            ok = result.returncode == 0
            output = result.stdout if ok else result.stderr
            self.finished.emit(self._package_name, ok, output.strip())
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.finished.emit(self._package_name, False, str(exc))


class _DepUpgradeCheckWorker(QThread):
    """Background worker to check latest version of a single package."""

    result_ready = Signal(str, str, str)  # package_name, current_version, latest_version

    def __init__(
        self,
        package_name: str,
        current_version: str,
        mirror_url: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._package_name = package_name
        self._current_version = current_version
        self._mirror_url = mirror_url

    def run(self) -> None:
        from ivo.model_services.local_models import _get_latest_version

        latest = _get_latest_version(self._package_name, mirror_url=self._mirror_url)
        self.result_ready.emit(self._package_name, self._current_version, latest)


class _DepStatusLoadWorker(QThread):
    """Background worker to load all dependency statuses without blocking UI."""

    result_ready = Signal(object)  # list[DependencyStatus]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

    def run(self) -> None:
        all_statuses: list[DependencyStatus] = []
        for svc in ALL_LOCAL_MODEL_SERVICES:
            try:
                all_statuses.extend(svc.check_dependency_status())
            except Exception:
                pass
        self.result_ready.emit(all_statuses)


class _DepRowWidget(QFrame):
    """A single dependency row showing package name, status, version, and action."""

    install_requested = Signal(str, str, str)  # package_name, venv_name, status
    upgrade_requested = Signal(str, str)  # package_name, venv_name

    def __init__(self, status: DependencyStatus, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._status = status
        self.setProperty("cssClass", "depRow")
        self.setFixedHeight(44)

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        # Status dot
        status_map = {"installed": "ready", "missing": "missing", "broken": "failed"}
        dot = QLabel("●")
        mark_status_dot(dot, status_map.get(status.status, "missing"))
        layout.addWidget(dot)

        # Package name
        name_label = QLabel(status.package_name)
        name_label.setMinimumWidth(120)
        mark_item_title(name_label)
        layout.addWidget(name_label)

        # Status text
        status_text_map = {
            "installed": "已安装",
            "missing": "未安装",
            "broken": "已损坏",
        }
        status_color_map = {
            "installed": "success",
            "missing": "danger",
            "broken": "warning",
        }
        status_label = QLabel(status_text_map.get(status.status, status.status))
        status_label.setStyleSheet(
            f"color: {active_color(status_color_map.get(status.status, 'text_secondary'))};"
        )
        status_label.setFixedWidth(56)
        layout.addWidget(status_label)

        # Version
        version_text = status.version if status.version else "—"
        ver_label = QLabel(version_text)
        mark_sub_text(ver_label)
        ver_label.setMinimumWidth(80)
        layout.addWidget(ver_label)

        layout.addStretch()

        # Venv hint for pyannote
        if status.venv_name != ".venv":
            venv_hint = QLabel(f"({status.venv_name})")
            mark_sub_text(venv_hint)
            layout.addWidget(venv_hint)

        # Action button
        action = status.action_label
        if action:
            btn = QPushButton(action)
            btn.setMinimumSize(72, 30)
            if action == "升级":
                mark_link_button(btn)
                btn.clicked.connect(
                    lambda _checked=False, s=status: self.upgrade_requested.emit(
                        s.package_name, s.venv_name
                    )
                )
            else:
                mark_primary_button(btn)
                btn.clicked.connect(
                    lambda _checked=False, s=status: self.install_requested.emit(
                        s.package_name, s.venv_name, s.status
                    )
                )
            layout.addWidget(btn)

        self.setLayout(layout)

    def update_status(self, status: DependencyStatus) -> None:
        """Refresh the row with new status data."""
        self._status = status
        # Rebuild the widget
        pass


class _ProviderItemWidget(QFrame):
    """A single provider config item in the stage card list."""

    edit_requested = Signal(str)  # config_id
    delete_requested = Signal(str)  # config_id

    def __init__(self, config: StageProviderConfig, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config_id = config.id
        self.setFixedHeight(56)
        self.setStyleSheet("")
        mark_provider_item(self)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(12)

        # Status dot
        status_dot = QLabel("●")
        mark_status_dot(status_dot, config.last_validation_status)
        status_dot.setToolTip(
            _STATUS_LABELS.get(config.last_validation_status, config.last_validation_message)
        )
        layout.addWidget(status_dot)

        # Main text
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        main_label = QLabel(config.display_name)
        main_label.setMinimumWidth(1)
        mark_item_title(main_label)
        text_layout.addWidget(main_label)

        sub_label = QLabel(f"{config.provider_key} - {config.model_name or config.protocol}")
        mark_sub_text(sub_label)
        text_layout.addWidget(sub_label)

        layout.addLayout(text_layout, 1)

        # Kind badge
        kind_badge = QLabel("本地" if config.kind == "local" else "云端")
        mark_kind_badge(kind_badge)
        layout.addWidget(kind_badge)

        # Edit button
        edit_btn = QPushButton("编辑")
        edit_btn.setMinimumWidth(56)
        edit_btn.setFixedHeight(30)
        edit_btn.setStyleSheet("")
        mark_compact_button(edit_btn)
        edit_btn.clicked.connect(lambda: self.edit_requested.emit(self.config_id))
        layout.addWidget(edit_btn)

        # Delete button
        delete_btn = QPushButton("删除")
        delete_btn.setMinimumWidth(56)
        delete_btn.setFixedHeight(30)
        delete_btn.setStyleSheet("")
        mark_danger_button(delete_btn)
        delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.config_id))
        layout.addWidget(delete_btn)

        self.setLayout(layout)


class _StageCard(QFrame):
    """A content panel for a single pipeline stage (e.g. ASR, TTS)."""

    provider_added = Signal(str)  # stage
    provider_deleted = Signal(str, str)  # stage, config_id

    def __init__(
        self,
        stage: StageName,
        store: ProviderStore,
        registry: ProviderRegistry,
        secret_store: SecretStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.stage = stage
        self.store = store
        self.registry = registry
        self.secret_store = secret_store
        self.setStyleSheet("")
        mark_stage_panel(self)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(18, 18, 18, 18)
        outer_layout.setSpacing(10)
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Provider list
        self._list_layout = QVBoxLayout()
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        outer_layout.addLayout(self._list_layout)

        # Empty state
        self._empty_label = QLabel("暂未配置供应商，点击上方按钮添加")
        mark_sub_text(self._empty_label)
        self._empty_label.setStyleSheet("padding: 16px;")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        outer_layout.addWidget(self._empty_label)

        self.setLayout(outer_layout)

    def add_provider(self) -> None:
        """Open the add-provider dialog for this stage (public entry point)."""
        self._on_add_provider()

    def refresh(self) -> None:
        """Reload the provider items for this stage."""
        # Clear existing items
        while self._list_layout.count():
            old_item = self._list_layout.takeAt(0)
            if old_item is not None:
                w = old_item.widget()
                if w is not None:
                    w.deleteLater()

        configs = [
            c for c in self.store.load_stage_configs() if c.stage == self.stage
        ]
        self._empty_label.setVisible(len(configs) == 0)

        for config in configs:
            widget = _ProviderItemWidget(config)
            widget.edit_requested.connect(self._on_edit_provider)
            widget.delete_requested.connect(self._on_delete_provider)
            self._list_layout.addWidget(widget)

    def _on_add_provider(self) -> None:
        dialog = ProviderConfigDialog(
            stage=self.stage,
            registry=self.registry,
            parent=self,
        )
        if dialog.exec() == ProviderConfigDialog.DialogCode.Accepted:
            values = dialog.values()
            config_id = str(uuid.uuid4())[:8]
            provider_id = str(values.get("provider_id", ""))
            kind = str(values.get("kind", "api"))
            protocol = self._resolve_protocol(provider_id, kind)
            model_name = self._resolve_model_name(values)

            # --- Save API key to SecretStore and create account ---
            account_id: str | None = None
            if kind == "api" and provider_id != "local":
                account_id = config_id
                api_key_value = dialog.api_key()

                # Save API key to encrypted store
                secret_id = f"api-key-{account_id}"
                if self.secret_store and api_key_value:
                    self.secret_store.save(secret_id, api_key_value)

                # Filter sensitive keys from auth_fields
                safe_auth = {
                    k: str(v) for k, v in values.items()
                    if k not in ("display_name", "stage", "provider_id", "kind")
                    and k.lower() not in _SENSITIVE_KEYS
                }

                account = ProviderAccount(
                    id=account_id,
                    display_name=str(values.get("display_name", "")) or "未命名",
                    provider_key=provider_id,
                    kind="api",
                    api_base_url=str(values.get("base_url", "")),
                    api_key_ref=secret_id if api_key_value else None,
                    auth_fields=safe_auth,
                )
                self.store.save_account(account)

            # Collect non-standard fields into extra
            extra: dict[str, object] = {
                k: v for k, v in values.items()
                if k not in _EXTRA_EXCLUDE_KEYS
            }

            config = StageProviderConfig(
                id=config_id,
                display_name=str(values.get("display_name", "")) or "未命名",
                account_id=account_id,
                provider_key=provider_id,
                kind=kind,  # type: ignore[arg-type]
                stage=self.stage,
                protocol=protocol,
                model_name=model_name,
                local_model_path=str(values.get("local_model_path", "")),
                device=str(values.get("device", "auto")),
                precision=str(values.get("precision", "auto")),
                upload_media_to_cloud=(kind == "api"),
                extra=extra,
            )
            self.store.save_stage_config(config)

            self.refresh()
            self.provider_added.emit(self.stage)

    def _on_edit_provider(self, config_id: str) -> None:
        config = self.store.get_stage_config(config_id)
        if config is None:
            return
        existing = {
            "display_name": config.display_name,
            "local_model_path": config.local_model_path,
            "device": config.device,
            "model_name": config.model_name,
            "provider_id": config.provider_key,
        }
        existing.update({k: str(v) for k, v in config.extra.items()})

        dialog = ProviderConfigDialog(
            stage=self.stage,
            registry=self.registry,
            existing_values=existing,
            parent=self,
        )
        if dialog.exec() == ProviderConfigDialog.DialogCode.Accepted:
            values = dialog.values()
            updated_extra: dict[str, object] = {
                k: v for k, v in values.items()
                if k not in _EXTRA_EXCLUDE_KEYS
            }
            updated = config.model_copy(
                update={
                    "display_name": values.get("display_name", config.display_name),
                    "model_name": self._resolve_model_name(values) or config.model_name,
                    "local_model_path": values.get("local_model_path", config.local_model_path),
                    "device": values.get("device", config.device),
                    "precision": values.get("precision", config.precision),
                    "extra": updated_extra,
                }
            )
            self.store.save_stage_config(updated)
            self.refresh()

    def _on_delete_provider(self, config_id: str) -> None:
        result = QMessageBox.question(
            self,
            "确认删除",
            "该配置可能被方案引用，删除后相关方案将失效。是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self.store.delete_stage_config(config_id)
            self.store.delete_account(config_id)
            # Also remove the secret
            if self.secret_store:
                self.secret_store.delete(f"api-key-{config_id}")
            self.refresh()
            self.provider_deleted.emit(self.stage, config_id)

    def _resolve_protocol(self, provider_id: str, kind: str) -> str:
        entry = self.registry.get(provider_id)
        if entry and entry.protocols:
            keywords = _STAGE_PROTOCOL_KEYWORDS.get(self.stage, (self.stage,))
            for proto in entry.protocols:
                proto_lower = proto.lower()
                if any(kw in proto_lower for kw in keywords):
                    return proto
            return entry.protocols[0]
        # Fallback for unknown providers
        if kind == "local":
            return f"local_{self.stage}"
        return f"{provider_id}_{self.stage}"

    def _resolve_model_name(self, values: dict[str, object]) -> str:
        # Try common model field names
        for key in (
            "translation_model",
            "diarization_model",
            "asr_model",
            "tts_model",
            "model",
            "model_name",
        ):
            if key in values and values[key]:
                return str(values[key])
        return ""


class ModelServicesPage(QWidget):
    """Page for managing model service providers across 5 pipeline stages."""

    provider_config_changed = Signal(str, object)  # stage, config

    def __init__(
        self,
        *,
        store: ProviderStore | None = None,
        registry: ProviderRegistry | None = None,
        secret_store: SecretStore | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._registry = registry or ProviderRegistry()
        config_dir = default_config_dir()
        self._store = store or ProviderStore(config_dir)
        self._secret_store = secret_store or SecretStore(config_dir)
        self._stage_cards: dict[StageName, _StageCard] = {}
        self._nav_buttons: dict[StageName, QPushButton] = {}
        self._current_stage: StageName = STAGE_NAMES[0]

        # Load pip mirror setting
        settings_store = UserSettingsStore(
            default_user_settings_path(), runtime_root=config_dir
        )
        settings = settings_store.load()
        self._pip_mirror = PYPI_MIRRORS.get(settings.pip_mirror, ("", ""))[1]

        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 16, 20, 12)
        main_layout.setSpacing(0)

        # Title
        title = QLabel("模型服务")
        title.setObjectName("PageTitle")
        main_layout.addWidget(title)

        # Tab widget
        tabs = QTabWidget()

        # ── Tab 1: Provider configuration ──
        provider_tab = QWidget()
        provider_layout = QHBoxLayout(provider_tab)
        provider_layout.setContentsMargins(8, 8, 8, 8)
        provider_layout.setSpacing(16)

        # Left stage navigation
        nav_frame = QFrame()
        nav_frame.setFixedWidth(180)
        nav_frame.setStyleSheet("")
        nav_layout = QVBoxLayout()
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(4)

        for stage in STAGE_NAMES:
            icon = _STAGE_ICONS.get(stage, "📦")
            label = STAGE_LABELS.get(stage, stage)
            btn = QPushButton(f"{icon}  {label}")
            btn.setCheckable(True)
            btn.setStyleSheet("")
            mark_stage_list_item(btn)
            btn.clicked.connect(lambda _checked=False, s=stage: self._select_stage(s))
            nav_layout.addWidget(btn)
            self._nav_buttons[stage] = btn

        nav_layout.addStretch()
        nav_frame.setLayout(nav_layout)
        provider_layout.addWidget(nav_frame)

        # Right panel (stage cards)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        self._stage_title_label = QLabel("")
        mark_heading3(self._stage_title_label)
        header_layout.addWidget(self._stage_title_label)
        header_layout.addStretch()

        self._add_button = QPushButton("+ 添加供应商")
        self._add_button.setStyleSheet("")
        mark_primary_button(self._add_button)
        self._add_button.setFixedHeight(32)
        self._add_button.clicked.connect(self._on_header_add)
        header_layout.addWidget(self._add_button)
        right_layout.addLayout(header_layout)

        for stage in STAGE_NAMES:
            card = _StageCard(stage, self._store, self._registry, self._secret_store)
            card.provider_added.connect(self._on_provider_added)
            card.provider_deleted.connect(self._on_provider_deleted)
            self._stage_cards[stage] = card
            right_layout.addWidget(card, 1)

        provider_layout.addWidget(right_widget, 1)
        tabs.addTab(provider_tab, "供应商配置")

        # ── Tab 2: Local model dependencies ──
        dep_tab = QWidget()
        dep_outer = QVBoxLayout(dep_tab)
        dep_outer.setContentsMargins(18, 14, 18, 14)
        dep_outer.setSpacing(10)

        # Header row: title + buttons
        dep_header = QHBoxLayout()
        dep_title = QLabel("本地模型依赖")
        mark_heading3(dep_title)
        dep_header.addWidget(dep_title)
        dep_header.addStretch()

        self._refresh_btn = QPushButton("刷新状态")
        self._refresh_btn.setStyleSheet("")
        mark_compact_button(self._refresh_btn)
        self._refresh_btn.setFixedHeight(28)
        self._refresh_btn.clicked.connect(self._refresh_dep_status)
        dep_header.addWidget(self._refresh_btn)

        self._install_all_btn = QPushButton("一键安装缺失")
        self._install_all_btn.setStyleSheet("")
        mark_primary_button(self._install_all_btn)
        self._install_all_btn.clicked.connect(self._install_all_missing)
        dep_header.addWidget(self._install_all_btn)

        dep_outer.addLayout(dep_header)

        # Scrollable dependency content (full height)
        dep_scroll = QScrollArea()
        dep_scroll.setWidgetResizable(True)
        dep_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        dep_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._dep_content = QWidget()
        self._dep_layout = QVBoxLayout()
        self._dep_layout.setContentsMargins(0, 0, 0, 0)
        self._dep_layout.setSpacing(12)
        self._dep_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._dep_content.setLayout(self._dep_layout)

        dep_scroll.setWidget(self._dep_content)
        dep_outer.addWidget(dep_scroll, 1)

        # Footer hint
        self._hint_label = QLabel(
            "pyannote.audio 安装到独立 .venv-pyannote 环境，其余安装到主环境。"
            "模型权重需另行下载。"
        )
        self._hint_label.setProperty("cssClass", "statusDanger")
        self._hint_label.setWordWrap(True)
        dep_outer.addWidget(self._hint_label)

        tabs.addTab(dep_tab, "本地模型依赖")

        main_layout.addWidget(tabs, 1)
        self.setLayout(main_layout)

        # Track install workers
        self._install_workers: list[_PipInstallWorker] = []
        self._active_install_package = ""
        self._install_in_progress = False
        self._dep_worker: _DepStatusLoadWorker | None = None

        # Track async upgrade check workers to avoid duplicate refreshes
        self._upgrade_check_pending = 0
        self._upgrade_results: dict[str, str] = {}

        # Loading animation state
        self._loading_timer = QTimer(self)
        self._loading_timer.setInterval(150)
        self._loading_timer.timeout.connect(self._animate_loading)
        self._loading_dots = 0

        # Select first stage by default
        self._select_stage(STAGE_NAMES[0])

        # Auto-refresh dependency status on first show
        self._dep_loaded = False

    def _select_stage(self, stage: StageName) -> None:
        """Switch the right panel to show the given stage."""
        self._current_stage = stage

        # Update nav button checked states
        for s, btn in self._nav_buttons.items():
            btn.setChecked(s == stage)

        # Update header title
        icon = _STAGE_ICONS.get(stage, "📦")
        label = STAGE_LABELS.get(stage, stage)
        self._stage_title_label.setText(f"{icon}  {label}")

        # Show only the selected stage card
        for s, card in self._stage_cards.items():
            card.setVisible(s == stage)

    def _on_header_add(self) -> None:
        """Handle the add-provider button in the header."""
        card = self._stage_cards.get(self._current_stage)
        if card:
            card.add_provider()

    # ── Dependency management ──────────────────────────────────────────────

    def showEvent(self, event: QShowEvent) -> None:
        super().showEvent(event)
        if not self._dep_loaded:
            self._dep_loaded = True
            self._refresh_dep_status()

    def _refresh_dep_status(
        self, upgrade_results: dict[str, str] | None = None
    ) -> None:
        """Reload dependency status in background, then rebuild UI.

        When upgrade_results is provided, uses cached data to avoid
        redundant subprocess calls.
        """
        if upgrade_results is not None and hasattr(self, "_last_statuses"):
            self._build_dep_ui(self._last_statuses, upgrade_results)
            return

        # Prevent duplicate worker if one is already running
        if hasattr(self, "_dep_worker") and self._dep_worker is not None and self._dep_worker.isRunning():
            return

        self._refresh_btn.setEnabled(False)
        self._loading_dots = 0
        self._loading_timer.start()

        # Show loading placeholder in dep content
        self._show_loading_placeholder()

        self._dep_worker = _DepStatusLoadWorker(parent=self)
        self._dep_worker.result_ready.connect(self._on_dep_status_loaded)
        self._dep_worker.start()

    def _animate_loading(self) -> None:
        """Animate the loading dots on the refresh button."""
        self._loading_dots = (self._loading_dots + 1) % 4
        dots = "." * self._loading_dots
        self._refresh_btn.setText(f"加载中{dots}")

    def _show_loading_placeholder(self) -> None:
        """Show a centered loading indicator in the dep content area."""
        # Clear existing content
        while self._dep_layout.count():
            item = self._dep_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        loading_label = QLabel("正在检测依赖状态...")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        mark_sub_text(loading_label)
        loading_label.setStyleSheet(f"color: {active_color('text_secondary')}; padding: 40px;")
        self._dep_layout.addWidget(loading_label)

    def _on_dep_status_loaded(self, statuses: list[DependencyStatus]) -> None:
        """Handle loaded dependency statuses from background worker."""
        self._loading_timer.stop()
        self._build_dep_ui(statuses, None)

    def _build_dep_ui(
        self,
        all_statuses: list[DependencyStatus],
        upgrade_results: dict[str, str] | None = None,
    ) -> None:
        """Build dependency panel UI from already-loaded data (no subprocess)."""
        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText("刷新状态")

        # Cache for incremental upgrade-result rebuilds
        self._last_statuses = all_statuses

        # Clear existing content
        while self._dep_layout.count():
            item = self._dep_layout.takeAt(0)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.deleteLater()

        # Inject upgrade results into statuses
        if upgrade_results:
            for status in all_statuses:
                if status.package_name in upgrade_results:
                    status.latest_version = upgrade_results[status.package_name]

        # Group services by stage and collect statuses per service
        from ivo.model_services.local_models import LocalModelService

        stage_services: dict[str, list[LocalModelService]] = {}
        for svc in ALL_LOCAL_MODEL_SERVICES:
            stage_services.setdefault(svc.stage, []).append(svc)

        # Flatten statuses per service for look-up
        svc_status_map: dict[str, list[DependencyStatus]] = {}
        for svc in ALL_LOCAL_MODEL_SERVICES:
            dep_names = {d.package_name for d in svc.dependencies}
            svc_status_map[svc.provider_key] = [
                s for s in all_statuses if s.package_name in dep_names
            ]

        for stage in _LOCAL_STAGES:
            services = stage_services.get(stage, [])
            if not services:
                continue

            group = QFrame()
            group.setProperty("cssClass", "depGroup")
            group_layout = QVBoxLayout()
            group_layout.setContentsMargins(12, 10, 12, 10)
            group_layout.setSpacing(6)

            icon = _STAGE_ICONS.get(stage, "📦")
            stage_label = STAGE_LABELS.get(stage, stage)  # type: ignore[call-overload]
            group_title = QLabel(f"{icon}  {stage_label}")
            mark_heading2(group_title)
            group_layout.addWidget(group_title)

            for svc in services:
                model_label = QLabel(svc.display_name)
                mark_sub_text(model_label)
                model_label.setStyleSheet("padding-left: 18px;")
                group_layout.addWidget(model_label)

            # Deduplicate dependencies by package_name within this stage
            seen: set[str] = set()
            stage_deps: list[DependencyStatus] = []
            for svc in services:
                for dep_status in svc_status_map.get(svc.provider_key, []):
                    if dep_status.package_name not in seen:
                        seen.add(dep_status.package_name)
                        stage_deps.append(dep_status)

            for dep_status in stage_deps:
                if upgrade_results and dep_status.package_name in upgrade_results:
                    dep_status.latest_version = upgrade_results[dep_status.package_name]
                row = _DepRowWidget(dep_status)
                row.install_requested.connect(self._on_install_dep)
                row.upgrade_requested.connect(self._on_upgrade_dep)
                group_layout.addWidget(row)

            group.setLayout(group_layout)
            self._dep_layout.addWidget(group)

        self._dep_layout.addStretch()

        # If an install is in progress, keep all action buttons disabled
        if self._install_in_progress:
            self._refresh_btn.setEnabled(False)
            self._install_all_btn.setEnabled(False)
            self._set_dep_row_buttons_enabled(False)

        # Start async upgrade checks (only if not already checking)
        if self._upgrade_check_pending == 0 and upgrade_results is None:
            checked: set[str] = set()
            for status in all_statuses:
                if (
                    status.status == "installed"
                    and status.version
                    and status.package_name not in checked
                ):
                    checked.add(status.package_name)
                    self._upgrade_check_pending += 1
                    worker = _DepUpgradeCheckWorker(
                        status.package_name,
                        status.version,
                        mirror_url=self._pip_mirror,
                        parent=self,
                    )
                    worker.result_ready.connect(self._on_upgrade_check_ready)
                    worker.start()

    def _guard_install_not_running(self) -> bool:
        """Return False and inform the user if an install task is already running."""
        if not self._install_in_progress:
            return True
        QMessageBox.information(
            self,
            "提示",
            "已有依赖安装任务正在进行，请等待完成后再操作。",
        )
        return False

    def _on_install_dep(
        self, package_name: str, venv_name: str, status: str = "missing"
    ) -> None:
        """Install a missing or broken dependency."""
        if not self._guard_install_not_running():
            return
        venv_python = self._resolve_venv_python(venv_name)
        if venv_python is None:
            QMessageBox.warning(
                self, "安装失败", f"找不到 {venv_name} 环境，请先运行 setup-local-env.ps1"
            )
            return
        force_reinstall = status == "broken"
        self._run_pip_install(
            package_name, venv_python, upgrade=False, force_reinstall=force_reinstall
        )

    def _on_upgrade_dep(self, package_name: str, venv_name: str) -> None:
        """Upgrade an installed dependency."""
        if not self._guard_install_not_running():
            return
        venv_python = self._resolve_venv_python(venv_name)
        if venv_python is None:
            QMessageBox.warning(self, "升级失败", f"找不到 {venv_name} 环境")
            return
        self._run_pip_install(package_name, venv_python, upgrade=True)

    def _on_upgrade_check_ready(
        self, package_name: str, current_version: str, latest_version: str
    ) -> None:
        """Store upgrade check result; refresh UI once when all checks complete."""
        self._upgrade_check_pending -= 1
        if latest_version and latest_version != current_version:
            self._upgrade_results[package_name] = latest_version
        if self._upgrade_check_pending <= 0:
            self._upgrade_check_pending = 0
            if self._upgrade_results:
                self._refresh_dep_status(upgrade_results=dict(self._upgrade_results))
                self._upgrade_results.clear()

    def _install_all_missing(self) -> None:
        """Install all missing/broken dependencies sequentially."""
        if not self._guard_install_not_running():
            return
        if not hasattr(self, "_last_statuses"):
            QMessageBox.information(self, "提示", "依赖状态还在检测中，请稍后再试。")
            return

        missing: list[tuple[str, Path, str]] = []
        unresolved: list[tuple[str, str]] = []
        seen: set[str] = set()
        for dep_status in self._last_statuses:
            if dep_status.status in ("missing", "broken") and dep_status.package_name not in seen:
                seen.add(dep_status.package_name)
                venv_python = self._resolve_venv_python(dep_status.venv_name)
                if venv_python is not None:
                    missing.append((dep_status.package_name, venv_python, dep_status.status))
                else:
                    unresolved.append((dep_status.package_name, dep_status.venv_name))

        if unresolved:
            detail = "\n".join(f"{pkg}: {venv}" for pkg, venv in unresolved)
            QMessageBox.warning(
                self,
                "安装失败",
                f"以下依赖找不到目标 Python 环境，请先创建环境后重试：\n{detail}",
            )
            return

        if not missing:
            QMessageBox.information(self, "提示", "所有依赖已安装，无需操作。")
            return

        # Install first one; on completion, install next
        self._missing_queue: list[tuple[str, Path, str]] = missing[1:]
        pkg, python, dep_st = missing[0]
        self._run_pip_install(pkg, python, upgrade=False, force_reinstall=dep_st == "broken")

    def _run_pip_install(
        self,
        package_name: str,
        venv_python: Path,
        upgrade: bool,
        force_reinstall: bool = False,
    ) -> None:
        """Run pip install in a background thread."""
        self._install_in_progress = True
        self._refresh_btn.setEnabled(False)
        self._install_all_btn.setEnabled(False)
        self._set_dep_row_buttons_enabled(False)

        action = "升级" if upgrade else ("修复" if force_reinstall else "安装")
        self._active_install_package = package_name
        self._hint_label.setProperty("cssClass", "statusWarning")
        self._hint_label.setText(f"正在{action} {package_name}，请勿关闭程序...")
        self._hint_label.style().unpolish(self._hint_label)
        self._hint_label.style().polish(self._hint_label)

        worker = _PipInstallWorker(
            package_name, venv_python, upgrade,
            force_reinstall=force_reinstall,
            mirror_url=self._pip_mirror,
            parent=self,
        )
        worker.finished.connect(self._on_install_finished)
        self._install_workers.append(worker)
        worker.start()

    def _on_install_finished(self, package_name: str, success: bool, output: str) -> None:
        """Handle pip install completion."""
        if success:
            self._hint_label.setProperty("cssClass", "statusSuccess")
            self._hint_label.setText(f"{package_name} 处理完成，正在刷新依赖状态...")
            self._hint_label.style().unpolish(self._hint_label)
            self._hint_label.style().polish(self._hint_label)

            # Continue installing remaining missing packages without releasing the lock
            if hasattr(self, "_missing_queue") and self._missing_queue:
                pkg, python, dep_st = self._missing_queue.pop(0)
                self._run_pip_install(
                    pkg, python, upgrade=False, force_reinstall=dep_st == "broken"
                )
                return

            # All done — release lock and restore buttons
            self._install_in_progress = False
            self._refresh_btn.setEnabled(True)
            self._install_all_btn.setEnabled(True)
            self._set_dep_row_buttons_enabled(True)
            self._refresh_dep_status()
            return

        # Failed — release lock and restore buttons
        self._install_in_progress = False
        self._missing_queue = []
        self._refresh_btn.setEnabled(True)
        self._install_all_btn.setEnabled(True)
        self._set_dep_row_buttons_enabled(True)
        self._hint_label.setProperty("cssClass", "statusDanger")
        self._hint_label.setText(f"{package_name} 安装失败，请查看弹窗错误信息。")
        self._hint_label.style().unpolish(self._hint_label)
        self._hint_label.style().polish(self._hint_label)
        QMessageBox.warning(
            self, "安装失败",
            f"安装 {package_name} 失败：\n{output[:500]}",
        )

    @staticmethod
    def _resolve_venv_python(venv_name: str) -> Path | None:
        """Resolve the Python executable for a given venv name."""
        import sys as _sys

        if venv_name == ".venv":
            return Path(_sys.executable).resolve()

        # For .venv-pyannote, search project root
        exe_dir = Path(_sys.executable).resolve().parent
        candidates = [exe_dir]
        if (exe_dir.parent / "pyvenv.cfg").is_file():
            candidates.append(exe_dir.parent.parent)

        for base in candidates:
            python = base / venv_name / "Scripts" / "python.exe"
            if python.is_file():
                return python
        return None

    def _set_dep_row_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable all action buttons inside dependency row widgets."""
        from PySide6.QtWidgets import QPushButton

        for i in range(self._dep_layout.count()):
            item = self._dep_layout.itemAt(i)
            if item is None:
                continue
            w = item.widget()
            if w is not None:
                for btn in w.findChildren(QPushButton):
                    btn.setEnabled(enabled)

    def _on_provider_added(self, stage: str) -> None:
        configs = [
            c for c in self._store.load_stage_configs() if c.stage == stage
        ]
        if configs:
            self.provider_config_changed.emit(stage, configs[-1])

    def _on_provider_deleted(self, stage: str, config_id: str) -> None:
        self.provider_config_changed.emit(stage, None)

    def stage_cards(self) -> dict[StageName, _StageCard]:
        """Return the stage card dict for testing."""
        return dict(self._stage_cards)

    def refresh_all(self) -> None:
        """Refresh all stage cards."""
        for card in self._stage_cards.values():
            card.refresh()

    def scroll_to_stage(self, stage: StageName) -> None:
        """Select a specific stage in the left nav."""
        self._select_stage(stage)
