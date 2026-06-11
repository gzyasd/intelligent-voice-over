"""Tests for ProviderConfigDialog."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication

from ivo.model_services.provider_registry import ProviderRegistry
from ivo.ui.provider_dialogs import ProviderConfigDialog


@pytest.fixture
def qt_app(qapp: QApplication) -> QApplication:
    return qapp


class TestProviderConfigDialogInit:
    def test_dialog_creates_with_stage(self, qt_app: QApplication) -> None:
        dialog = ProviderConfigDialog(stage="asr")
        assert dialog._stage == "asr"
        assert dialog.windowTitle() == "添加供应商"
        assert dialog.provider_combo.count() > 0

    def test_dialog_edit_mode_title(self, qt_app: QApplication) -> None:
        dialog = ProviderConfigDialog(
            stage="asr",
            existing_values={"display_name": "Test"},
        )
        assert dialog.windowTitle() == "编辑供应商"

    def test_provider_combo_has_entries_for_stage(self, qt_app: QApplication) -> None:
        dialog = ProviderConfigDialog(stage="asr")
        # Should have at least OpenAI, Deepgram, Alibaba + separator + local
        assert dialog.provider_combo.count() >= 4

    def test_provider_combo_has_local_option(self, qt_app: QApplication) -> None:
        dialog = ProviderConfigDialog(stage="asr")
        # Should include registry local providers (no generic "local" item)
        provider_ids = [
            dialog.provider_combo.itemData(i)
            for i in range(dialog.provider_combo.count())
        ]
        assert "faster-whisper-large-v3" in provider_ids

    def test_dialog_minimum_width(self, qt_app: QApplication) -> None:
        dialog = ProviderConfigDialog(stage="tts")
        assert dialog.minimumWidth() == 480


class TestProviderConfigDialogFields:
    def test_cloud_fields_shown_for_api_provider(self, qt_app: QApplication) -> None:
        dialog = ProviderConfigDialog(stage="asr")
        # First provider should be an API provider (OpenAI)
        dialog.provider_combo.setCurrentIndex(0)
        assert dialog._cloud_warning.isVisible() or not dialog._cloud_warning.isHidden()

    def test_local_fields_shown_when_local_selected(self, qt_app: QApplication) -> None:
        dialog = ProviderConfigDialog(stage="asr")
        # Find a local provider from registry (e.g. faster-whisper-large-v3)
        local_index = -1
        for i in range(dialog.provider_combo.count()):
            if dialog.provider_combo.itemData(i) == "faster-whisper-large-v3":
                local_index = i
                break
        assert local_index >= 0
        dialog.provider_combo.setCurrentIndex(local_index)
        # Local model path field should be present via registry config_fields
        assert "local_model_path" in dialog._field_widgets or dialog._local_path_edit is not None

    def test_display_name_edit_exists(self, qt_app: QApplication) -> None:
        dialog = ProviderConfigDialog(stage="translation")
        assert dialog.display_name_edit is not None

    def test_api_key_toggle_visibility(self, qt_app: QApplication) -> None:
        dialog = ProviderConfigDialog(stage="asr")
        dialog.provider_combo.setCurrentIndex(0)
        # Find API key widget
        api_key_widget = dialog._field_widgets.get("api_key")
        if api_key_widget:
            from PySide6.QtWidgets import QLineEdit
            edit = dialog._get_api_key_edit(api_key_widget)
            if edit:
                assert edit.echoMode() == QLineEdit.EchoMode.Password
                # Toggle
                toggle_btn = api_key_widget.findChild(
                    __import__("PySide6.QtWidgets", fromlist=["QPushButton"]).QPushButton
                )
                if toggle_btn:
                    toggle_btn.click()
                    assert edit.echoMode() == QLineEdit.EchoMode.Normal

    def test_openai_asr_dialog_does_not_show_tts_fields(
        self, qt_app: QApplication
    ) -> None:
        dialog = ProviderConfigDialog(stage="asr", registry=ProviderRegistry())
        assert dialog.provider_combo.currentData() == "openai"
        assert "asr_model" in dialog._field_widgets
        assert "tts_model" not in dialog._field_widgets
        assert "voice" not in dialog._field_widgets

    def test_openai_diarization_dialog_does_not_show_tts_fields(
        self, qt_app: QApplication
    ) -> None:
        dialog = ProviderConfigDialog(stage="diarization", registry=ProviderRegistry())
        assert dialog.provider_combo.currentData() == "openai"
        assert "diarization_model" in dialog._field_widgets
        assert "asr_model" not in dialog._field_widgets
        assert "tts_model" not in dialog._field_widgets
        assert "voice" not in dialog._field_widgets

    def test_openai_tts_dialog_does_not_show_asr_fields(
        self, qt_app: QApplication
    ) -> None:
        dialog = ProviderConfigDialog(stage="tts", registry=ProviderRegistry())
        for i in range(dialog.provider_combo.count()):
            if dialog.provider_combo.itemData(i) == "openai":
                dialog.provider_combo.setCurrentIndex(i)
                break
        assert "tts_model" in dialog._field_widgets
        assert "voice" in dialog._field_widgets
        assert "asr_model" not in dialog._field_widgets

    def test_translation_dialog_shows_request_url_not_audio_fields(
        self, qt_app: QApplication
    ) -> None:
        dialog = ProviderConfigDialog(stage="translation", registry=ProviderRegistry())
        assert dialog.provider_combo.currentData() == "openai_compatible_translation"
        assert "request_url" in dialog._field_widgets
        assert "translation_model" in dialog._field_widgets
        assert "asr_model" not in dialog._field_widgets
        assert "tts_model" not in dialog._field_widgets
        assert "voice" not in dialog._field_widgets

    def test_translation_connection_test_uses_request_url(
        self, qt_app: QApplication, monkeypatch
    ) -> None:
        captured: dict[str, object] = {}

        class FakeValidationResult:
            ok = True
            latency_ms = 12
            error_code = None
            error_message = None

        class FakeValidator:
            def validate_credentials(self) -> FakeValidationResult:
                return FakeValidationResult()

        def fake_create_validator(**kwargs):
            captured.update(kwargs)
            return FakeValidator()

        monkeypatch.setattr(
            "ivo.model_services.validators.create_validator",
            fake_create_validator,
        )
        dialog = ProviderConfigDialog(stage="translation", registry=ProviderRegistry())
        api_key_edit = dialog._get_api_key_edit(dialog._field_widgets["api_key"])
        assert api_key_edit is not None
        api_key_edit.setText("lm-studio")

        request_url_widget = dialog._field_widgets["request_url"]
        request_url_widget.setText("http://127.0.0.1:1995/v1/chat/completions")

        dialog._on_test_connection()

        assert captured["provider_id"] == "openai_compatible_translation"
        assert captured["stage"] == "translation"
        assert captured["base_url"] == "http://127.0.0.1:1995/v1/chat/completions"

    def test_openai_compatible_translation_can_test_without_api_key(
        self, qt_app: QApplication, monkeypatch
    ) -> None:
        captured: dict[str, object] = {}

        class FakeValidationResult:
            ok = True
            latency_ms = 12
            error_code = None
            error_message = None

        class FakeValidator:
            def validate_credentials(self) -> FakeValidationResult:
                return FakeValidationResult()

        def fake_create_validator(**kwargs):
            captured.update(kwargs)
            return FakeValidator()

        monkeypatch.setattr(
            "ivo.model_services.validators.create_validator",
            fake_create_validator,
        )
        dialog = ProviderConfigDialog(stage="translation", registry=ProviderRegistry())
        request_url_widget = dialog._field_widgets["request_url"]
        request_url_widget.setText("http://127.0.0.1:1995/v1/chat/completions")

        dialog._update_test_button_enabled()
        assert dialog.test_button.isEnabled()

        dialog._on_test_connection()

        assert captured["provider_id"] == "openai_compatible_translation"
        assert captured["api_key"] == ""
        assert "连接成功" in dialog.test_result_label.text()


class TestProviderConfigDialogValues:
    def test_values_returns_stage_and_provider(self, qt_app: QApplication) -> None:
        dialog = ProviderConfigDialog(stage="tts")
        dialog.display_name_edit.setText("My TTS")
        values = dialog.values()
        assert values["stage"] == "tts"
        assert values["display_name"] == "My TTS"

    def test_values_local_kind(self, qt_app: QApplication) -> None:
        dialog = ProviderConfigDialog(stage="asr")
        # Select local provider from registry
        for i in range(dialog.provider_combo.count()):
            if dialog.provider_combo.itemData(i) == "faster-whisper-large-v3":
                dialog.provider_combo.setCurrentIndex(i)
                break
        dialog.display_name_edit.setText("Local ASR")
        values = dialog.values()
        assert values["kind"] == "local"
        assert values["provider_id"] == "faster-whisper-large-v3"
        assert values.get("local_model_path") is not None

    def test_is_local_returns_true_for_local(self, qt_app: QApplication) -> None:
        dialog = ProviderConfigDialog(stage="asr")
        for i in range(dialog.provider_combo.count()):
            if dialog.provider_combo.itemData(i) == "faster-whisper-large-v3":
                dialog.provider_combo.setCurrentIndex(i)
                break
        assert dialog.is_local()

    def test_is_local_returns_false_for_api(self, qt_app: QApplication) -> None:
        dialog = ProviderConfigDialog(stage="asr")
        dialog.provider_combo.setCurrentIndex(0)
        assert not dialog.is_local()

    def test_existing_values_pre_filled(self, qt_app: QApplication) -> None:
        dialog = ProviderConfigDialog(
            stage="asr",
            existing_values={"display_name": "Existing Config"},
        )
        assert dialog.display_name_edit.text() == "Existing Config"

    def test_display_name_method(self, qt_app: QApplication) -> None:
        dialog = ProviderConfigDialog(stage="asr")
        dialog.display_name_edit.setText("Test Name")
        assert dialog.display_name() == "Test Name"
