"""Tests for translation provider adapters."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx


def test_openai_compatible_translation_provider_creation() -> None:
    from ivo.model_services.adapters.openai_compatible_translation import (
        OpenAICompatibleTranslationProvider,
    )

    provider = OpenAICompatibleTranslationProvider(
        base_url="https://api.openai.com",
        api_key="sk-test",
        model_name="gpt-4o-mini",
    )
    assert provider.provider_id == "openai_compatible"
    assert provider.stage == "translation"


def test_openai_compatible_translation_to_pipeline_adapter() -> None:
    from ivo.model_services.adapters.openai_compatible_translation import (
        OpenAICompatibleTranslationProvider,
    )

    provider = OpenAICompatibleTranslationProvider(
        base_url="https://api.openai.com",
        api_key="sk-test",
        model_name="gpt-4o-mini",
        config_id="test-1",
    )
    adapter = provider.to_pipeline_adapter()
    assert hasattr(adapter, "translate")
    assert adapter.profile.stage == "translation"
    assert "openai.com" in adapter.profile.url


def test_openai_compatible_validation_200() -> None:
    from ivo.model_services.adapters.openai_compatible_translation import (
        OpenAICompatibleTranslationProvider,
    )

    provider = OpenAICompatibleTranslationProvider(
        base_url="https://api.openai.com",
        api_key="valid-key",
    )
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200

    with patch("httpx.get", return_value=mock_response):
        result = provider.validate_credentials()

    assert result.ok is True


def test_openai_compatible_validation_401() -> None:
    from ivo.model_services.adapters.openai_compatible_translation import (
        OpenAICompatibleTranslationProvider,
    )

    provider = OpenAICompatibleTranslationProvider(
        base_url="https://api.openai.com",
        api_key="invalid",
    )
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401

    with patch("httpx.get", return_value=mock_response):
        result = provider.validate_credentials()

    assert result.ok is False
    assert result.error_code == "AUTH_FAILED"


def test_anthropic_compatible_translation_provider_creation() -> None:
    from ivo.model_services.adapters.anthropic_compatible_translation import (
        AnthropicCompatibleTranslationProvider,
    )

    provider = AnthropicCompatibleTranslationProvider(
        base_url="https://api.anthropic.com",
        api_key="sk-ant-test",
        model_name="claude-sonnet-4-20250514",
    )
    assert provider.provider_id == "anthropic_compatible"
    assert provider.stage == "translation"


def test_anthropic_compatible_to_pipeline_adapter() -> None:
    from ivo.model_services.adapters.anthropic_compatible_translation import (
        AnthropicCompatibleTranslationProvider,
    )

    provider = AnthropicCompatibleTranslationProvider(
        base_url="https://api.anthropic.com",
        api_key="sk-ant-test",
        config_id="test-2",
    )
    adapter = provider.to_pipeline_adapter()
    assert hasattr(adapter, "translate")
    assert "anthropic" in adapter.profile.url
    assert "x-api-key" in adapter.profile.headers


def test_anthropic_compatible_validation_200() -> None:
    from ivo.model_services.adapters.anthropic_compatible_translation import (
        AnthropicCompatibleTranslationProvider,
    )

    provider = AnthropicCompatibleTranslationProvider(
        base_url="https://api.anthropic.com",
        api_key="valid-key",
    )
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200

    with patch("httpx.post", return_value=mock_response):
        result = provider.validate_credentials()

    assert result.ok is True
