"""Tests for LALAL.AI separation provider adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from ivo.model_services.adapters.lalalai import LalalaiProvider


class TestLalalaiProvider:
    def test_provider_metadata(self) -> None:
        provider = LalalaiProvider(api_key="test-key")
        assert provider.provider_id == "lalalai"
        assert provider.stage == "separation"
        assert provider.protocol == "lalalai_separation"

    def test_to_pipeline_adapter_has_separate_method(self) -> None:
        provider = LalalaiProvider(api_key="test-key")
        adapter = provider.to_pipeline_adapter()
        assert hasattr(adapter, "separate")
        assert callable(adapter.separate)

    @patch("ivo.model_services.adapters.lalalai.httpx.request")
    def test_validate_credentials_success(self, mock_request: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        provider = LalalaiProvider(api_key="valid-key")
        result = provider.validate_credentials()
        assert result.ok is True
        assert result.provider_id == "lalalai"

    @patch("ivo.model_services.adapters.lalalai.httpx.request")
    def test_validate_credentials_auth_failed(self, mock_request: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_request.return_value = mock_response
        provider = LalalaiProvider(api_key="bad-key")
        result = provider.validate_credentials()
        assert result.ok is False
        assert result.error_code == "AUTH_FAILED"

    @patch("ivo.model_services.adapters.lalalai.httpx.request")
    def test_validate_credentials_connection_error(self, mock_request: MagicMock) -> None:
        import httpx
        mock_request.side_effect = httpx.ConnectError("connection refused")
        provider = LalalaiProvider(api_key="any-key")
        result = provider.validate_credentials()
        assert result.ok is False
        assert result.error_code == "CONNECTION_ERROR"
