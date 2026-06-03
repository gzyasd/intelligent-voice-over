from __future__ import annotations

from pathlib import Path
from typing import Protocol

import httpx
from pydantic import BaseModel, field_validator, model_validator

from ivo.adapters.base import AdapterContext
from ivo.adapters.http import ApiAdapterProfile, HttpStageAdapter
from ivo.adapters.local import CommandRunner, LocalCommandAdapter, LocalCommandProfile
from ivo.core.timeline import SourceLanguage


class TranscriptionSegment(BaseModel):
    id: str
    start_ms: int
    end_ms: int
    source_language: SourceLanguage
    source_text: str
    speaker_id: str = "unknown"

    @field_validator("start_ms", "end_ms")
    @classmethod
    def require_non_negative_time(cls, value: int) -> int:
        if value < 0:
            raise ValueError("timestamp cannot be negative")
        return value

    @model_validator(mode="after")
    def require_ordered_time_range(self) -> TranscriptionSegment:
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be greater than start_ms")
        return self


class DiarizationSegment(BaseModel):
    start_ms: int
    end_ms: int
    speaker_id: str


class AsrAdapter(Protocol):
    def transcribe(self, audio_path: Path, *, source_language: SourceLanguage) -> list[TranscriptionSegment]:
        ...


class MockAsrAdapter:
    def __init__(self, segments: list[TranscriptionSegment]) -> None:
        self.segments = segments

    def transcribe(self, audio_path: Path, *, source_language: SourceLanguage) -> list[TranscriptionSegment]:
        if not audio_path.is_file():
            raise FileNotFoundError(audio_path)
        return [
            segment.model_copy(update={"source_language": source_language})
            for segment in self.segments
        ]


class LocalCommandAsrAdapter:
    def __init__(
        self,
        profile: LocalCommandProfile,
        *,
        runner: CommandRunner | None = None,
    ) -> None:
        self.profile = profile
        self.adapter = LocalCommandAdapter(profile, runner=runner)

    def transcribe(self, audio_path: Path, *, source_language: SourceLanguage) -> list[TranscriptionSegment]:
        if not audio_path.is_file():
            raise FileNotFoundError(audio_path)
        result = self.adapter.run(
            AdapterContext(
                project_path=audio_path.parent,
                segment_text="",
                source_language=source_language,
                target_language="zh",
                speaker_id="unknown",
                extra={"audio_path": str(audio_path)},
            )
        )
        if not result.ok:
            message = result.error.message if result.error is not None else "unknown ASR error"
            raise RuntimeError(f"{self.profile.id}: {message}")

        raw_segments = result.payload.get("segments")
        if not isinstance(raw_segments, list):
            raise RuntimeError(f"{self.profile.id}: ASR output missing segments list")

        segments: list[TranscriptionSegment] = []
        for index, raw_segment in enumerate(raw_segments):
            if not isinstance(raw_segment, dict):
                raise RuntimeError(f"{self.profile.id}: ASR segment must be an object")
            segments.append(
                TranscriptionSegment(
                    id=str(raw_segment.get("id", f"seg-{index + 1:03d}")),
                    start_ms=int(raw_segment["start_ms"]),
                    end_ms=int(raw_segment["end_ms"]),
                    source_language=source_language,
                    source_text=str(raw_segment.get("source_text", raw_segment.get("text", ""))),
                    speaker_id=str(raw_segment.get("speaker_id", "unknown")),
                )
            )
        return segments


class AsrProviderError(RuntimeError):
    """Raised when an ASR provider cannot produce normalized segments."""


class HttpAsrAdapter:
    def __init__(
        self,
        profile: ApiAdapterProfile,
        *,
        project_path: Path,
        client: httpx.Client | None = None,
        extra: dict[str, object] | None = None,
    ) -> None:
        self.profile = profile
        self.project_path = project_path
        self.extra = extra or {}
        self.adapter = HttpStageAdapter(profile, client=client)

    def transcribe(
        self,
        audio_path: Path,
        *,
        source_language: SourceLanguage,
    ) -> list[TranscriptionSegment]:
        if not audio_path.is_file():
            raise FileNotFoundError(audio_path)
        result = self.adapter.run(
            AdapterContext(
                project_path=self.project_path,
                segment_text="",
                source_language=source_language,
                target_language="zh",
                speaker_id="unknown",
                extra={"audio_path": str(audio_path), **self.extra},
            )
        )
        if not result.ok:
            message = result.error.message if result.error is not None else "unknown ASR error"
            raise AsrProviderError(f"{self.profile.id}: {message}")

        raw_segments = result.payload.get("segments")
        if not isinstance(raw_segments, list):
            raise AsrProviderError(f"{self.profile.id}: ASR output missing segments list")

        segments: list[TranscriptionSegment] = []
        for index, raw_segment in enumerate(raw_segments):
            if not isinstance(raw_segment, dict):
                raise AsrProviderError(f"{self.profile.id}: ASR segment must be an object")
            segments.append(
                TranscriptionSegment(
                    id=str(raw_segment.get("id", f"seg-{index + 1:03d}")),
                    start_ms=int(raw_segment["start_ms"]),
                    end_ms=int(raw_segment["end_ms"]),
                    source_language=source_language,
                    source_text=str(raw_segment.get("source_text", raw_segment.get("text", ""))),
                    speaker_id=str(raw_segment.get("speaker_id", "unknown")),
                )
            )
        return segments


def transcribe_audio(
    adapter: AsrAdapter,
    audio_path: Path,
    *,
    source_language: SourceLanguage,
) -> list[TranscriptionSegment]:
    return adapter.transcribe(audio_path, source_language=source_language)


def assign_speakers(
    segments: list[TranscriptionSegment],
    diarization_segments: list[DiarizationSegment],
) -> list[TranscriptionSegment]:
    assigned: list[TranscriptionSegment] = []
    for segment in segments:
        midpoint = segment.start_ms + ((segment.end_ms - segment.start_ms) // 2)
        speaker_id = segment.speaker_id
        for diarization in diarization_segments:
            if diarization.start_ms <= midpoint < diarization.end_ms:
                speaker_id = diarization.speaker_id
                break
        assigned.append(segment.model_copy(update={"speaker_id": speaker_id}))
    return assigned
