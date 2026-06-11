"""Scheme runtime compiler: converts DubbingScheme into pipeline Protocol adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from ivo.model_services.combined_asr import (
    CombinedAsrPipelineAdapter,
    CombinedAsrResultCache,
    CombinedDiarizationPipelineAdapter,
)
from ivo.model_services.provider_config import (
    DubbingScheme,
    StageProviderConfig,
)


@runtime_checkable
class SeparationAdapter(Protocol):
    def separate(
        self,
        input_audio: Any,
        *,
        vocals_path: Any,
        background_path: Any,
    ) -> Any: ...


@runtime_checkable
class AsrAdapter(Protocol):
    def transcribe(self, audio_path: Any, *, source_language: Any) -> Any: ...


@runtime_checkable
class DiarizationAdapter(Protocol):
    def diarize(self, audio_path: Any) -> Any: ...


@runtime_checkable
class TranslationAdapter(Protocol):
    def translate(self, segment: Any, *, prompt: str) -> Any: ...


@runtime_checkable
class TtsAdapter(Protocol):
    def synthesize(
        self,
        *,
        text: str,
        speaker_id: str,
        output_path: Any,
        style_prompt: str | None,
        reference_audio_path: Any | None,
        reference_text: str,
        target_duration_ms: int,
    ) -> int: ...


@dataclass
class CompiledPipelineAdapters:
    """Compiled pipeline adapter collection ready for injection into the pipeline."""

    separation: Any | None = None
    asr: Any | None = None
    diarization: Any | None = None
    translation: Any | None = None
    tts: Any | None = None

    # Local command profiles (kept for backward compatibility)
    local_profiles: Any | None = None

    # Record skipped stages (for logging/UI only, not passed to pipeline directly)
    skipped_stages: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class ProviderAdapterFactory(Protocol):
    def create(self, config: StageProviderConfig) -> Any: ...


@runtime_checkable
class ProviderRegistry(Protocol):
    def get(self, provider_id: str) -> Any | None: ...

    def list_all(self) -> list[Any]: ...


@runtime_checkable
class StageProviderConfigStore(Protocol):
    def get(self, config_id: str) -> StageProviderConfig: ...


# Protocols that support combined ASR + diarization
_COMBINED_PROTOCOLS = frozenset({"openai_diarize", "deepgram_diarize"})


def _detect_combined(
    asr_config: StageProviderConfig | None,
    diar_config: StageProviderConfig | None,
) -> bool:
    """Detect if ASR and diarization should use a combined adapter."""
    if not asr_config or not diar_config:
        return False
    if asr_config.id != diar_config.id:
        return False
    return asr_config.protocol in _COMBINED_PROTOCOLS


class SchemeRuntimeCompiler:
    """Compile a DubbingScheme into pipeline-ready adapters."""

    def __init__(
        self,
        *,
        registry: ProviderRegistry,
        config_store: StageProviderConfigStore,
        adapter_factory: ProviderAdapterFactory,
    ) -> None:
        self._registry = registry
        self._config_store = config_store
        self._adapter_factory = adapter_factory

    def compile(self, scheme: DubbingScheme) -> CompiledPipelineAdapters:
        """Compile scheme bindings into pipeline Protocol adapters."""
        compiled = CompiledPipelineAdapters()

        # Load configs for each binding
        configs_by_stage: dict[str, StageProviderConfig] = {}
        for binding in scheme.bindings:
            config = self._config_store.get(binding.stage_config_id)
            configs_by_stage[binding.stage] = config

        # Detect combined ASR + diarization
        asr_config = configs_by_stage.get("asr")
        diar_config = configs_by_stage.get("diarization")
        use_combined = _detect_combined(asr_config, diar_config)

        # Shared cache for combined ASR + diarization
        combined_cache: CombinedAsrResultCache | None = (
            CombinedAsrResultCache() if use_combined else None
        )

        # Build adapters per stage
        for stage_name, config in configs_by_stage.items():
            adapter = self._adapter_factory.create(config)

            if stage_name == "separation":
                compiled.separation = adapter
            elif stage_name == "asr":
                if combined_cache is not None:
                    compiled.asr = CombinedAsrPipelineAdapter(
                        adapter, combined_cache
                    )
                else:
                    compiled.asr = adapter
            elif stage_name == "diarization":
                if combined_cache is not None:
                    compiled.diarization = CombinedDiarizationPipelineAdapter(
                        combined_cache
                    )
                    compiled.skipped_stages["diarization"] = (
                        "merged with ASR via combined adapter"
                    )
                else:
                    compiled.diarization = adapter
            elif stage_name == "translation":
                compiled.translation = adapter
            elif stage_name == "tts":
                compiled.tts = adapter

        return compiled
