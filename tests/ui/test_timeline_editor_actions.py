from __future__ import annotations


def test_timeline_editor_save_button_persists_row(qtbot, tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.ui.timeline_editor import TimelineEditor

    project = DubbingProject.create(
        tmp_path / "timeline-actions.ivoproj",
        name="Timeline Actions",
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
    editor.table.item(0, editor.COLUMN_TARGET_TEXT).setText("嗯，你好。")
    editor.table.item(0, editor.COLUMN_STATUS).setText("approved")

    editor.save_buttons[0].click()

    reloaded = project.timeline.get_segment("seg-001")
    assert reloaded.target_text == "嗯，你好。"
    assert reloaded.status == "approved"


def test_timeline_editor_regenerate_button_emits_segment_id(qtbot, tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.ui.timeline_editor import TimelineEditor

    project = DubbingProject.create(
        tmp_path / "timeline-regenerate.ivoproj",
        name="Timeline Regenerate",
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
            status="rendered",
        )
    )
    emitted: list[str] = []

    editor = TimelineEditor()
    qtbot.addWidget(editor)
    editor.regenerate_requested.connect(emitted.append)
    editor.set_project(project)

    editor.regenerate_buttons[0].click()

    assert emitted == ["seg-001"]
