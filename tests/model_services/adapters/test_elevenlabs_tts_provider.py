"""Tests for ElevenLabs TTS provider adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from ivo.model_services.adapters.elevenlabs_tts import ElevenLabsTtsProvider


class TestElevenLabsTtsProvider:
    def test_provider_metadata(self) -> None:
        provider = ElevenLabsTtsProvider(api_key="test-key")
        assert provider.provider_id == "elevenlabs"
        assert provider.stage == "tts"
        assert provider.protocol == "elevenlabs_tts"

    def test_default_model(self) -> None:
        provider = ElevenLabsTtsProvider(api_key="test-key")
        assert provider._model_id == "eleven_multilingual_v2"

    def test_to_pipeline_adapter_has_synthesize(self) -> None:
        provider = ElevenLabsTtsProvider(api_key="test-key", voice_id="voice123")
        adapter = provider.to_pipeline_adapter()
        assert hasattr(adapter, "synthesize")
        assert callable(adapter.synthesize)

    @patch("ivo.model_services.adapters.elevenlabs_tts.httpx.get")
    def test_validate_credentials_success(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        provider = ElevenLabsTtsProvider(api_key="valid-key")
        result = provider.validate_credentials()
        assert result.ok is True

    @patch("ivo.model_services.adapters.elevenlabs_tts.httpx.get")
    def test_validate_credentials_auth_failed(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        provider = ElevenLabsTtsProvider(api_key="bad-key")
        result = provider.validate_credentials()
        assert result.ok is False
        assert result.error_code == "AUTH_FAILED"
