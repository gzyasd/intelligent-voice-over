"""Tests for OpenAI TTS provider adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from ivo.model_services.adapters.openai_tts import OpenAITtsProvider


class TestOpenAITtsProvider:
    def test_provider_metadata(self) -> None:
        provider = OpenAITtsProvider(api_key="test-key")
        assert provider.provider_id == "openai"
        assert provider.stage == "tts"
        assert provider.protocol == "openai_tts"

    def test_default_model(self) -> None:
        provider = OpenAITtsProvider(api_key="test-key")
        assert provider._model_name == "gpt-4o-mini-tts"
        assert provider._voice == "alloy"

    def test_to_pipeline_adapter_has_synthesize(self) -> None:
        provider = OpenAITtsProvider(api_key="test-key")
        adapter = provider.to_pipeline_adapter()
        assert hasattr(adapter, "synthesize")
        assert callable(adapter.synthesize)

    @patch("ivo.model_services.adapters.openai_tts.httpx.post")
    def test_validate_credentials_success(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        provider = OpenAITtsProvider(api_key="valid-key")
        result = provider.validate_credentials()
        assert result.ok is True

    @patch("ivo.model_services.adapters.openai_tts.httpx.post")
    def test_validate_credentials_auth_failed(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        provider = OpenAITtsProvider(api_key="bad-key")
        result = provider.validate_credentials()
        assert result.ok is False
        assert result.error_code == "AUTH_FAILED"
