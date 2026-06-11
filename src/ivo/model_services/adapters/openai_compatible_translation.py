"""OpenAI-compatible translation adapter provider module.

Wraps the existing HttpTranslationAdapter with StageProviderConfig-driven setup.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from ivo.adapters.http import ApiAdapterProfile
from ivo.model_services.adapters.base import ConnectionValidationResult
from ivo.pipeline.translate import HttpTranslationAdapter


class OpenAICompatibleTranslationProvider:
    """Provider adapter for OpenAI-compatible Chat Completions translation."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model_name: str = "gpt-4o-mini",
        config_id: str = "",
    ) -> None:
        self.provider_id = "openai_compatible"
        self.stage = "translation"
        self.protocol = "openai_compatible_translation"
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model_name = model_name
        self._config_id = config_id

    def validate_credentials(self) -> ConnectionValidationResult:
        """Validate by listing available models."""
        try:
            response = httpx.get(
                f"{self._base_url}/v1/models",
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=10.0,
            )
            if response.status_code == 200:
                return ConnectionValidationResult(
                    ok=True,
                    provider_id=self.provider_id,
                    stage=self.stage,
                    model_name=self._model_name,
                )
            return ConnectionValidationResult(
                ok=False,
                provider_id=self.provider_id,
                stage=self.stage,
                error_message=f"HTTP {response.status_code}",
                error_code="AUTH_FAILED" if response.status_code == 401 else None,
            )
        except httpx.HTTPError as exc:
            return ConnectionValidationResult(
                ok=False,
                provider_id=self.provider_id,
                stage=self.stage,
                error_message=str(exc)[:200],
                error_code="CONNECTION_ERROR",
            )

    def to_pipeline_adapter(self, *, project_path: Path = Path(".")) -> HttpTranslationAdapter:
        """Build an HttpTranslationAdapter for the pipeline."""
        profile = ApiAdapterProfile(
            id=f"openai_compatible_{self._config_id}",
            stage="translation",
            method="POST",
            url=f"{self._base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            request_template={
                "model": self._model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "请将以下 {{source_language}} 台词翻译成{{target_language}}自然中文。"
                            "要求：保留语气和情绪；适合配音口型。"
                            "输出JSON: target_text, emotion, style_prompt。"
                        ),
                    },
                    {"role": "user", "content": "{{segment_text}}"},
                ],
                "temperature": 0.3,
                "max_tokens": 1000,
            },
            response_mapping={"content_json": "$.choices[0].message.content"},
        )
        return HttpTranslationAdapter(profile=profile, project_path=project_path)
