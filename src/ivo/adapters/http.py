from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from typing import Any, Literal

import httpx
from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment
from jsonpath_ng import parse  # type: ignore[import-untyped]
from pydantic import BaseModel, Field, field_validator

from ivo.adapters.base import AdapterContext, AdapterError, AdapterResult


class ApiAdapterProfile(BaseModel):
    id: str
    stage: str
    method: Literal["GET", "POST"]
    url: str
    headers: dict[str, str] = Field(default_factory=dict)
    request_template: dict[str, Any] = Field(default_factory=dict)
    response_mapping: dict[str, str] = Field(default_factory=dict)
    optional_response_keys: list[str] = Field(default_factory=list)
    timeout_seconds: int = 120
    file_upload_fields: dict[str, str] = Field(default_factory=dict)

    @field_validator("id", "stage", "url")
    @classmethod
    def require_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value cannot be empty")
        return value

    @field_validator("timeout_seconds")
    @classmethod
    def require_positive_timeout(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("timeout_seconds must be positive")
        return value


class HttpStageAdapter:
    def __init__(self, profile: ApiAdapterProfile, client: httpx.Client | None = None) -> None:
        self.profile = profile
        self.stage = profile.stage
        self.provider = profile.id
        self._client = client or httpx.Client()
        self._environment = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)

    def validate_config(self) -> None:
        self.profile.model_validate(self.profile.model_dump())

    def run(self, context: AdapterContext) -> AdapterResult:
        values = context.template_values()
        try:
            response = self._send_request(values)
            if response.status_code >= 400:
                return self._provider_error(response)
            return AdapterResult(
                stage=self.stage,
                provider=self.provider,
                ok=True,
                payload=self._map_response(response.json()),
            )
        except httpx.TimeoutException:
            return self._error("request timed out", retryable=True)
        except httpx.HTTPError as exc:
            return self._error(str(exc), retryable=True)
        except ValueError as exc:
            return self._error(str(exc), retryable=False)

    def _send_request(self, values: dict[str, Any]) -> httpx.Response:
        url = self._render_string(self.profile.url, values)
        headers = {
            key: self._render_string(value, values) for key, value in self.profile.headers.items()
        }
        body = self._render_value(self.profile.request_template, values)

        if self.profile.method == "GET":
            return self._client.get(
                url,
                headers=headers,
                params=body,
                timeout=self.profile.timeout_seconds,
            )

        if self.profile.file_upload_fields:
            return self._post_with_files(url, headers, body, values)

        return self._client.post(
            url,
            headers=headers,
            json=body,
            timeout=self.profile.timeout_seconds,
        )

    def _post_with_files(
        self,
        url: str,
        headers: dict[str, str],
        body: Any,
        values: dict[str, Any],
    ) -> httpx.Response:
        with ExitStack() as stack:
            files: dict[str, tuple[str, Any]] = {}
            for field_name, value_name in self.profile.file_upload_fields.items():
                path = Path(str(values[value_name]))
                handle = stack.enter_context(path.open("rb"))
                files[field_name] = (path.name, handle)
            return self._client.post(
                url,
                headers=headers,
                data=body if isinstance(body, dict) else None,
                files=files,
                timeout=self.profile.timeout_seconds,
            )

    def _map_response(self, response_json: Any) -> dict[str, Any]:
        mapped: dict[str, Any] = {}
        for output_key, expression in self.profile.response_mapping.items():
            matches = [match.value for match in parse(expression).find(response_json)]
            if not matches:
                if output_key in self.profile.optional_response_keys:
                    continue
                raise ValueError(f"response mapping did not match: {output_key}")
            mapped[output_key] = matches[0]
        return mapped

    def _provider_error(self, response: httpx.Response) -> AdapterResult:
        message = response.text[:500]
        return AdapterResult(
            stage=self.stage,
            provider=self.provider,
            ok=False,
            error=AdapterError(
                provider=self.provider,
                stage=self.stage,
                message=message,
                http_status=response.status_code,
                retryable=response.status_code == 429 or response.status_code >= 500,
            ),
        )

    def _error(self, message: str, *, retryable: bool) -> AdapterResult:
        return AdapterResult(
            stage=self.stage,
            provider=self.provider,
            ok=False,
            error=AdapterError(
                provider=self.provider,
                stage=self.stage,
                message=message,
                retryable=retryable,
            ),
        )

    def _render_value(self, value: Any, variables: dict[str, Any]) -> Any:
        if isinstance(value, str):
            return self._render_string(value, variables)
        if isinstance(value, list):
            return [self._render_value(item, variables) for item in value]
        if isinstance(value, dict):
            return {key: self._render_value(item, variables) for key, item in value.items()}
        return value

    def _render_string(self, template: str, variables: dict[str, Any]) -> str:
        return self._environment.from_string(template).render(**variables)
