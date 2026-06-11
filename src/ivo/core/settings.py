from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from ivo.core.project import DubbingProject

ProcessingMode = Literal["fast_preview", "high_quality_export"]
SeriesType = Literal["american_drama", "japanese_drama", "korean_drama", "other"]


class TranslationSettings(BaseModel):
    series_type: SeriesType = "other"
    translation_style_notes: str = ""
    glossary: dict[str, str] = Field(default_factory=dict)
    preserve_fillers: bool = True
    max_length_ratio: float = 1.2

    @field_validator("max_length_ratio")
    @classmethod
    def require_positive_length_ratio(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("max_length_ratio must be positive")
        return value


class ProfileSelectionSettings(BaseModel):
    local_model_path: str = ""
    local_command_profiles_path: str = ""
    separation_profile_path: str = ""
    asr_profile_path: str = ""
    diarization_profile_path: str = ""
    translation_profile_path: str = ""
    tts_profile_path: str = ""


class ProjectSettings(BaseModel):
    translation: TranslationSettings = Field(default_factory=TranslationSettings)
    profiles: ProfileSelectionSettings = Field(default_factory=ProfileSelectionSettings)


class ProjectSettingsStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> ProjectSettings:
        if not self.path.is_file():
            return ProjectSettings()
        return ProjectSettings.model_validate(json.loads(self.path.read_text(encoding="utf-8")))

    def save(self, settings: ProjectSettings) -> ProjectSettings:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(settings.model_dump_json(indent=2), encoding="utf-8")
        return settings

    def update_translation(self, translation: TranslationSettings) -> ProjectSettings:
        settings = self.load()
        updated = settings.model_copy(update={"translation": translation})
        return self.save(updated)

    def update_profiles(self, profiles: ProfileSelectionSettings) -> ProjectSettings:
        settings = self.load()
        updated = settings.model_copy(update={"profiles": profiles})
        return self.save(updated)


class ProcessingProfile(BaseModel):
    mode: ProcessingMode
    asr_quality: Literal["fast", "high"]
    translation_quality: Literal["fast", "high"]
    tts_quality: Literal["fast", "high"]
    requires_approved_segments: bool
    duration_tolerance_ms: int


PROFILES: dict[ProcessingMode, ProcessingProfile] = {
    "fast_preview": ProcessingProfile(
        mode="fast_preview",
        asr_quality="fast",
        translation_quality="fast",
        tts_quality="fast",
        requires_approved_segments=False,
        duration_tolerance_ms=600,
    ),
    "high_quality_export": ProcessingProfile(
        mode="high_quality_export",
        asr_quality="high",
        translation_quality="high",
        tts_quality="high",
        requires_approved_segments=True,
        duration_tolerance_ms=300,
    ),
}


def get_processing_profile(mode: ProcessingMode) -> ProcessingProfile:
    return PROFILES[mode]


def validate_project_for_profile(
    project: DubbingProject,
    profile: ProcessingProfile,
) -> None:
    if not profile.requires_approved_segments:
        return

    invalid_segments = [
        segment.id
        for segment in project.timeline.list_segments()
        if segment.status not in {"approved", "rendered"}
    ]
    if invalid_segments:
        joined = ", ".join(invalid_segments)
        raise ValueError(f"segments must be approved before high-quality export: {joined}")
