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


def test_timeline_editor_reference_button_stores_speaker_profile_segment(qtbot, tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.ui.timeline_editor import TimelineEditor

    project = DubbingProject.create(
        tmp_path / "timeline-reference.ivoproj",
        name="Timeline Reference",
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
            target_text="Hello.",
            status="approved",
        )
    )

    editor = TimelineEditor()
    qtbot.addWidget(editor)
    editor.set_project(project)

    editor.set_reference_buttons[0].click()

    profile = project.speakers.get("speaker-1")
    assert profile is not None
    assert profile.reference_segment_ids == ["seg-001"]


def test_timeline_editor_filters_duration_quality_flags(qtbot) -> None:
    from ivo.ui.timeline_editor import TimelineEditor

    editor = TimelineEditor()
    qtbot.addWidget(editor)
    editor.set_segments(
        [
            _segment("seg-001", quality_flags=["duration_too_long"]),
            _segment("seg-002", quality_flags=["duration_ok"]),
        ]
    )

    editor.set_quality_filter("duration_too_long")

    assert editor.visible_segment_ids() == ["seg-001"]


def test_timeline_editor_shows_review_summary(qtbot) -> None:
    from ivo.ui.timeline_editor import TimelineEditor

    editor = TimelineEditor()
    qtbot.addWidget(editor)

    editor.set_segments(
        [
            _segment("seg-001", status="approved", quality_flags=["duration_too_long"]),
            _segment("seg-002", status="rendered", quality_flags=[]),
        ]
    )

    assert "总片段：2" in editor.review_summary_label.text()
    assert "已审核：2" in editor.review_summary_label.text()
    assert "已生成：1" in editor.review_summary_label.text()
    assert "质量标记：1" in editor.review_summary_label.text()


def test_timeline_editor_hides_technical_columns_by_default(qtbot) -> None:
    from ivo.ui.timeline_editor import TimelineEditor

    editor = TimelineEditor()
    qtbot.addWidget(editor)

    assert editor.table.isColumnHidden(editor.COLUMN_ID) is True
    assert editor.table.isColumnHidden(editor.COLUMN_STYLE_PROMPT) is True
    assert editor.table.isColumnHidden(editor.COLUMN_QUALITY_FLAGS) is True


def test_timeline_editor_updates_readable_detail_panel_on_selection(qtbot) -> None:
    from ivo.ui.timeline_editor import TimelineEditor

    editor = TimelineEditor()
    qtbot.addWidget(editor)
    editor.set_segments(
        [
            _segment(
                "seg-001",
                source_text="Original line.",
                target_text="中文台词。",
                emotion="tense",
            )
        ]
    )

    editor.table.selectRow(0)

    assert "Original line." in editor.detail_source_label.text()
    assert "中文台词。" in editor.detail_target_label.text()
    assert "speaker-1" in editor.detail_speaker_label.text()
    assert "tense" in editor.detail_emotion_label.text()


def test_timeline_editor_displays_speaker_profile_name_without_changing_id(qtbot, tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.speakers import SpeakerProfile
    from ivo.core.timeline import DubbingSegment
    from ivo.ui.timeline_editor import TimelineEditor

    project = DubbingProject.create(
        tmp_path / "timeline-speaker-name.ivoproj",
        name="Timeline Speaker Name",
        source_language="en",
        target_language="zh",
    )
    project.speakers.upsert(SpeakerProfile(id="speaker-1", display_name="Hero A"))
    project.timeline.add_segment(
        DubbingSegment(
            id="seg-001",
            start_ms=0,
            end_ms=1_000,
            speaker_id="speaker-1",
            source_language="en",
            source_text="Well, hi.",
            target_language="zh",
            target_text="Hello.",
            status="needs_review",
        )
    )

    editor = TimelineEditor()
    qtbot.addWidget(editor)
    editor.set_project(project)
    editor.table.item(0, editor.COLUMN_TARGET_TEXT).setText("Hi.")

    updated = editor.save_row(0)

    assert editor.table.item(0, editor.COLUMN_SPEAKER).text() == "Hero A"
    assert updated.speaker_id == "speaker-1"


def _segment(
    segment_id: str,
    *,
    status: str = "needs_review",
    quality_flags: list[str] | None = None,
    source_text: str = "Hello.",
    target_text: str = "你好。",
    emotion: str | None = None,
):
    from ivo.core.timeline import DubbingSegment

    return DubbingSegment(
        id=segment_id,
        start_ms=0,
        end_ms=1_000,
        speaker_id="speaker-1",
        source_language="en",
        source_text=source_text,
        target_language="zh",
        target_text=target_text,
        emotion=emotion,
        status=status,
        quality_flags=quality_flags or [],
    )
