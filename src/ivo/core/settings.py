from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ivo.core.project import DubbingProject

ProcessingMode = Literal["fast_preview", "high_quality_export"]


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
