"""Tests for SchemeManagementPage."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QLabel

from ivo.model_services.provider_config import (
    DubbingScheme,
    SchemeStageBinding,
    StageProviderConfig,
)
from ivo.model_services.provider_store import ProviderStore
from ivo.model_services.stages import STAGE_NAMES
from ivo.ui.scheme_management_page import SchemeManagementPage, _StageRow


@pytest.fixture
def qt_app(qapp: QApplication) -> QApplication:
    return qapp


@pytest.fixture
def tmp_store(tmp_path: Path) -> ProviderStore:
    return ProviderStore(tmp_path / ".ivo-config")


@pytest.fixture
def page(qt_app: QApplication, tmp_store: ProviderStore) -> SchemeManagementPage:
    return SchemeManagementPage(store=tmp_store)


class TestSchemeManagementPageInit:
    def test_page_title(self, page: SchemeManagementPage) -> None:
        title = page.findChild(QLabel, "PageTitle")
        assert title is not None
        assert title.text() == "方案管理"

    def test_has_scheme_buttons(self, page: SchemeManagementPage) -> None:
        assert len(page._scheme_buttons) >= 1

    def test_creates_default_mock_scheme(self, page: SchemeManagementPage) -> None:
        assert len(page._scheme_buttons) >= 1

    def test_has_stage_rows(self, page: SchemeManagementPage) -> None:
        rows = page._stage_rows
        assert len(rows) == len(STAGE_NAMES)
        for stage in STAGE_NAMES:
            assert stage in rows

    def test_has_action_buttons(self, page: SchemeManagementPage) -> None:
        assert page._validate_button is not None
        assert page._set_default_button is not None
        assert page._new_scheme_button is not None


class TestSchemeManagementPageCRUD:
    def test_new_scheme_via_store(
        self, qt_app: QApplication, tmp_store: ProviderStore
    ) -> None:
        scheme = DubbingScheme(
            id="test-1",
            display_name="Test Scheme",
            bindings=[],
        )
        tmp_store.save_scheme(scheme)
        page = SchemeManagementPage(store=tmp_store)
        assert "test-1" in page._scheme_buttons

    def test_delete_scheme_via_store(
        self, qt_app: QApplication, tmp_store: ProviderStore
    ) -> None:
        tmp_store.save_scheme(DubbingScheme(id="del-1", display_name="Delete Me", bindings=[]))
        tmp_store.save_scheme(DubbingScheme(id="keep-1", display_name="Keep Me", bindings=[]))
        page = SchemeManagementPage(store=tmp_store)
        tmp_store.delete_scheme("del-1")
        page.refresh()
        assert "del-1" not in page._scheme_buttons
        assert "keep-1" in page._scheme_buttons

    def test_copy_scheme(
        self, qt_app: QApplication, tmp_store: ProviderStore
    ) -> None:
        tmp_store.save_scheme(DubbingScheme(id="orig", display_name="Original", bindings=[]))
        page = SchemeManagementPage(store=tmp_store)
        # Select the original
        page._select_scheme("orig")
        page._on_copy_scheme()
        schemes = tmp_store.load_schemes()
        assert len(schemes) == 2
        assert any("副本" in s.display_name for s in schemes)


class TestStageRow:
    def test_stage_row_initial_state(self, qt_app: QApplication) -> None:
        row = _StageRow("asr")
        assert row.config_id() is None
        assert row._service_label.text() == "未配置"

    def test_stage_row_set_config(self, qt_app: QApplication) -> None:
        row = _StageRow("tts")
        config = StageProviderConfig(
            id="cfg-1",
            display_name="OpenAI TTS",
            provider_key="openai",
            kind="api",
            stage="tts",
            protocol="openai_tts",
            model_name="gpt-4o-mini-tts",
            last_validation_status="ready",
        )
        row.set_config(config)
        assert row.config_id() == "cfg-1"
        assert "OpenAI TTS" in row._service_label.text()

    def test_stage_row_clear_config(self, qt_app: QApplication) -> None:
        row = _StageRow("translation")
        config = StageProviderConfig(
            id="cfg-2",
            display_name="Test",
            provider_key="test",
            kind="api",
            stage="translation",
            protocol="test_translation",
        )
        row.set_config(config)
        assert row.config_id() == "cfg-2"
        row.set_config(None)
        assert row.config_id() is None


class TestSchemeValidation:
    def test_validate_with_missing_stages(
        self, qt_app: QApplication, tmp_store: ProviderStore
    ) -> None:
        page = SchemeManagementPage(store=tmp_store)
        page._on_validate()
        # All stages are unconfigured, should show error
        assert "未配置" in page._status_label.text()

    def test_validate_with_all_stages_configured(
        self, qt_app: QApplication, tmp_store: ProviderStore
    ) -> None:
        stage_protocols: dict[str, tuple[str, str]] = {
            "separation": ("audioshake", "audioshake_separation"),
            "asr": ("openai", "openai_asr"),
            "diarization": ("openai", "openai_diarize"),
            "translation": ("openai", "openai_compatible_translation"),
            "tts": ("openai", "openai_tts"),
        }
        for stage, (provider_key, protocol) in stage_protocols.items():
            config = StageProviderConfig(
                id=f"cfg-{stage}",
                display_name=f"{stage} Config",
                provider_key=provider_key,
                kind="api",
                stage=stage,  # type: ignore[arg-type]
                protocol=protocol,
                last_validation_status="ready",
            )
            tmp_store.save_stage_config(config)

        scheme = DubbingScheme(
            id="full-scheme",
            display_name="Full Scheme",
            bindings=[
                SchemeStageBinding(stage=stage, stage_config_id=f"cfg-{stage}")
                for stage in STAGE_NAMES
            ],
        )
        tmp_store.save_scheme(scheme)

        page = SchemeManagementPage(store=tmp_store)
        page._select_scheme("full-scheme")
        page._on_validate()
        assert "验证通过" in page._status_label.text()


class TestSchemeDefault:
    def test_set_default(
        self, qt_app: QApplication, tmp_store: ProviderStore
    ) -> None:
        page = SchemeManagementPage(store=tmp_store)
        page._on_set_default()
        default_id = tmp_store.load_default_scheme_id()
        assert default_id is not None
