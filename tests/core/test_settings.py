from __future__ import annotations

import pytest


def test_processing_profiles_define_preview_and_final_export_modes() -> None:
    from ivo.core.settings import get_processing_profile

    preview = get_processing_profile("fast_preview")
    final = get_processing_profile("high_quality_export")

    assert preview.requires_approved_segments is False
    assert final.requires_approved_segments is True
    assert final.tts_quality == "high"


def test_unknown_processing_profile_is_rejected() -> None:
    from ivo.core.settings import get_processing_profile

    with pytest.raises(KeyError):
        get_processing_profile("unknown")


def test_high_quality_profile_requires_approved_or_rendered_segments(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.settings import get_processing_profile, validate_project_for_profile
    from ivo.core.timeline import DubbingSegment

    project = DubbingProject.create(
        tmp_path / "quality.ivoproj",
        name="Quality",
        source_language="en",
        target_language="zh",
    )
    project.timeline.add_segment(
        DubbingSegment(
            id="seg-001",
            start_ms=0,
            end_ms=1_000,
            speaker_id="speaker-1",
            source_language="en",
            source_text="Hello.",
            target_language="zh",
            target_text="你好。",
            status="needs_review",
        )
    )

    with pytest.raises(ValueError, match="seg-001"):
        validate_project_for_profile(project, get_processing_profile("high_quality_export"))

    validate_project_for_profile(project, get_processing_profile("fast_preview"))
    project.timeline.update_segment("seg-001", status="approved")
    validate_project_for_profile(project, get_processing_profile("high_quality_export"))
