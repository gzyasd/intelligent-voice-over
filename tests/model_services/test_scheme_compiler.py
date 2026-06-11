"""Tests for model_services scheme compiler."""

from __future__ import annotations

from unittest.mock import MagicMock


from ivo.model_services.provider_config import (
    DubbingScheme,
    ProviderAccount,
    SchemeStageBinding,
    StageProviderConfig,
)


def _make_openai_account() -> ProviderAccount:
    return ProviderAccount(
        id="acct-openai",
        display_name="Test OpenAI",
        provider_key="openai",
        kind="api",
        api_key_ref="secret-openai",
    )


def _make_asr_config(account_id: str) -> StageProviderConfig:
    return StageProviderConfig(
        id="stage-openai-asr",
        display_name="OpenAI ASR+Diar",
        account_id=account_id,
        provider_key="openai",
        kind="api",
        stage="asr",
        protocol="openai_diarize",
        model_name="gpt-4o-transcribe-diarize",
    )


def _make_diar_config(account_id: str) -> StageProviderConfig:
    return StageProviderConfig(
        id="stage-openai-asr",  # Same ID = same config for combined
        display_name="OpenAI ASR+Diar",
        account_id=account_id,
        provider_key="openai",
        kind="api",
        stage="diarization",
        protocol="openai_diarize",
        model_name="gpt-4o-transcribe-diarize",
    )


def _make_tts_config(account_id: str) -> StageProviderConfig:
    return StageProviderConfig(
        id="stage-openai-tts",
        display_name="OpenAI TTS",
        account_id=account_id,
        provider_key="openai",
        kind="api",
        stage="tts",
        protocol="openai_tts",
        model_name="gpt-4o-mini-tts",
    )


def _make_translation_config(account_id: str) -> StageProviderConfig:
    return StageProviderConfig(
        id="stage-openai-translation",
        display_name="OpenAI Translation",
        account_id=account_id,
        provider_key="openai",
        kind="api",
        stage="translation",
        protocol="openai_compatible_translation",
        model_name="gpt-4o-mini",
    )


def _make_scheme_with_bindings(
    configs: list[StageProviderConfig],
) -> DubbingScheme:
    bindings = [
        SchemeStageBinding(
            stage=config.stage,
            stage_config_id=config.id,
        )
        for config in configs
    ]
    return DubbingScheme(
        id="test-scheme",
        display_name="Test Scheme",
        bindings=bindings,
    )


def test_scheme_compiler_returns_compiled_adapters() -> None:
    from ivo.model_services.scheme_compiler import (
        CompiledPipelineAdapters,
        SchemeRuntimeCompiler,
    )

    account = _make_openai_account()
    asr_config = _make_asr_config(account.id)
    tts_config = _make_tts_config(account.id)
    translation_config = _make_translation_config(account.id)
    scheme = _make_scheme_with_bindings([asr_config, tts_config, translation_config])

    mock_registry = MagicMock()
    mock_config_store = MagicMock()
    mock_config_store.get.side_effect = lambda config_id: {
        asr_config.id: asr_config,
        tts_config.id: tts_config,
        translation_config.id: translation_config,
    }[config_id]
    mock_adapter_factory = MagicMock()

    compiler = SchemeRuntimeCompiler(
        registry=mock_registry,
        config_store=mock_config_store,
        adapter_factory=mock_adapter_factory,
    )
    compiled = compiler.compile(scheme)

    assert isinstance(compiled, CompiledPipelineAdapters)


def test_compiled_pipeline_adapters_has_expected_fields() -> None:
    from ivo.model_services.scheme_compiler import CompiledPipelineAdapters

    compiled = CompiledPipelineAdapters()
    assert compiled.separation is None
    assert compiled.asr is None
    assert compiled.diarization is None
    assert compiled.translation is None
    assert compiled.tts is None
    assert compiled.local_profiles is None
    assert compiled.skipped_stages == {}


def test_compiled_pipeline_adapters_skipped_stages_for_logging() -> None:
    from ivo.model_services.scheme_compiler import CompiledPipelineAdapters

    compiled = CompiledPipelineAdapters(
        skipped_stages={"diarization": "merged with ASR via combined adapter"},
    )
    assert "diarization" in compiled.skipped_stages
    assert "merged" in compiled.skipped_stages["diarization"]


def test_detect_combined_adapter_returns_none_when_no_diar_config() -> None:
    from ivo.model_services.scheme_compiler import _detect_combined

    asr_config = _make_asr_config("acct-1")
    result = _detect_combined(asr_config, None)
    assert result is False


def test_detect_combined_adapter_returns_none_when_different_ids() -> None:
    from ivo.model_services.scheme_compiler import _detect_combined

    asr_config = _make_asr_config("acct-1")
    diar_config = StageProviderConfig(
        id="stage-different-diar",
        display_name="Different Diar",
        account_id="acct-1",
        provider_key="deepgram",
        kind="api",
        stage="diarization",
        protocol="deepgram_diarize",
    )
    result = _detect_combined(asr_config, diar_config)
    assert result is False


def test_detect_combined_adapter_returns_combined_for_matching_openai() -> None:
    from ivo.model_services.scheme_compiler import _detect_combined

    asr_config = _make_asr_config("acct-1")
    diar_config = _make_diar_config("acct-1")

    result = _detect_combined(asr_config, diar_config)
    assert result is True
