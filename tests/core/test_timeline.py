from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_timeline_inserts_and_lists_segments_in_time_order(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment

    project = DubbingProject.create(
        tmp_path / "timeline.ivoproj",
        name="Timeline",
        source_language="ko",
        target_language="zh",
    )

    later = DubbingSegment(
        id="seg-002",
        start_ms=2_000,
        end_ms=3_000,
        speaker_id="speaker-1",
        source_language="ko",
        source_text="안녕",
        target_language="zh",
        target_text="你好",
        status="needs_review",
    )
    earlier = DubbingSegment(
        id="seg-001",
        start_ms=500,
        end_ms=1_200,
        speaker_id="speaker-1",
        source_language="ko",
        source_text="그래",
        target_language="zh",
        target_text="嗯",
        status="pending",
    )

    project.timeline.add_segment(later)
    project.timeline.add_segment(earlier)

    assert [segment.id for segment in project.timeline.list_segments()] == ["seg-001", "seg-002"]


def test_segment_rejects_invalid_time_range() -> None:
    from ivo.core.timeline import DubbingSegment

    with pytest.raises(ValidationError):
        DubbingSegment(
            id="bad",
            start_ms=1000,
            end_ms=1000,
            speaker_id="speaker-1",
            source_language="en",
            source_text="Hello",
            target_language="zh",
            target_text="你好",
            status="pending",
        )


def test_timeline_updates_editable_segment_fields(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment

    project = DubbingProject.create(
        tmp_path / "editable.ivoproj",
        name="Editable",
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
            source_text="Well, hi.",
            target_language="zh",
            target_text="你好。",
            status="needs_review",
        )
    )

    updated = project.timeline.update_segment(
        "seg-001",
        target_text="嗯，你好。",
        speaker_id="speaker-2",
        emotion="warm",
        style_prompt="soft, friendly",
        status="approved",
        quality_flags=["duration_ok"],
    )

    assert updated.target_text == "嗯，你好。"
    assert updated.speaker_id == "speaker-2"
    assert updated.emotion == "warm"
    assert updated.style_prompt == "soft, friendly"
    assert updated.status == "approved"
    assert updated.quality_flags == ["duration_ok"]

    reloaded = DubbingProject.load(project.path)
    assert reloaded.timeline.get_segment("seg-001") == updated


def test_speaker_profile_stores_reference_segments(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.speakers import SpeakerProfile

    project = DubbingProject.create(
        tmp_path / "speakers.ivoproj",
        name="Speakers",
        source_language="ja",
        target_language="zh",
    )

    project.speakers.upsert(
        SpeakerProfile(
            id="speaker-1",
            display_name="角色 A",
            reference_segment_ids=["seg-001"],
            preferred_tts_profile_id="f5-tts-local",
            notes="Use calm references.",
        )
    )

    loaded = project.speakers.get("speaker-1")
    reloaded = DubbingProject.load(project.path).speakers.get("speaker-1")

    assert loaded is not None
    assert loaded.display_name == "角色 A"
    assert loaded.reference_segment_ids == ["seg-001"]
    assert loaded.notes == "Use calm references."
    assert reloaded == loaded
