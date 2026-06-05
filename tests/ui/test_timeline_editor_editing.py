from __future__ import annotations

import pytest


def test_timeline_editor_saves_editable_segment_fields(qtbot, tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.ui.timeline_editor import TimelineEditor

    project = DubbingProject.create(
        tmp_path / "timeline.ivoproj",
        name="Timeline",
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
            emotion="warm",
            style_prompt="warm and quiet",
            status="needs_review",
        )
    )
    editor = TimelineEditor()
    qtbot.addWidget(editor)
    editor.set_project(project)

    editor.table.item(0, editor.COLUMN_TARGET_TEXT).setText("嗯，你好。")
    editor.table.item(0, editor.COLUMN_EMOTION).setText("gentle")
    editor.table.item(0, editor.COLUMN_STYLE_PROMPT).setText("gentle but tense")
    editor.table.item(0, editor.COLUMN_STATUS).setText("approved")

    updated = editor.save_row(0)

    reloaded = project.timeline.get_segment("seg-001")
    assert updated.target_text == "嗯，你好。"
    assert reloaded.target_text == "嗯，你好。"
    assert reloaded.emotion == "gentle"
    assert reloaded.style_prompt == "gentle but tense"
    assert reloaded.status == "approved"


def test_timeline_editor_rejects_invalid_status(qtbot, tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.ui.timeline_editor import TimelineEditor

    project = DubbingProject.create(
        tmp_path / "timeline-invalid.ivoproj",
        name="Timeline Invalid",
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
    editor = TimelineEditor()
    qtbot.addWidget(editor)
    editor.set_project(project)
    editor.table.item(0, editor.COLUMN_STATUS).setText("not-a-status")

    with pytest.raises(ValueError, match="invalid segment status"):
        editor.save_row(0)


def test_timeline_editor_summarizes_quality_flags(qtbot, tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.ui.timeline_editor import TimelineEditor

    project = DubbingProject.create(
        tmp_path / "timeline-quality.ivoproj",
        name="Timeline Quality",
        source_language="en",
        target_language="zh",
    )
    for segment_id, flags in [
        ("seg-001", ["duration_mismatch", "speaker_unmatched"]),
        ("seg-002", ["duration_mismatch"]),
    ]:
        project.timeline.add_segment(
            DubbingSegment(
                id=segment_id,
                start_ms=0,
                end_ms=1_000,
                speaker_id="speaker-1",
                source_language="en",
                source_text="Hello.",
                target_language="zh",
                target_text="你好。",
                status="needs_review",
                quality_flags=flags,
            )
        )

    editor = TimelineEditor()
    qtbot.addWidget(editor)
    editor.set_project(project)

    assert editor.quality_summary_label.text() == (
        "质量摘要：duration_mismatch: 2; speaker_unmatched: 1"
    )


def test_timeline_editor_shows_readable_tts_quality_flags(qtbot, tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.ui.timeline_editor import TimelineEditor

    project = DubbingProject.create(
        tmp_path / "timeline-readable-quality.ivoproj",
        name="Timeline Readable Quality",
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
            quality_flags=["duration_too_short", "duration_too_long", "tts_retried"],
        )
    )

    editor = TimelineEditor()
    qtbot.addWidget(editor)
    editor.set_project(project)

    quality_text = editor.table.item(0, editor.COLUMN_QUALITY_FLAGS).text()
    assert "配音偏短" in quality_text
    assert "配音偏长" in quality_text
    assert "已自动重试" in quality_text


def test_timeline_editor_shows_empty_quality_summary(qtbot, tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.ui.timeline_editor import TimelineEditor

    project = DubbingProject.create(
        tmp_path / "timeline-quality-empty.ivoproj",
        name="Timeline Quality Empty",
        source_language="en",
        target_language="zh",
    )
    editor = TimelineEditor()
    qtbot.addWidget(editor)

    editor.set_project(project)

    assert editor.quality_summary_label.text() == "质量摘要：暂无质量问题"
