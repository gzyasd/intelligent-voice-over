"""Alibaba Cloud Qwen-TTS provider adapter.

Supports qwen3-tts-flash and other Qwen-TTS models via DashScope API.
Non-streaming mode: returns audio file URL, needs download.
Implements TtsAdapter protocol for the pipeline.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from ivo.model_services.adapters.base import ConnectionValidationResult


class AlibabaQwenTtsProvider:
    """Provider adapter for Alibaba Cloud Qwen-TTS API."""

    BASE_URL = "https://dashscope.aliyuncs.com/api/v1"

    def __init__(
        self,
        *,
        api_key: str,
        model_name: str = "qwen3-tts-flash",
        voice: str = "Cherry",
        language_type: str = "zh",
        config_id: str = "",
    ) -> None:
        self.provider_id = "alibaba_qwen_tts"
        self.stage = "tts"
        self.protocol = "alibaba_qwen_tts"
        self._api_key = api_key
        self._model_name = model_name
        self._voice = voice
        self._language_type = language_type
        self._config_id = config_id

    def validate_credentials(self) -> ConnectionValidationResult:
        """Validate by listing tasks."""
        try:
            response = httpx.get(
                f"{self.BASE_URL}/tasks",
                headers={"Authorization": f"Bearer {self._api_key}"},
                params={"page_no": "1", "page_size": "1"},
                timeout=10.0,
            )
            if response.status_code == 200:
                return ConnectionValidationResult(
                    ok=True,
                    provider_id=self.provider_id,
                    stage=self.stage,
                    model_name=self._model_name,
                )
            if response.status_code in (401, 403):
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

    def to_pipeline_adapter(self) -> _AlibabaQwenTtsPipelineAdapter:
        """Return a pipeline-compatible TTS adapter."""
        return _AlibabaQwenTtsPipelineAdapter(self)


class _AlibabaQwenTtsPipelineAdapter:
    """Implements TtsAdapter protocol for Alibaba Qwen-TTS."""

    def __init__(self, provider: AlibabaQwenTtsProvider) -> None:
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
    ) -> int:
        response = httpx.post(
            f"{self._provider.BASE_URL}/services/aigc/multimodal-generation/generation",
            headers={
                "Authorization": f"Bearer {self._provider._api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._provider._model_name,
                "input": {
                    "text": text,
                    "voice": self._provider._voice,
                    "language_type": self._provider._language_type,
                    "format": "wav",
                },
            },
            timeout=120.0,
        )
        response.raise_for_status()
        data = response.json()

        # Non-streaming: response contains audio URL
        audio_url = data.get("output", {}).get("audio_url", "")
        if audio_url:
            audio_response = httpx.get(audio_url, timeout=120.0)
            audio_response.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(audio_response.content)
        elif response.headers.get("content-type", "").startswith("audio/"):
            # Streaming: response body is audio data
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
        else:
            raise RuntimeError(
                f"Qwen-TTS did not return audio data or URL. Response: {data}"
            )

        from ivo.model_services.adapters.openai_tts import _estimate_wav_duration_ms
        return _estimate_wav_duration_ms(output_path)
