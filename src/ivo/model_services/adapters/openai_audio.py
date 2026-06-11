"""OpenAI ASR / ASR+diarization provider adapter.

Supports:
- gpt-4o-transcribe / gpt-4o-mini-transcribe (text only, no segments)
- gpt-4o-transcribe-diarize (ASR + speaker diarization)
- whisper-1 (verbose_json with segment timestamps)
"""

from __future__ import annotations

import io
import wave
from pathlib import Path
from typing import Any

import httpx

from ivo.core.timeline import SourceLanguage
from ivo.model_services.adapters.base import ConnectionValidationResult
from ivo.pipeline.transcribe import DiarizationSegment, TranscriptionSegment


class OpenAIAudioProvider:
    """Provider adapter for OpenAI audio transcription APIs."""

    def __init__(
        self,
        *,
        base_url: str = "https://api.openai.com",
        api_key: str,
        model_name: str = "gpt-4o-transcribe",
        config_id: str = "",
        protocol: str = "openai_asr",
    ) -> None:
        self.provider_id = "openai"
        self.stage = "asr"
        self.protocol = protocol
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model_name = model_name
        self._config_id = config_id

    # -- ProviderAdapter protocol --

    def validate_credentials(self) -> ConnectionValidationResult:
        """Validate by sending a minimal transcription request."""
        try:
            audio_bytes = _generate_silence_wav(duration_s=1)
            files = {"file": ("silence.wav", audio_bytes, "audio/wav")}
            data: dict[str, str] = {"model": self._model_name}
            if self._is_diarize_model():
                data["response_format"] = "diarized_json"
                data["chunking_strategy"] = "auto"
            response = httpx.post(
                f"{self._base_url}/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                files=files,
                data=data,
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
            if response.status_code == 429:
                return ConnectionValidationResult(
                    ok=True,
                    provider_id=self.provider_id,
                    stage=self.stage,
                    model_name=self._model_name,
                    error_message="Rate limited during validation",
                    error_code="RATE_LIMITED",
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

    def to_pipeline_adapter(self) -> _OpenAIAsrPipelineAdapter:
        """Return a pipeline-compatible ASR adapter."""
        return _OpenAIAsrPipelineAdapter(self)

    # -- Internal helpers --

    def _is_diarize_model(self) -> bool:
        return "diarize" in self._model_name

    def _transcribe_request(
        self, audio_path: Path, source_language: SourceLanguage
    ) -> dict[str, Any]:
        """Send transcription request and return parsed JSON response."""
        audio_bytes = audio_path.read_bytes()
        files = {"file": (audio_path.name, audio_bytes, "audio/wav")}
        data: dict[str, str] = {
            "model": self._model_name,
            "language": source_language,
        }

        if self._is_diarize_model():
            data["response_format"] = "diarized_json"
            data["chunking_strategy"] = "auto"
        elif self._model_name == "whisper-1":
            data["response_format"] = "verbose_json"
            data["timestamp_granularities[]"] = "segment"
        else:
            data["response_format"] = "json"

        response = httpx.post(
            f"{self._base_url}/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            files=files,
            data=data,
            timeout=120.0,
        )
        response.raise_for_status()
        return response.json()  # type: ignore[no-any-return]


class _OpenAIAsrPipelineAdapter:
    """Implements AsrAdapter protocol for OpenAI audio transcription."""

    def __init__(self, provider: OpenAIAudioProvider) -> None:
        self._provider = provider

    def transcribe(
        self, audio_path: Path, *, source_language: SourceLanguage
    ) -> list[TranscriptionSegment]:
        if not audio_path.is_file():
            raise FileNotFoundError(audio_path)
        response = self._provider._transcribe_request(audio_path, source_language)
        if self._provider._is_diarize_model():
            asr_segments, _ = _parse_diarized(response, source_language)
            return asr_segments
        return _parse_segments(response, source_language)


class _OpenAIDiarizationPipelineAdapter:
    """Implements DiarizationAdapter protocol using cached diarization results."""

    def __init__(self, provider: OpenAIAudioProvider) -> None:
        self._provider = provider
        self._cached_diarization: list[DiarizationSegment] | None = None

    def set_cached_diarization(self, segments: list[DiarizationSegment]) -> None:
        self._cached_diarization = segments

    def diarize(self, audio_path: Path) -> list[DiarizationSegment]:
        if self._cached_diarization is not None:
            return self._cached_diarization
        # If no cache, perform a fresh diarization request
        if not audio_path.is_file():
            raise FileNotFoundError(audio_path)
        response = self._provider._transcribe_request(audio_path, "en")
        _, diar_segments = _parse_diarized(response, "en")
        return diar_segments


def _parse_segments(
    response: dict[str, Any],
    source_language: SourceLanguage,
) -> list[TranscriptionSegment]:
    """Parse whisper-1 verbose_json or fallback single-text response."""
    segments = response.get("segments", [])
    if segments:
        return [
            TranscriptionSegment(
                id=str(seg.get("id", i)),
                start_ms=int(seg["start"] * 1000),
                end_ms=int(seg["end"] * 1000),
                source_language=source_language,
                source_text=seg["text"].strip(),
                speaker_id=str(seg.get("speaker", "unknown")),
            )
            for i, seg in enumerate(segments)
        ]
    # gpt-4o-transcribe fallback: no segments, return single entry
    duration_ms = int(response.get("duration", 0) * 1000)
    return [
        TranscriptionSegment(
            id="0",
            start_ms=0,
            end_ms=max(duration_ms, 1),
            source_language=source_language,
            source_text=response.get("text", "").strip(),
        )
    ]


def _parse_diarized(
    response: dict[str, Any],
    source_language: SourceLanguage,
) -> tuple[list[TranscriptionSegment], list[DiarizationSegment]]:
    """Parse gpt-4o-transcribe-diarize diarized_json response."""
    asr_segments: list[TranscriptionSegment] = []
    diar_segments: list[DiarizationSegment] = []
    transcript_segments = response.get("segments", [])
    for i, seg in enumerate(transcript_segments):
        speaker = seg.get("speaker", "unknown")
        start_ms = int(seg["start"] * 1000)
        end_ms = int(seg["end"] * 1000)
        asr_segments.append(
            TranscriptionSegment(
                id=str(i),
                start_ms=start_ms,
                end_ms=end_ms,
                source_language=source_language,
                source_text=seg["text"].strip(),
                speaker_id=speaker,
            )
        )
        diar_segments.append(
            DiarizationSegment(
                start_ms=start_ms,
                end_ms=end_ms,
                speaker_id=speaker,
            )
        )
    return asr_segments, diar_segments


def _generate_silence_wav(duration_s: int = 1) -> bytes:
    """Generate a minimal silent WAV file for validation."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 16000 * duration_s)
    return buf.getvalue()
