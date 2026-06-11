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
        if hasattr(page, "_worker"):
            page._worker.result_ready.connect(lambda _s: _on_loaded())
            page._worker.finished.connect(_on_loaded)
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
