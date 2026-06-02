from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SegmentStatusValue = Literal[
    "pending",
    "running",
    "needs_review",
    "approved",
    "failed",
    "rendered",
]
SourceLanguage = Literal["en", "ja", "ko"]
TargetLanguage = Literal["zh"]
ModelStage = Literal["separation", "asr", "diarization", "translation", "tts", "export"]
ModelBackend = Literal["local", "http", "mock"]


class DubbingSegment(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    id: str
    start_ms: int
    end_ms: int
    speaker_id: str
    source_language: SourceLanguage
    source_text: str
    target_language: TargetLanguage
    target_text: str
    emotion: str | None = None
    style_prompt: str | None = None
    status: SegmentStatusValue
    quality_flags: list[str] = Field(default_factory=list)

    @field_validator("id", "speaker_id")
    @classmethod
    def require_non_empty_identifier(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("identifier cannot be empty")
        return value

    @field_validator("start_ms", "end_ms")
    @classmethod
    def require_non_negative_time(cls, value: int) -> int:
        if value < 0:
            raise ValueError("timestamp cannot be negative")
        return value

    @model_validator(mode="after")
    def require_ordered_time_range(self) -> DubbingSegment:
        if self.end_ms <= self.start_ms:
            raise ValueError("end_ms must be greater than start_ms")
        return self


class SpeakerProfile(BaseModel):
    id: str
    display_name: str
    reference_segment_ids: list[str] = Field(default_factory=list)
    voice_embedding_path: str | None = None
    preferred_tts_profile_id: str | None = None


class ModelProfile(BaseModel):
    id: str
    stage: ModelStage
    backend: ModelBackend
    name: str
    config: dict[str, Any] = Field(default_factory=dict)


class TimelineStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._initialize()

    def add_segment(self, segment: DubbingSegment) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO segments (
                    id, start_ms, end_ms, speaker_id, source_language, source_text,
                    target_language, target_text, emotion, style_prompt, status, quality_flags
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._to_row(segment),
            )

    def get_segment(self, segment_id: str) -> DubbingSegment:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM segments WHERE id = ?",
                (segment_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"segment not found: {segment_id}")
        return self._from_row(row)

    def list_segments(self) -> list[DubbingSegment]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM segments ORDER BY start_ms ASC, end_ms ASC, id ASC"
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def update_segment(self, segment_id: str, **changes: Any) -> DubbingSegment:
        allowed_fields = {
            "target_text",
            "speaker_id",
            "emotion",
            "style_prompt",
            "status",
            "quality_flags",
        }
        unknown_fields = set(changes) - allowed_fields
        if unknown_fields:
            joined = ", ".join(sorted(unknown_fields))
            raise ValueError(f"cannot update fields: {joined}")

        current = self.get_segment(segment_id)
        updated = current.model_copy(update=changes)
        updated = DubbingSegment.model_validate(updated.model_dump())

        with self._connect() as connection:
            connection.execute(
                """
                UPDATE segments
                SET speaker_id = ?, target_text = ?, emotion = ?, style_prompt = ?,
                    status = ?, quality_flags = ?
                WHERE id = ?
                """,
                (
                    updated.speaker_id,
                    updated.target_text,
                    updated.emotion,
                    updated.style_prompt,
                    updated.status,
                    json.dumps(updated.quality_flags, ensure_ascii=False),
                    updated.id,
                ),
            )
        return updated

    def _initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS segments (
                    id TEXT PRIMARY KEY,
                    start_ms INTEGER NOT NULL,
                    end_ms INTEGER NOT NULL,
                    speaker_id TEXT NOT NULL,
                    source_language TEXT NOT NULL,
                    source_text TEXT NOT NULL,
                    target_language TEXT NOT NULL,
                    target_text TEXT NOT NULL,
                    emotion TEXT,
                    style_prompt TEXT,
                    status TEXT NOT NULL,
                    quality_flags TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _to_row(segment: DubbingSegment) -> tuple[object, ...]:
        return (
            segment.id,
            segment.start_ms,
            segment.end_ms,
            segment.speaker_id,
            segment.source_language,
            segment.source_text,
            segment.target_language,
            segment.target_text,
            segment.emotion,
            segment.style_prompt,
            segment.status,
            json.dumps(segment.quality_flags, ensure_ascii=False),
        )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> DubbingSegment:
        return DubbingSegment(
            id=row["id"],
            start_ms=row["start_ms"],
            end_ms=row["end_ms"],
            speaker_id=row["speaker_id"],
            source_language=row["source_language"],
            source_text=row["source_text"],
            target_language=row["target_language"],
            target_text=row["target_text"],
            emotion=row["emotion"],
            style_prompt=row["style_prompt"],
            status=row["status"],
            quality_flags=json.loads(row["quality_flags"]),
        )
