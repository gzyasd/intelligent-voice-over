from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field


class AdapterContext(BaseModel):
    project_path: Path
    segment_text: str
    source_language: str
    target_language: str
    speaker_id: str
    reference_audio_path: Path | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    def template_values(self) -> dict[str, Any]:
        values: dict[str, Any] = {
            "project_path": str(self.project_path),
            "segment_text": self.segment_text,
            "source_language": self.source_language,
            "target_language": self.target_language,
            "speaker_id": self.speaker_id,
            "reference_audio_path": (
                str(self.reference_audio_path) if self.reference_audio_path is not None else ""
            ),
        }
        values.update(self.extra)
        return values


class AdapterError(BaseModel):
    provider: str
    stage: str
    message: str
    http_status: int | None = None
    retryable: bool = False


class AdapterResult(BaseModel):
    stage: str
    provider: str
    ok: bool
    payload: dict[str, Any] = Field(default_factory=dict)
    error: AdapterError | None = None


class StageAdapter(Protocol):
    stage: str
    provider: str

    def validate_config(self) -> None: ...

    def run(self, context: AdapterContext) -> AdapterResult: ...


class MockStageAdapter:
    def __init__(self, *, stage: str, payload: dict[str, Any], provider: str = "mock") -> None:
        self.stage = stage
        self.provider = provider
        self.payload = payload

    def validate_config(self) -> None:
        return None

    def run(self, context: AdapterContext) -> AdapterResult:
        return AdapterResult(
            stage=self.stage,
            provider=self.provider,
            ok=True,
            payload=self.payload,
        )
