"""ElevenLabs TTS provider adapter.

Supports text-to-speech with voice_id, model_id, and voice_settings.
Implements TtsAdapter protocol for the pipeline.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from ivo.model_services.adapters.base import ConnectionValidationResult


class ElevenLabsTtsProvider:
    """Provider adapter for ElevenLabs Text-to-Speech API."""

    BASE_URL = "https://api.elevenlabs.io"

    def __init__(
        self,
        *,
        api_key: str,
        voice_id: str = "",
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        config_id: str = "",
    ) -> None:
        self.provider_id = "elevenlabs"
        self.stage = "tts"
        self.protocol = "elevenlabs_tts"
        self._api_key = api_key
        self._voice_id = voice_id
        self._model_id = model_id
        self._stability = stability
        self._similarity_boost = similarity_boost
        self._config_id = config_id

    def validate_credentials(self) -> ConnectionValidationResult:
        """Validate by fetching user info."""
        try:
            response = httpx.get(
                f"{self.BASE_URL}/v1/user",
                headers={"xi-api-key": self._api_key},
                timeout=10.0,
            )
            if response.status_code == 200:
                return ConnectionValidationResult(
                    ok=True,
                    provider_id=self.provider_id,
                    stage=self.stage,
                    model_name=self._model_id,
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

    def to_pipeline_adapter(self) -> _ElevenLabsTtsPipelineAdapter:
        """Return a pipeline-compatible TTS adapter."""
        return _ElevenLabsTtsPipelineAdapter(self)


class _ElevenLabsTtsPipelineAdapter:
    """Implements TtsAdapter protocol for ElevenLabs TTS."""

    def __init__(self, provider: ElevenLabsTtsProvider) -> None:
        self._provider = provider

    def synthesize(
        self,
        *,
        text: str,
        speaker_id: str,
        output_path: Path,
        style_prompt: str | None,
        reference_audio_path: Path | None,
        reference_text: str,
        target_duration_ms: int,
        speech_rate: float = 1.0,
    ) -> int:
        voice_id = self._provider._voice_id or speaker_id
        response = httpx.post(
            f"{self._provider.BASE_URL}/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": self._provider._api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json={
                "text": text,
                "model_id": self._provider._model_id,
                "voice_settings": {
                    "stability": self._provider._stability,
                    "similarity_boost": self._provider._similarity_boost,
                },
            },
            timeout=120.0,
        )
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

        from ivo.model_services.adapters.openai_tts import _estimate_wav_duration_ms
        return _estimate_wav_duration_ms(output_path)
