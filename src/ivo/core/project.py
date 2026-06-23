from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, model_validator

from ivo.core.jobs import JobStore
from ivo.core.settings import ProjectSettingsStore
from ivo.core.speakers import SpeakerProfileStore
from ivo.core.timeline import SourceLanguage, TargetLanguage, TimelineStore


class ProjectMetadata(BaseModel):
    name: str
    source_language: SourceLanguage
    target_language: TargetLanguage
    content_type: Literal["video", "audio"] = "video"
    source_media_path: Path | None = None
    scheme_id: str | None = None
    # Backward compatibility: read old source_video_path if source_media_path is None
    source_video_path: Path | None = None
    generation_status: str = "not_started"
    generation_started_at: float | None = None
    generation_completed_at: float | None = None
    generation_elapsed_seconds: int | None = None

    @model_validator(mode="after")
    def _compatibility_source_media_path(self) -> ProjectMetadata:
        if self.source_media_path is None and self.source_video_path is not None:
            self.source_media_path = self.source_video_path
        return self


class DubbingProject:
    def __init__(self, path: Path, metadata: ProjectMetadata) -> None:
        self.path = path
        self.metadata = metadata
        self.name = metadata.name
        self.source_language = metadata.source_language
        self.target_language = metadata.target_language
        self.content_type = metadata.content_type
        self.source_media_path = metadata.source_media_path
        self.timeline = TimelineStore(path / "segments.sqlite")
        self.speakers = SpeakerProfileStore(path / "speakers.json")
        self.settings = ProjectSettingsStore(path / "settings.json")
        self.jobs = JobStore(path / "jobs.sqlite")

    @classmethod
    def create(
        cls,
        path: Path,
        *,
        name: str,
        source_language: SourceLanguage,
        target_language: TargetLanguage,
        content_type: Literal["video", "audio"] = "video",
        source_media: Path | None = None,
        scheme_id: str | None = None,
    ) -> DubbingProject:
        path.mkdir(parents=True, exist_ok=False)
        for directory_name in ("assets", "work", "renders"):
            (path / directory_name).mkdir()

        metadata = ProjectMetadata(
            name=name,
            source_language=source_language,
            target_language=target_language,
            content_type=content_type,
            source_media_path=source_media,
            scheme_id=scheme_id,
        )
        (path / "project.json").write_text(
            metadata.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8",
        )
        return cls(path, metadata)

    @classmethod
    def load(cls, path: Path) -> DubbingProject:
        metadata_path = path / "project.json"
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        return cls(path, ProjectMetadata.model_validate(data))

    def mark_generation_started(self, *, now: float | None = None) -> None:
        timestamp = time.time() if now is None else now
        self.metadata.generation_status = "running"
        self.metadata.generation_started_at = timestamp
        self.metadata.generation_completed_at = None
        self.metadata.generation_elapsed_seconds = None
        self._save_metadata()

    def mark_generation_completed(
        self,
        *,
        now: float | None = None,
        elapsed_seconds: int | None = None,
    ) -> None:
        self._finish_generation("completed", now=now, elapsed_seconds=elapsed_seconds)

    def mark_generation_failed(
        self,
        *,
        now: float | None = None,
        elapsed_seconds: int | None = None,
    ) -> None:
        self._finish_generation("failed", now=now, elapsed_seconds=elapsed_seconds)

    def _finish_generation(
        self,
        status: str,
        *,
        now: float | None = None,
        elapsed_seconds: int | None = None,
    ) -> None:
        timestamp = time.time() if now is None else now
        started_at = self.metadata.generation_started_at or timestamp
        self.metadata.generation_status = status
        self.metadata.generation_completed_at = timestamp
        elapsed = elapsed_seconds
        if elapsed is None:
            elapsed = round(timestamp - started_at)
        self.metadata.generation_elapsed_seconds = max(0, elapsed)
        self._save_metadata()

    def _save_metadata(self) -> None:
        (self.path / "project.json").write_text(
            self.metadata.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8",
        )
