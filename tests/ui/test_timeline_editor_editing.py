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
