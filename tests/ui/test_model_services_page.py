"""Tests for ModelServicesPage."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication

from ivo.model_services.provider_config import StageProviderConfig
from ivo.model_services.provider_registry import ProviderRegistry
from ivo.model_services.provider_store import ProviderStore
from ivo.model_services.stages import STAGE_NAMES
from ivo.ui.model_services_page import ModelServicesPage, _StageCard


@pytest.fixture
def qt_app(qapp: QApplication) -> QApplication:
    return qapp


@pytest.fixture
def tmp_store(tmp_path: Path) -> ProviderStore:
    return ProviderStore(tmp_path / ".ivo-config")


@pytest.fixture
def registry() -> ProviderRegistry:
    return ProviderRegistry()


@pytest.fixture
def page(qt_app: QApplication, tmp_store: ProviderStore, registry: ProviderRegistry) -> ModelServicesPage:
    return ModelServicesPage(store=tmp_store, registry=registry)


class TestModelServicesPageInit:
    def test_page_title(self, page: ModelServicesPage) -> None:
        from PySide6.QtWidgets import QLabel
        title = page.findChild(QLabel, "PageTitle")
        assert title is not None
        assert title.text() == "模型服务"

    def test_page_has_five_stage_cards(self, page: ModelServicesPage) -> None:
        cards = page.stage_cards()
        assert len(cards) == len(STAGE_NAMES)
        for stage in STAGE_NAMES:
            assert stage in cards

    def test_page_has_local_model_section(self, page: ModelServicesPage) -> None:
        assert page._refresh_btn is not None
        assert page._install_all_btn is not None

    def test_page_has_nav_buttons(self, page: ModelServicesPage) -> None:
        """Page has 5 stage navigation buttons in the left nav."""
        from ivo.model_services.stages import STAGE_LABELS
        assert len(page._nav_buttons) == len(STAGE_NAMES)
        for stage in STAGE_NAMES:
            btn = page._nav_buttons[stage]
            label = STAGE_LABELS.get(stage, stage)
            assert label in btn.text()


class TestStageCard:
    def test_stage_card_has_list_layout(
        self, qt_app: QApplication, tmp_store: ProviderStore, registry: ProviderRegistry
    ) -> None:
        """_StageCard has a provider list layout (no longer has its own title)."""
        card = _StageCard("asr", tmp_store, registry)
        assert card._list_layout is not None
        assert card._empty_label is not None

    def test_stage_card_empty_state(
        self, qt_app: QApplication, tmp_store: ProviderStore, registry: ProviderRegistry
    ) -> None:
        card = _StageCard("tts", tmp_store, registry)
        assert not card._empty_label.isHidden()

    def test_stage_card_shows_configured_providers(
        self, qt_app: QApplication, tmp_store: ProviderStore, registry: ProviderRegistry
    ) -> None:
        config = StageProviderConfig(
            id="test-1",
            display_name="OpenAI Test",
            provider_key="openai",
            kind="api",
            stage="asr",
            protocol="openai_asr",
            model_name="gpt-4o-transcribe",
            last_validation_status="ready",
        )
        tmp_store.save_stage_config(config)
        card = _StageCard("asr", tmp_store, registry)
        assert card._empty_label.isHidden()

    def test_page_has_add_button_in_header(
        self, qt_app: QApplication, tmp_store: ProviderStore, registry: ProviderRegistry
    ) -> None:
        """Add button is now in the page header, not inside _StageCard."""
        page = ModelServicesPage(store=tmp_store, registry=registry)
        assert page._add_button is not None
        assert page._add_button.text() == "+ 添加供应商"


class TestModelServicesPageRefresh:
    def test_refresh_all_reloads_cards(
        self,
        qt_app: QApplication,
        tmp_store: ProviderStore,
        registry: ProviderRegistry,
    ) -> None:
        page = ModelServicesPage(store=tmp_store, registry=registry)

        # Add a config
        config = StageProviderConfig(
            id="refresh-test",
            display_name="Refresh Test",
            provider_key="openai",
            kind="api",
            stage="translation",
            protocol="openai_compatible_translation",
            last_validation_status="ready",
        )
        tmp_store.save_stage_config(config)
        page.refresh_all()

        # Verify the card was refreshed
        card = page.stage_cards()["translation"]
        assert card._empty_label.isHidden()


class TestModelServicesPageLocalModels:
    def test_dep_panel_has_buttons(self, page: ModelServicesPage) -> None:
        assert page._refresh_btn.text() == "刷新状态"
        assert page._install_all_btn.text() == "一键安装缺失"

    def test_refresh_dep_status_populates_panel(
        self,
        qt_app: QApplication,
        tmp_path: Path,
        registry: ProviderRegistry,
    ) -> None:
        store = ProviderStore(tmp_path / ".ivo-config")
        page = ModelServicesPage(store=store, registry=registry)
        loaded: list[bool] = [False]

        def _on_loaded() -> None:
            loaded[0] = True

        page._refresh_dep_status()
        if page._dep_worker is not None:
            page._dep_worker.result_ready.connect(lambda _s: _on_loaded())
            page._dep_worker.finished.connect(_on_loaded)
        # Wait for async worker (max 30 seconds for subprocess-heavy load)
        for _ in range(300):
            qt_app.processEvents()
            if loaded[0]:
                break
            QThread.msleep(100)
        assert page._dep_layout.count() > 0


class TestProviderItemWidget:
    def test_provider_item_shows_status(
        self, qt_app: QApplication, tmp_store: ProviderStore, registry: ProviderRegistry
    ) -> None:
        from ivo.ui.model_services_page import _ProviderItemWidget

        config = StageProviderConfig(
            id="item-test",
            display_name="Item Test",
            provider_key="openai",
            kind="api",
            stage="asr",
            protocol="openai_asr",
            model_name="whisper-1",
            last_validation_status="ready",
        )
        item = _ProviderItemWidget(config)
        assert item.config_id == "item-test"

    def test_provider_item_has_edit_delete_buttons(
        self, qt_app: QApplication
    ) -> None:
        from PySide6.QtWidgets import QPushButton
        from ivo.ui.model_services_page import _ProviderItemWidget

        config = StageProviderConfig(
            id="btn-test",
            display_name="Button Test",
            provider_key="deepgram",
            kind="api",
            stage="asr",
            protocol="deepgram_asr",
        )
        item = _ProviderItemWidget(config)
        buttons = item.findChildren(QPushButton)
        texts = [btn.text() for btn in buttons]
        assert "编辑" in texts
        assert "删除" in texts

    def test_provider_item_shows_kind_badge(
        self, qt_app: QApplication
    ) -> None:
        from PySide6.QtWidgets import QLabel
        from ivo.ui.model_services_page import _ProviderItemWidget

        config = StageProviderConfig(
            id="badge-test",
            display_name="Badge Test",
            provider_key="f5-tts",
            kind="local",
            stage="tts",
            protocol="local_f5_tts",
        )
        item = _ProviderItemWidget(config)
        labels = item.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert "本地" in texts


class TestModelServicesPageNavigation:
    def test_default_stage_selected(
        self, qt_app: QApplication, tmp_store: ProviderStore, registry: ProviderRegistry
    ) -> None:
        """First stage (separation) should be selected by default."""
        page = ModelServicesPage(store=tmp_store, registry=registry)
        # Default: separation
        assert page._current_stage == "separation"
        # Only the first stage card should be shown (not hidden)
        for stage in STAGE_NAMES:
            card = page._stage_cards[stage]
            if stage == "separation":
                assert not card.isHidden()
            else:
                assert card.isHidden()
        # Nav button for separation should be checked
        assert page._nav_buttons["separation"].isChecked()

    def test_select_stage_switches_visibility(
        self, qt_app: QApplication, tmp_store: ProviderStore, registry: ProviderRegistry
    ) -> None:
        """Clicking a nav button switches the visible stage card and header title."""
        page = ModelServicesPage(store=tmp_store, registry=registry)

        # Select ASR
        page._select_stage("asr")
        assert page._current_stage == "asr"
        assert "语音识别" in page._stage_title_label.text()
        assert not page._stage_cards["asr"].isHidden()
        assert page._stage_cards["separation"].isHidden()

        # Select TTS
        page._select_stage("tts")
        assert page._current_stage == "tts"
        assert "语音合成" in page._stage_title_label.text()
        assert not page._stage_cards["tts"].isHidden()
        assert page._stage_cards["asr"].isHidden()

    def test_nav_button_exclusive_checked(
        self, qt_app: QApplication, tmp_store: ProviderStore, registry: ProviderRegistry
    ) -> None:
        """Only one nav button should be checked at a time."""
        page = ModelServicesPage(store=tmp_store, registry=registry)

        for stage in STAGE_NAMES:
            page._select_stage(stage)
            # Only the current stage button should be checked
            for s, btn in page._nav_buttons.items():
                if s == stage:
                    assert btn.isChecked(), f"Button for {s} should be checked"
                else:
                    assert not btn.isChecked(), f"Button for {s} should not be checked"


# ── Task 1: Install/Repair button signal fix ───────────────────────────


class TestDepRowButtons:
    def test_dep_row_install_button_emits_install_request(
        self, qt_app: QApplication
    ) -> None:
        from PySide6.QtWidgets import QPushButton
        from ivo.model_services.local_models import DependencyStatus
        from ivo.ui.model_services_page import _DepRowWidget

        row = _DepRowWidget(
            DependencyStatus(
                package_name="demucs",
                import_name="demucs",
                status="missing",
                venv_name=".venv",
            )
        )
        emitted: list[tuple[str, str, str]] = []
        row.install_requested.connect(
            lambda package, venv, status: emitted.append((package, venv, status))
        )

        buttons = row.findChildren(QPushButton)
        install_button = next(button for button in buttons if button.text() == "安装")
        install_button.click()
        qt_app.processEvents()

        assert emitted == [("demucs", ".venv", "missing")]

    def test_dep_row_repair_button_emits_install_request_with_broken_status(
        self, qt_app: QApplication,
    ) -> None:
        from PySide6.QtWidgets import QPushButton
        from ivo.model_services.local_models import DependencyStatus
        from ivo.ui.model_services_page import _DepRowWidget

        row = _DepRowWidget(
            DependencyStatus(
                package_name="soundfile",
                import_name="soundfile",
                status="broken",
                version="0.13.1",
                venv_name=".venv",
            )
        )
        emitted: list[tuple[str, str, str]] = []
        row.install_requested.connect(
            lambda package, venv, status: emitted.append((package, venv, status))
        )

        buttons = row.findChildren(QPushButton)
        repair_button = next(button for button in buttons if button.text() == "修复")
        repair_button.click()
        qt_app.processEvents()

        assert emitted == [("soundfile", ".venv", "broken")]

    def test_dep_row_upgrade_button_emits_upgrade_request(
        self, qt_app: QApplication,
    ) -> None:
        from PySide6.QtWidgets import QPushButton
        from ivo.model_services.local_models import DependencyStatus
        from ivo.ui.model_services_page import _DepRowWidget

        row = _DepRowWidget(
            DependencyStatus(
                package_name="torch",
                import_name="torch",
                status="installed",
                version="2.1.0",
                latest_version="2.2.0",
                venv_name=".venv",
            )
        )
        emitted: list[tuple[str, str]] = []
        row.upgrade_requested.connect(
            lambda package, venv: emitted.append((package, venv))
        )

        buttons = row.findChildren(QPushButton)
        upgrade_button = next(button for button in buttons if button.text() == "升级")
        upgrade_button.click()
        qt_app.processEvents()

        assert emitted == [("torch", ".venv")]


# ── Task 3: Page-level install/upgrade dispatch ────────────────────────


class TestPageInstallDispatch:
    def test_on_install_dep_runs_pip_install_for_missing(
        self, page: ModelServicesPage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        python = Path("C:/fake/.venv/Scripts/python.exe")
        calls: list[tuple[str, Path, bool, bool]] = []

        monkeypatch.setattr(page, "_resolve_venv_python", lambda _venv: python)
        monkeypatch.setattr(
            page,
            "_run_pip_install",
            lambda package, venv_python, upgrade, force_reinstall=False: calls.append(
                (package, venv_python, upgrade, force_reinstall)
            ),
        )

        page._on_install_dep("demucs", ".venv", "missing")

        assert calls == [("demucs", python, False, False)]

    def test_on_install_dep_runs_force_reinstall_for_broken(
        self, page: ModelServicesPage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        python = Path("C:/fake/.venv/Scripts/python.exe")
        calls: list[tuple[str, Path, bool, bool]] = []

        monkeypatch.setattr(page, "_resolve_venv_python", lambda _venv: python)
        monkeypatch.setattr(
            page,
            "_run_pip_install",
            lambda package, venv_python, upgrade, force_reinstall=False: calls.append(
                (package, venv_python, upgrade, force_reinstall)
            ),
        )

        page._on_install_dep("soundfile", ".venv", "broken")

        assert calls == [("soundfile", python, False, True)]

    def test_on_upgrade_dep_runs_pip_install_with_upgrade(
        self, page: ModelServicesPage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        python = Path("C:/fake/.venv/Scripts/python.exe")
        calls: list[tuple[str, Path, bool, bool]] = []

        monkeypatch.setattr(page, "_resolve_venv_python", lambda _venv: python)
        monkeypatch.setattr(
            page,
            "_run_pip_install",
            lambda package, venv_python, upgrade, force_reinstall=False: calls.append(
                (package, venv_python, upgrade, force_reinstall)
            ),
        )

        page._on_upgrade_dep("torch", ".venv")

        assert calls == [("torch", python, True, False)]


# ── Task 4: PipInstallWorker command construction ──────────────────────


class TestPipInstallWorkerCommands:
    def test_pip_install_worker_builds_repair_command_without_no_deps(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from ivo.ui.model_services_page import _PipInstallWorker

        captured: list[list[str]] = []

        class Result:
            returncode = 0
            stdout = "ok"
            stderr = ""

        def fake_run(cmd: list[str], **_kwargs: object) -> Result:
            captured.append(cmd)
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)

        worker = _PipInstallWorker(
            "soundfile",
            Path("C:/fake/.venv/Scripts/python.exe"),
            force_reinstall=True,
        )
        worker.run()

        assert len(captured) == 1
        cmd = captured[0]
        assert cmd[0] == str(Path("C:/fake/.venv/Scripts/python.exe"))
        assert cmd[1:] == ["-m", "pip", "install", "--force-reinstall", "soundfile"]

    def test_pip_install_worker_builds_upgrade_command(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from ivo.ui.model_services_page import _PipInstallWorker

        captured: list[list[str]] = []

        class Result:
            returncode = 0
            stdout = "ok"
            stderr = ""

        def fake_run(cmd: list[str], **_kwargs: object) -> Result:
            captured.append(cmd)
            return Result()

        monkeypatch.setattr("subprocess.run", fake_run)

        worker = _PipInstallWorker(
            "torch",
            Path("C:/fake/.venv/Scripts/python.exe"),
            upgrade=True,
            mirror_url="https://pypi.tuna.tsinghua.edu.cn/simple",
        )
        worker.run()

        assert len(captured) == 1
        cmd = captured[0]
        assert cmd[0] == str(Path("C:/fake/.venv/Scripts/python.exe"))
        assert cmd[1:] == [
            "-m", "pip", "install",
            "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
            "--upgrade",
            "torch",
        ]


# ── Task 5: Install all missing feedback ───────────────────────────────


class TestInstallAllMissing:
    def test_install_all_missing_warns_when_status_not_loaded(
        self, page: ModelServicesPage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        messages: list[tuple[str, str]] = []

        monkeypatch.setattr(
            "ivo.ui.model_services_page.QMessageBox.information",
            lambda _parent, title, text: messages.append((title, text)),
        )

        page._install_all_missing()

        assert messages == [("提示", "依赖状态还在检测中，请稍后再试。")]

    def test_install_all_missing_warns_when_required_venv_missing(
        self, page: ModelServicesPage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ivo.model_services.local_models import DependencyStatus

        page._last_statuses = [
            DependencyStatus(
                package_name="pyannote.audio",
                import_name="pyannote.audio",
                status="missing",
                venv_name=".venv-pyannote",
            )
        ]
        warnings: list[tuple[str, str]] = []

        monkeypatch.setattr(page, "_resolve_venv_python", lambda _venv: None)
        monkeypatch.setattr(
            "ivo.ui.model_services_page.QMessageBox.warning",
            lambda _parent, title, text: warnings.append((title, text)),
        )

        page._install_all_missing()

        assert warnings
        assert warnings[0][0] == "安装失败"
        assert ".venv-pyannote" in warnings[0][1]
        assert "pyannote.audio" in warnings[0][1]

    def test_install_all_missing_starts_first_package_and_queues_rest(
        self, page: ModelServicesPage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ivo.model_services.local_models import DependencyStatus

        python = Path("C:/fake/.venv/Scripts/python.exe")
        page._last_statuses = [
            DependencyStatus("demucs", "demucs", "missing", venv_name=".venv"),
            DependencyStatus(
                "soundfile", "soundfile", "broken", version="0.13.1", venv_name=".venv"
            ),
            DependencyStatus(
                "torch", "torch", "installed", version="2.1.0", venv_name=".venv"
            ),
        ]
        calls: list[tuple[str, Path, bool, bool]] = []

        monkeypatch.setattr(page, "_resolve_venv_python", lambda _venv: python)
        monkeypatch.setattr(
            page,
            "_run_pip_install",
            lambda package, venv_python, upgrade, force_reinstall=False: calls.append(
                (package, venv_python, upgrade, force_reinstall)
            ),
        )

        page._install_all_missing()

        assert calls == [("demucs", python, False, False)]
        assert page._missing_queue == [("soundfile", python, "broken")]


# ── Task 6: UI feedback during install ─────────────────────────────────


class TestRunPipInstallFeedback:
    def test_run_pip_install_updates_hint_and_disables_header_buttons(
        self, page: ModelServicesPage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        started: list[str] = []

        class FakeWorker(QThread):
            finished = QThread.finished  # type: ignore[assignment]

            def __init__(self, package_name: str, *_args: object, **_kwargs: object) -> None:
                super().__init__()
                self.package_name = package_name

            def start(self) -> None:  # type: ignore[override]
                started.append(self.package_name)

        monkeypatch.setattr("ivo.ui.model_services_page._PipInstallWorker", FakeWorker)

        page._run_pip_install(
            "soundfile",
            Path("C:/fake/.venv/Scripts/python.exe"),
            upgrade=False,
            force_reinstall=True,
        )

        assert started == ["soundfile"]
        assert not page._refresh_btn.isEnabled()
        assert not page._install_all_btn.isEnabled()
        assert page._install_in_progress is True
        assert "正在修复 soundfile" in page._hint_label.text()

    def test_install_in_progress_disables_dep_row_buttons(
        self, qt_app: QApplication, tmp_store: ProviderStore, registry: ProviderRegistry,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from PySide6.QtWidgets import QPushButton
        from ivo.model_services.local_models import DependencyStatus
        from ivo.ui.model_services_page import _DepRowWidget

        page = ModelServicesPage(store=tmp_store, registry=registry)

        # Manually add a dep row to the layout
        row = _DepRowWidget(
            DependencyStatus("demucs", "demucs", "missing", venv_name=".venv")
        )
        page._dep_layout.addWidget(row)

        # Simulate install in progress
        page._install_in_progress = True
        page._set_dep_row_buttons_enabled(False)

        for btn in row.findChildren(QPushButton):
            assert not btn.isEnabled()

        # Simulate install finished
        page._install_in_progress = False
        page._set_dep_row_buttons_enabled(True)

        for btn in row.findChildren(QPushButton):
            assert btn.isEnabled()

    def test_on_install_finished_resets_install_in_progress(
        self, page: ModelServicesPage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        page._install_in_progress = True
        page._missing_queue = []
        page._refresh_btn.setEnabled(False)
        page._install_all_btn.setEnabled(False)

        monkeypatch.setattr(page, "_set_dep_row_buttons_enabled", lambda _enabled: None)
        monkeypatch.setattr(page, "_refresh_dep_status", lambda: None)

        page._on_install_finished("demucs", True, "ok")

        assert page._install_in_progress is False
        assert page._refresh_btn.isEnabled()
        assert page._install_all_btn.isEnabled()

    def test_on_install_failure_resets_install_in_progress(
        self, page: ModelServicesPage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        page._install_in_progress = True
        page._refresh_btn.setEnabled(False)
        page._install_all_btn.setEnabled(False)

        monkeypatch.setattr(page, "_set_dep_row_buttons_enabled", lambda _enabled: None)
        monkeypatch.setattr(
            "ivo.ui.model_services_page.QMessageBox.warning",
            lambda *_args: None,
        )

        page._on_install_finished("demucs", False, "error output")

        assert page._install_in_progress is False

    # ── Task 1: Guard tests ───────────────────────────────────────────

    def test_on_install_dep_is_blocked_when_install_in_progress(
        self, page: ModelServicesPage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        messages: list[tuple[str, str]] = []
        calls: list[tuple[str, Path, bool, bool]] = []

        page._install_in_progress = True
        monkeypatch.setattr(page, "_resolve_venv_python", lambda _venv: Path("C:/fake/python.exe"))
        monkeypatch.setattr(
            page,
            "_run_pip_install",
            lambda package, python, upgrade, force_reinstall=False: calls.append(
                (package, python, upgrade, force_reinstall)
            ),
        )
        monkeypatch.setattr(
            "ivo.ui.model_services_page.QMessageBox.information",
            lambda _parent, title, text: messages.append((title, text)),
        )

        page._on_install_dep("demucs", ".venv", "missing")

        assert calls == []
        assert messages == [("提示", "已有依赖安装任务正在进行，请等待完成后再操作。")]

    def test_on_upgrade_dep_is_blocked_when_install_in_progress(
        self, page: ModelServicesPage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        messages: list[tuple[str, str]] = []
        calls: list[tuple[str, Path, bool, bool]] = []

        page._install_in_progress = True
        monkeypatch.setattr(page, "_resolve_venv_python", lambda _venv: Path("C:/fake/python.exe"))
        monkeypatch.setattr(
            page,
            "_run_pip_install",
            lambda package, python, upgrade, force_reinstall=False: calls.append(
                (package, python, upgrade, force_reinstall)
            ),
        )
        monkeypatch.setattr(
            "ivo.ui.model_services_page.QMessageBox.information",
            lambda _parent, title, text: messages.append((title, text)),
        )

        page._on_upgrade_dep("torch", ".venv")

        assert calls == []
        assert messages == [("提示", "已有依赖安装任务正在进行，请等待完成后再操作。")]

    def test_install_all_missing_is_blocked_when_install_in_progress(
        self, page: ModelServicesPage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from ivo.model_services.local_models import DependencyStatus

        messages: list[tuple[str, str]] = []
        calls: list[tuple[str, Path, bool, bool]] = []

        page._install_in_progress = True
        page._last_statuses = [
            DependencyStatus("demucs", "demucs", "missing", venv_name=".venv")
        ]
        monkeypatch.setattr(page, "_resolve_venv_python", lambda _venv: Path("C:/fake/python.exe"))
        monkeypatch.setattr(
            page,
            "_run_pip_install",
            lambda package, python, upgrade, force_reinstall=False: calls.append(
                (package, python, upgrade, force_reinstall)
            ),
        )
        monkeypatch.setattr(
            "ivo.ui.model_services_page.QMessageBox.information",
            lambda _parent, title, text: messages.append((title, text)),
        )

        page._install_all_missing()

        assert calls == []
        assert messages == [("提示", "已有依赖安装任务正在进行，请等待完成后再操作。")]

    # ── Task 2: UI rebuild keeps buttons disabled ─────────────────────

    def test_build_dep_ui_keeps_row_buttons_disabled_when_install_in_progress(
        self, page: ModelServicesPage,
    ) -> None:
        from PySide6.QtWidgets import QPushButton
        from ivo.model_services.local_models import DependencyStatus

        statuses = [
            DependencyStatus("demucs", "demucs", "missing", venv_name=".venv"),
            DependencyStatus(
                "soundfile", "soundfile", "broken", version="0.13.1", venv_name=".venv"
            ),
        ]

        page._install_in_progress = True
        page._build_dep_ui(statuses, None)

        action_buttons = [
            button
            for button in page._dep_content.findChildren(QPushButton)
            if button.text() in {"安装", "修复", "升级"}
        ]
        assert action_buttons
        assert all(not button.isEnabled() for button in action_buttons)
        assert not page._refresh_btn.isEnabled()
        assert not page._install_all_btn.isEnabled()

    # ── Task 3: Queue continuation keeps lock ──────────────────────────

    def test_on_install_finished_continues_queue_without_enabling_buttons(
        self, page: ModelServicesPage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        next_python = Path("C:/fake/.venv/Scripts/python.exe")
        calls: list[tuple[str, Path, bool, bool]] = []
        enabled_values: list[bool] = []

        page._install_in_progress = True
        page._missing_queue = [("soundfile", next_python, "broken")]
        page._refresh_btn.setEnabled(False)
        page._install_all_btn.setEnabled(False)

        monkeypatch.setattr(
            page,
            "_set_dep_row_buttons_enabled",
            lambda enabled: enabled_values.append(enabled),
        )
        monkeypatch.setattr(
            page,
            "_run_pip_install",
            lambda package, python, upgrade, force_reinstall=False: calls.append(
                (package, python, upgrade, force_reinstall)
            ),
        )

        page._on_install_finished("demucs", True, "ok")

        assert calls == [("soundfile", next_python, False, True)]
        assert page._install_in_progress is True
        assert not page._refresh_btn.isEnabled()
        assert not page._install_all_btn.isEnabled()
        assert True not in enabled_values

    def test_on_install_finished_reenables_buttons_when_queue_done(
        self, page: ModelServicesPage, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        enabled_values: list[bool] = []
        refreshed: list[bool] = []

        page._install_in_progress = True
        page._missing_queue = []
        page._refresh_btn.setEnabled(False)
        page._install_all_btn.setEnabled(False)

        monkeypatch.setattr(
            page,
            "_set_dep_row_buttons_enabled",
            lambda enabled: enabled_values.append(enabled),
        )
        monkeypatch.setattr(page, "_refresh_dep_status", lambda: refreshed.append(True))

        page._on_install_finished("soundfile", True, "ok")

        assert page._install_in_progress is False
        assert page._refresh_btn.isEnabled()
        assert page._install_all_btn.isEnabled()
        assert enabled_values == [True]
        assert refreshed == [True]

    # ── Task 4: Real button click regression ───────────────────────────

    def test_dep_action_buttons_stay_disabled_after_rebuild_during_install(
        self, page: ModelServicesPage,
    ) -> None:
        from PySide6.QtWidgets import QPushButton
        from ivo.model_services.local_models import DependencyStatus

        statuses = [
            DependencyStatus("demucs", "demucs", "missing", venv_name=".venv"),
            DependencyStatus(
                "soundfile", "soundfile", "broken", version="0.13.1", venv_name=".venv"
            ),
        ]

        page._build_dep_ui(statuses, None)
        action_buttons = [
            button
            for button in page._dep_content.findChildren(QPushButton)
            if button.text() in {"安装", "修复", "升级"}
        ]
        assert action_buttons
        assert all(button.isEnabled() for button in action_buttons)

        page._install_in_progress = True
        page._set_dep_row_buttons_enabled(False)
        assert all(not button.isEnabled() for button in action_buttons)

        # Rebuild UI while install is in progress
        page._build_dep_ui(statuses, {"demucs": "4.1.0"})
        rebuilt_buttons = [
            button
            for button in page._dep_content.findChildren(QPushButton)
            if button.text() in {"安装", "修复", "升级"}
        ]
        assert rebuilt_buttons
        assert all(not button.isEnabled() for button in rebuilt_buttons)
