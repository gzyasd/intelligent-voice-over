"""Tests for AudioShake separation provider adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from ivo.model_services.adapters.audioshake import AudioShakeProvider


class TestAudioShakeProvider:
    def test_provider_metadata(self) -> None:
        provider = AudioShakeProvider(api_key="test-key")
        assert provider.provider_id == "audioshake"
        assert provider.stage == "separation"
        assert provider.protocol == "audioshake_separation"

    def test_to_pipeline_adapter_has_separate_method(self) -> None:
        provider = AudioShakeProvider(api_key="test-key")
        adapter = provider.to_pipeline_adapter()
        assert hasattr(adapter, "separate")
        assert callable(adapter.separate)

    @patch("ivo.model_services.adapters.audioshake.httpx.get")
    def test_validate_credentials_success(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        provider = AudioShakeProvider(api_key="valid-key")
        result = provider.validate_credentials()
        assert result.ok is True
        assert result.provider_id == "audioshake"

    @patch("ivo.model_services.adapters.audioshake.httpx.get")
    def test_validate_credentials_auth_failed(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        provider = AudioShakeProvider(api_key="bad-key")
        result = provider.validate_credentials()
        assert result.ok is False
        assert result.error_code == "AUTH_FAILED"

    @patch("ivo.model_services.adapters.audioshake.httpx.get")
    def test_validate_credentials_forbidden(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response
        provider = AudioShakeProvider(api_key="forbidden-key")
        result = provider.validate_credentials()
        assert result.ok is False
        assert result.error_code == "AUTH_FAILED"

    @patch("ivo.model_services.adapters.audioshake.httpx.get")
    def test_validate_credentials_connection_error(self, mock_get: MagicMock) -> None:
        import httpx
        mock_get.side_effect = httpx.ConnectError("connection refused")
        provider = AudioShakeProvider(api_key="any-key")
        result = provider.validate_credentials()
        assert result.ok is False
        assert result.error_code == "CONNECTION_ERROR"
