from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from ivo.core.jobs import JobStore
from ivo.core.settings import ProjectSettingsStore
from ivo.core.speakers import SpeakerProfileStore
from ivo.core.timeline import SourceLanguage, TargetLanguage, TimelineStore


class ProjectMetadata(BaseModel):
    name: str
    source_language: SourceLanguage
    target_language: TargetLanguage
    source_video_path: Path | None = None


class DubbingProject:
    def __init__(self, path: Path, metadata: ProjectMetadata) -> None:
        self.path = path
        self.name = metadata.name
        self.source_language = metadata.source_language
        self.target_language = metadata.target_language
        self.source_video_path = metadata.source_video_path
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
        source_video: Path | None = None,
    ) -> DubbingProject:
        path.mkdir(parents=True, exist_ok=False)
        for directory_name in ("assets", "work", "renders"):
            (path / directory_name).mkdir()

        metadata = ProjectMetadata(
            name=name,
            source_language=source_language,
            target_language=target_language,
            source_video_path=source_video,
        )
        (path / "project.json").write_text(
            metadata.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return cls(path, metadata)

    @classmethod
    def load(cls, path: Path) -> DubbingProject:
        metadata_path = path / "project.json"
        data = json.loads(metadata_path.read_text(encoding="utf-8"))
        return cls(path, ProjectMetadata.model_validate(data))
