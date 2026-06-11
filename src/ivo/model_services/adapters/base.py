"""Provider adapter base protocols for model services."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class ConnectionValidationResult(BaseModel):
    """Result of credential validation."""

    ok: bool
    provider_id: str
    stage: str
    model_name: str | None = None
    latency_ms: int | None = None
    error_message: str | None = None
    error_code: str | None = None


@runtime_checkable
class ProviderAdapter(Protocol):
    """Base protocol for all provider adapters."""

    provider_id: str
    stage: str
    protocol: str

    def validate_credentials(self) -> ConnectionValidationResult: ...

    def to_pipeline_adapter(self) -> Any: ...
