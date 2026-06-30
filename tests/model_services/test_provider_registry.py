"""Tests for model_services provider registry."""

from __future__ import annotations


def test_registry_contains_separation_providers() -> None:
    from ivo.model_services.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    separation_entries = [
        entry for entry in registry.list_all() if "separation" in entry.supported_stages
    ]
    provider_ids = {entry.provider_id for entry in separation_entries}
    assert "audioshake" in provider_ids
    assert "lalalai" in provider_ids
    assert "demucs" in provider_ids


def test_registry_contains_asr_providers() -> None:
    from ivo.model_services.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    asr_entries = [
        entry for entry in registry.list_all() if "asr" in entry.supported_stages
    ]
    provider_ids = {entry.provider_id for entry in asr_entries}
    assert "openai" in provider_ids
    assert "deepgram" in provider_ids
    assert "alibaba" in provider_ids


def test_registry_contains_tts_providers() -> None:
    from ivo.model_services.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    tts_entries = [
        entry for entry in registry.list_all() if "tts" in entry.supported_stages
    ]
    provider_ids = {entry.provider_id for entry in tts_entries}
    assert "openai" in provider_ids
    assert "elevenlabs" in provider_ids
    assert "alibaba_qwen_tts" in provider_ids


def test_registry_iflytek_not_mvp_enabled() -> None:
    from ivo.model_services.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    iflytek_entries = [
        entry
        for entry in registry.list_all()
        if entry.provider_id == "iflytek"
    ]
    assert len(iflytek_entries) == 1
    assert iflytek_entries[0].mvp_enabled is False


def test_registry_local_models_present() -> None:
    from ivo.model_services.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    local_entries = [
        entry for entry in registry.list_all() if not entry.requires_api_key
    ]
    provider_ids = {entry.provider_id for entry in local_entries}
    assert "demucs" in provider_ids
    assert "faster-whisper-large-v3" in provider_ids
    assert "faster-whisper-small" in provider_ids
    assert "faster-whisper-tiny" in provider_ids
    assert "pyannote-community-1" in provider_ids
    assert "f5-tts" in provider_ids
    assert "cosyvoice3" in provider_ids


def test_f5_tts_provider_exposes_runtime_mode_setting() -> None:
    from ivo.model_services.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    entry = registry.get("f5-tts")
    assert entry is not None
    field_names = {field.name for field in entry.config_fields}
    assert "runtime_mode" in field_names


def test_registry_get_entry_by_id() -> None:
    from ivo.model_services.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    entry = registry.get("openai")
    assert entry is not None
    assert entry.provider_id == "openai"
    assert "asr" in entry.supported_stages


def test_registry_get_unknown_returns_none() -> None:
    from ivo.model_services.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    assert registry.get("nonexistent_provider") is None


def test_registry_translation_providers() -> None:
    from ivo.model_services.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    translation_entries = [
        entry for entry in registry.list_all() if "translation" in entry.supported_stages
    ]
    provider_ids = {entry.provider_id for entry in translation_entries}
    assert "openai_compatible_translation" in provider_ids
    assert "anthropic_compatible_translation" in provider_ids
    assert "openai" not in provider_ids


def test_openai_fields_are_stage_specific() -> None:
    from ivo.model_services.provider_registry import ProviderRegistry

    registry = ProviderRegistry()

    asr_fields = [f.name for f in registry.get_config_fields("openai", "asr")]
    diar_fields = [f.name for f in registry.get_config_fields("openai", "diarization")]
    tts_fields = [f.name for f in registry.get_config_fields("openai", "tts")]

    assert "asr_model" in asr_fields
    assert "tts_model" not in asr_fields
    assert "voice" not in asr_fields

    assert "diarization_model" in diar_fields
    assert "asr_model" not in diar_fields
    assert "tts_model" not in diar_fields
    assert "voice" not in diar_fields

    assert "tts_model" in tts_fields
    assert "voice" in tts_fields
    assert "asr_model" not in tts_fields


def test_translation_providers_use_translation_fields_only() -> None:
    from ivo.model_services.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    fields = [
        f.name
        for f in registry.get_config_fields(
            "openai_compatible_translation", "translation"
        )
    ]
    assert set(fields) == {
        "api_key",
        "request_url",
        "translation_model",
        "temperature",
        "max_tokens",
    }
    api_key_field = next(f for f in registry.get_config_fields(
        "openai_compatible_translation", "translation"
    ) if f.name == "api_key")
    assert api_key_field.required is False


def test_registry_diarization_providers() -> None:
    from ivo.model_services.provider_registry import ProviderRegistry

    registry = ProviderRegistry()
    diar_entries = [
        entry for entry in registry.list_all() if "diarization" in entry.supported_stages
    ]
    provider_ids = {entry.provider_id for entry in diar_entries}
    assert "openai" in provider_ids
    assert "deepgram" in provider_ids
    assert "pyannote-community-1" in provider_ids
