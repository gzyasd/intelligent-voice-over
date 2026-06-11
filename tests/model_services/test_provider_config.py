"""Tests for model_services provider config data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_openai_account_can_be_reused_by_asr_diarization_and_tts_configs() -> None:
    from ivo.model_services.provider_config import ProviderAccount, StageProviderConfig

    account = ProviderAccount(
        id="acct-openai",
        display_name="我的 OpenAI",
        provider_key="openai",
        kind="api",
        api_key_ref="secret-openai",
    )
    asr = StageProviderConfig(
        id="stage-openai-asr",
        display_name="OpenAI 转写",
        account_id=account.id,
        provider_key="openai",
        kind="api",
        stage="asr",
        protocol="openai_asr",
        model_name="gpt-4o-transcribe-diarize",
    )
    tts = StageProviderConfig(
        id="stage-openai-tts",
        display_name="OpenAI 配音",
        account_id=account.id,
        provider_key="openai",
        kind="api",
        stage="tts",
        protocol="openai_tts",
        model_name="gpt-4o-mini-tts",
    )

    assert asr.account_id == account.id
    assert tts.account_id == account.id


def test_provider_account_rejects_empty_id() -> None:
    from ivo.model_services.provider_config import ProviderAccount

    with pytest.raises(ValidationError):
        ProviderAccount(
            id="",
            display_name="Bad",
            provider_key="openai",
            kind="api",
        )


def test_provider_account_rejects_empty_display_name() -> None:
    from ivo.model_services.provider_config import ProviderAccount

    with pytest.raises(ValidationError):
        ProviderAccount(
            id="acct-1",
            display_name="",
            provider_key="openai",
            kind="api",
        )


def test_stage_provider_config_rejects_unknown_stage() -> None:
    from ivo.model_services.provider_config import StageProviderConfig

    with pytest.raises(ValidationError):
        StageProviderConfig(
            id="stage-1",
            display_name="Bad Stage",
            provider_key="openai",
            kind="api",
            stage="invalid_stage",  # type: ignore[arg-type]
            protocol="openai_asr",
        )


def test_stage_provider_config_rejects_empty_protocol() -> None:
    from ivo.model_services.provider_config import StageProviderConfig

    with pytest.raises(ValidationError):
        StageProviderConfig(
            id="stage-1",
            display_name="No Protocol",
            provider_key="openai",
            kind="api",
            stage="asr",
            protocol="",
        )


def test_dubbing_scheme_requires_bindings() -> None:
    from ivo.model_services.provider_config import DubbingScheme

    # Empty bindings should be allowed (scheme with no stages configured)
    scheme = DubbingScheme(id="empty", display_name="Empty Scheme", bindings=[])
    assert scheme.bindings == []


def test_dubbing_scheme_rejects_empty_id() -> None:
    from ivo.model_services.provider_config import DubbingScheme

    with pytest.raises(ValidationError):
        DubbingScheme(id="", display_name="Bad", bindings=[])


def test_scheme_stage_binding_creation() -> None:
    from ivo.model_services.provider_config import SchemeStageBinding

    binding = SchemeStageBinding(
        stage="asr",
        stage_config_id="stage-openai-asr",
        execution_group="openai_combined",
    )
    assert binding.stage == "asr"
    assert binding.stage_config_id == "stage-openai-asr"
    assert binding.execution_group == "openai_combined"


def test_local_model_config_allows_none_account() -> None:
    from ivo.model_services.provider_config import StageProviderConfig

    local_config = StageProviderConfig(
        id="local-demucs",
        display_name="Demucs 本地",
        account_id=None,
        provider_key="demucs",
        kind="local",
        stage="separation",
        protocol="local_demucs",
        local_model_path="models/separation/demucs",
    )
    assert local_config.account_id is None
    assert local_config.kind == "local"


def test_provider_capability_creation() -> None:
    from ivo.model_services.provider_config import ProviderCapability

    cap = ProviderCapability(
        stage="asr",
        output_keys=["segments", "text"],
        can_merge_with=["diarization"],
    )
    assert cap.stage == "asr"
    assert "diarization" in cap.can_merge_with


def test_secret_ref_creation() -> None:
    from ivo.model_services.provider_config import SecretRef

    ref = SecretRef(id="secret-1", label="OpenAI API Key")
    assert ref.id == "secret-1"
