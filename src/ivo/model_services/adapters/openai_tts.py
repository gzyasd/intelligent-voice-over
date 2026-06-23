"""OpenAI TTS provider adapter.

Supports gpt-4o-mini-tts, tts-1, tts-1-hd.
Implements TtsAdapter protocol for the pipeline.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from ivo.model_services.adapters.base import ConnectionValidationResult


class OpenAITtsProvider:
    """Provider adapter for OpenAI Text-to-Speech API."""

    def __init__(
        self,
        *,
        base_url: str = "https://api.openai.com",
        api_key: str,
        model_name: str = "gpt-4o-mini-tts",
        voice: str = "alloy",
        speed: float = 1.0,
        config_id: str = "",
    ) -> None:
        self.provider_id = "openai"
        self.stage = "tts"
        self.protocol = "openai_tts"
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model_name = model_name
        self._voice = voice
        self._speed = speed
        self._config_id = config_id

    def validate_credentials(self) -> ConnectionValidationResult:
        """Validate by sending a minimal TTS request."""
        try:
            response = httpx.post(
                f"{self._base_url}/v1/audio/speech",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self._model_name,
                    "input": "hi",
                    "voice": self._voice,
                    "response_format": "wav",
                },
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

    def to_pipeline_adapter(self) -> _OpenAITtsPipelineAdapter:
        """Return a pipeline-compatible TTS adapter."""
        return _OpenAITtsPipelineAdapter(self)


class _OpenAITtsPipelineAdapter:
    """Implements TtsAdapter protocol for OpenAI TTS."""

    def __init__(self, provider: OpenAITtsProvider) -> None:
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
        effective_speed = speech_rate if speech_rate > 0 else self._provider._speed
        response = httpx.post(
            f"{self._provider._base_url}/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {self._provider._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._provider._model_name,
                "input": text,
                "voice": self._provider._voice,
                "response_format": "wav",
                "speed": effective_speed,
            },
            timeout=120.0,
        )
        response.raise_for_status()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(response.content)

        # Return estimated duration from audio file
        return _estimate_wav_duration_ms(output_path)


def _estimate_wav_duration_ms(path: Path) -> int:
    """Estimate WAV file duration in milliseconds."""
    try:
        import wave as wave_module
        with wave_module.open(str(path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return int(frames / rate * 1000)
    except Exception:
        pass
    return 0
