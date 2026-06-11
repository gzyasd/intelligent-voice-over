"""Deepgram ASR / ASR+diarization provider adapter.

Supports:
- Pre-recorded audio via POST /v1/listen
- diarize_model=latest for speaker diarization
- Word-level speaker tagging with segment grouping
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from ivo.core.timeline import SourceLanguage
from ivo.model_services.adapters.base import ConnectionValidationResult
from ivo.pipeline.transcribe import DiarizationSegment, TranscriptionSegment


# Word grouping: new segment on speaker change or >500ms gap
_GAP_THRESHOLD_S = 0.5


class DeepgramProvider:
    """Provider adapter for Deepgram pre-recorded transcription API."""

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = "nova-3",
        config_id: str = "",
        protocol: str = "deepgram_asr",
        diarize: bool = False,
    ) -> None:
        self.provider_id = "deepgram"
        self.stage = "asr"
        self.protocol = protocol
        self._api_key = api_key
        self._model_name = model_name
        self._config_id = config_id
        self._diarize = diarize

    # -- ProviderAdapter protocol --

    def validate_credentials(self) -> ConnectionValidationResult:
        """Validate by sending a minimal audio request."""
        try:
            from ivo.model_services.adapters.openai_audio import _generate_silence_wav

            audio_bytes = _generate_silence_wav(duration_s=1)
            params: dict[str, str] = {"model": self._model_name}
            if self._diarize:
                params["diarize_model"] = "latest"
            response = httpx.post(
                "https://api.deepgram.com/v1/listen",
                headers={
                    "Authorization": f"Token {self._api_key}",
                    "Content-Type": "audio/wav",
                },
                params=params,
                content=audio_bytes,
                timeout=30.0,
            )
            if response.status_code == 200:
                return ConnectionValidationResult(
                    ok=True,
                    provider_id=self.provider_id,
                    stage=self.stage,
                    model_name=self._model_name,
                )
            if response.status_code == 401:
                return ConnectionValidationResult(
                    ok=False,
                    provider_id=self.provider_id,
                    stage=self.stage,
                    error_message="Invalid API key",
                    error_code="AUTH_FAILED",
                )
            return ConnectionValidationResult(
                ok=False,
                provider_id=self.provider_id,
                stage=self.stage,
                error_message=f"HTTP {response.status_code}",
                error_code="CONNECTION_ERROR",
            )
        except httpx.HTTPError as exc:
            return ConnectionValidationResult(
                ok=False,
                provider_id=self.provider_id,
                stage=self.stage,
                error_message=str(exc)[:200],
                error_code="CONNECTION_ERROR",
            )

    def to_pipeline_adapter(self) -> _DeepgramAsrPipelineAdapter:
        """Return a pipeline-compatible ASR adapter."""
        return _DeepgramAsrPipelineAdapter(self)

    # -- Internal helpers --

    def _transcribe_request(
        self, audio_path: Path, source_language: SourceLanguage
    ) -> dict[str, Any]:
        """Send transcription request and return parsed JSON response."""
        audio_bytes = audio_path.read_bytes()
        params: dict[str, str] = {
            "model": self._model_name,
            "language": source_language,
            "smart_format": "true",
            "punctuate": "true",
        }
        if self._diarize:
            params["diarize_model"] = "latest"

        response = httpx.post(
            "https://api.deepgram.com/v1/listen",
            headers={
                "Authorization": f"Token {self._api_key}",
                "Content-Type": "audio/wav",
            },
            params=params,
            content=audio_bytes,
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]


class _DeepgramAsrPipelineAdapter:
    """Implements AsrAdapter protocol for Deepgram transcription."""

    def __init__(self, provider: DeepgramProvider) -> None:
        self._provider = provider

    def transcribe(
        self, audio_path: Path, *, source_language: SourceLanguage
    ) -> list[TranscriptionSegment]:
        if not audio_path.is_file():
            raise FileNotFoundError(audio_path)
        response = self._provider._transcribe_request(audio_path, source_language)
        asr_segments, _ = _parse_deepgram_response(response, source_language)
        return asr_segments


class _DeepgramDiarizationPipelineAdapter:
    """Implements DiarizationAdapter protocol using cached diarization results."""

    def __init__(self, provider: DeepgramProvider) -> None:
        self._provider = provider
        self._cached_diarization: list[DiarizationSegment] | None = None

    def set_cached_diarization(self, segments: list[DiarizationSegment]) -> None:
        self._cached_diarization = segments

    def diarize(self, audio_path: Path) -> list[DiarizationSegment]:
        if self._cached_diarization is not None:
            return self._cached_diarization
        if not audio_path.is_file():
            raise FileNotFoundError(audio_path)
        response = self._provider._transcribe_request(audio_path, "en")
        _, diar_segments = _parse_deepgram_response(response, "en")
        return diar_segments


def _parse_deepgram_response(
    response: dict[str, Any],
    source_language: SourceLanguage,
) -> tuple[list[TranscriptionSegment], list[DiarizationSegment]]:
    """Parse Deepgram word-level response into segments.

    Groups words by speaker changes and pauses (>500ms gap).
    """
    channels = response.get("results", {}).get("channels", [])
    if not channels:
        return [], []
    alternatives = channels[0].get("alternatives", [])
    if not alternatives:
        return [], []
    words = alternatives[0].get("words", [])
    if not words:
        return [], []

    # Group words into segments by speaker change or gap
    groups: list[list[dict[str, Any]]] = []
    current_group: list[dict[str, Any]] = []

    for word_info in words:
        if current_group:
            prev = current_group[-1]
            speaker_changed = word_info.get("speaker", 0) != prev.get("speaker", 0)
            gap = word_info.get("start", 0) - prev.get("end", 0)
            if speaker_changed or gap > _GAP_THRESHOLD_S:
                groups.append(current_group)
                current_group = []
        current_group.append(word_info)

    if current_group:
        groups.append(current_group)

    asr_segments: list[TranscriptionSegment] = []
    diar_segments: list[DiarizationSegment] = []

    for i, group in enumerate(groups):
        start_ms = int(group[0].get("start", 0) * 1000)
        end_ms = int(group[-1].get("end", 0) * 1000)
        text = " ".join(w.get("word", "") for w in group).strip()
        speaker_num = group[0].get("speaker", 0)
        speaker_id = f"speaker_{speaker_num}"

        if end_ms <= start_ms:
            end_ms = start_ms + 1

        asr_segments.append(
            TranscriptionSegment(
                id=str(i),
                start_ms=start_ms,
                end_ms=end_ms,
                source_language=source_language,
                source_text=text,
                speaker_id=speaker_id,
            )
        )
        diar_segments.append(
            DiarizationSegment(
                start_ms=start_ms,
                end_ms=end_ms,
                speaker_id=speaker_id,
            )
        )

    return asr_segments, diar_segments
