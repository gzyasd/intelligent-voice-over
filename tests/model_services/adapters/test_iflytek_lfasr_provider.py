"""Tests for iFlytek lfasr provider adapter (P2 stub)."""

from __future__ import annotations

import pytest

from ivo.model_services.adapters.iflytek_lfasr import IflytekLfasrProvider


class TestIflytekLfasrProvider:
    def test_provider_metadata(self) -> None:
        provider = IflytekLfasrProvider(app_id="test-app", secret_key="test-secret")
        assert provider.provider_id == "iflytek"
        assert provider.stage == "asr"
        assert provider.protocol == "iflytek_lfasr"

    def test_to_pipeline_adapter_not_implemented(self) -> None:
        provider = IflytekLfasrProvider(app_id="test-app", secret_key="test-secret")
        with pytest.raises(NotImplementedError, match="P2 feature"):
            provider.to_pipeline_adapter()

    def test_generate_signa(self) -> None:
        provider = IflytekLfasrProvider(app_id="appid123", secret_key="secretkey456")
        signa = provider._generate_signa("1234567890")
        assert isinstance(signa, str)
        assert len(signa) > 0  # Should produce a base64 encoded HMAC

    def test_validate_credentials_stub(self) -> None:
        provider = IflytekLfasrProvider(app_id="test-app", secret_key="test-secret")
        result = provider.validate_credentials()
        # Stub implementation always returns ok=True
        assert result.ok is True
        assert result.provider_id == "iflytek"
