from __future__ import annotations

import json


def test_main_window_regenerates_timeline_segment_from_local_tts_profile(
    monkeypatch,
    qtbot,
    tmp_path,
) -> None:
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import SynthesisResult
    from ivo.ui.main_window import MainWindow

    profiles_path = _write_local_profiles(tmp_path)
    captured: dict[str, object] = {}

    class FakeLocalCommandTtsAdapter:
        def __init__(self, profile) -> None:
            captured["profile"] = profile

    def fake_synthesize_segment(project, segment, adapter):
        captured["segment"] = segment
        captured["adapter"] = adapter
        audio_path = project.path / "work" / "generated_segments" / f"{segment.id}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(b"speech")
        project.timeline.update_segment(
            segment.id,
            status="rendered",
            quality_flags=["duration_ok"],
        )
        return SynthesisResult(
            segment_id=segment.id,
            audio_path=audio_path,
            generated_duration_ms=segment.end_ms - segment.start_ms,
            quality_flags=["duration_ok"],
        )

    monkeypatch.setattr(
        "ivo.ui.main_window.LocalCommandTtsAdapter",
        FakeLocalCommandTtsAdapter,
        raising=False,
    )
    monkeypatch.setattr(
        "ivo.ui.main_window.synthesize_segment",
        fake_synthesize_segment,
        raising=False,
    )

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    window = MainWindow()
    qtbot.addWidget(window)
    project = window.create_project_from_inputs(
        project_name="Episode 01",
        source_video=source,
        output_dir=tmp_path,
        source_language="en",
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
            target_text="\u4f60\u597d\u3002",
            emotion="warm",
            status="approved",
        )
    )
    window.model_settings.local_command_profiles_path_edit.setText(str(profiles_path))
    window.timeline_editor.set_project(project)
    window.timeline_editor.table.item(0, window.timeline_editor.COLUMN_TARGET_TEXT).setText(
        "\u55e8\uff0c\u4f60\u597d\u3002"
    )

    result = window.regenerate_timeline_segment("seg-001")

    reloaded = project.timeline.get_segment("seg-001")
    assert result is not None
    assert result.segment_id == "seg-001"
    assert captured["profile"].id == "tts"
    assert captured["segment"].id == "seg-001"
    assert captured["segment"].target_text == "\u55e8\uff0c\u4f60\u597d\u3002"
    assert reloaded.target_text == "\u55e8\uff0c\u4f60\u597d\u3002"
    assert reloaded.status == "rendered"
    assert reloaded.quality_flags == ["duration_ok"]
    assert window.timeline_editor.table.item(0, window.timeline_editor.COLUMN_STATUS).text() == "rendered"
    assert "\u7247\u6bb5\u5df2\u91cd\u751f\u6210" in window.progress_label.text()


def test_main_window_builds_background_worker_for_segment_regeneration(
    monkeypatch,
    qtbot,
    tmp_path,
) -> None:
    from ivo.pipeline.synthesize import SynthesisResult
    from ivo.ui.main_window import MainWindow

    captured: dict[str, object] = {}

    def fake_execute_segment_regeneration(segment_id: str):
        captured["segment_id"] = segment_id
        project = window.current_project
        assert project is not None
        segment = project.timeline.get_segment(segment_id)
        audio_path = project.path / "work" / "generated_segments" / f"{segment_id}.wav"
        audio_path.parent.mkdir(parents=True, exist_ok=True)
        audio_path.write_bytes(b"speech")
        project.timeline.update_segment(
            segment_id,
            status="rendered",
            quality_flags=["duration_ok"],
        )
        return SynthesisResult(
            segment_id=segment_id,
            audio_path=audio_path,
            generated_duration_ms=segment.end_ms - segment.start_ms,
            quality_flags=["duration_ok"],
        )

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    window = MainWindow()
    qtbot.addWidget(window)
    project = window.create_project_from_inputs(
        project_name="Episode 01",
        source_video=source,
        output_dir=tmp_path,
        source_language="en",
    )
    _add_approved_segment(project)
    window.model_settings.local_command_profiles_path_edit.setText(str(_write_local_profiles(tmp_path)))
    window.timeline_editor.set_project(project)
    window.timeline_editor.table.item(0, window.timeline_editor.COLUMN_TARGET_TEXT).setText(
        "\u55e8\uff0c\u4f60\u597d\u3002"
    )
    monkeypatch.setattr(window, "_execute_segment_regeneration", fake_execute_segment_regeneration)

    worker = window.create_segment_regeneration_worker("seg-001")

    assert project.timeline.get_segment("seg-001").target_text == "\u55e8\uff0c\u4f60\u597d\u3002"
    assert window.timeline_editor.regenerate_buttons[0].isEnabled() is False
    assert "\u6b63\u5728\u91cd\u751f\u6210\u7247\u6bb5" in window.progress_label.text()

    worker.run()
    window.handle_segment_regeneration_succeeded()

    assert captured["segment_id"] == "seg-001"
    assert worker.result.segment_id == "seg-001"
    assert window.timeline_editor.regenerate_buttons[0].isEnabled() is True
    assert window.timeline_editor.table.item(0, window.timeline_editor.COLUMN_STATUS).text() == "rendered"
    assert "\u7247\u6bb5\u5df2\u91cd\u751f\u6210" in window.progress_label.text()


def test_editing_rendered_segment_reopens_review_and_removes_audio(qtbot, tmp_path) -> None:
    from ivo.core.timeline import DubbingSegment
    from ivo.ui.timeline_editor import TimelineEditor

    from ivo.core.project import DubbingProject

    project = DubbingProject.create(
        tmp_path / "review-reset.ivoproj",
        name="Review Reset",
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
            quality_flags=["duration_ok"],
        )
    )
    generated_audio = project.path / "work" / "generated_segments" / "seg-001.wav"
    generated_audio.parent.mkdir(parents=True, exist_ok=True)
    generated_audio.write_bytes(b"old speech")

    editor = TimelineEditor()
    qtbot.addWidget(editor)
    editor.set_project(project)
    editor.table.item(0, editor.COLUMN_TARGET_TEXT).setText("嗨，你好。")

    updated = editor.save_row(0)

    assert updated.status == "needs_review"
    assert project.timeline.get_segment("seg-001").status == "needs_review"
    assert not generated_audio.exists()


def _write_local_profiles(tmp_path):
    profiles_path = tmp_path / "local-profiles.json"
    profiles_path.write_text(
        json.dumps(
            {
                "separation": {
                    "id": "sep",
                    "stage": "separation",
                    "command": ["sep"],
                    "output_json_path": "sep.json",
                },
                "asr": {
                    "id": "asr",
                    "stage": "asr",
                    "command": ["asr"],
                    "output_json_path": "asr.json",
                },
                "tts": {
                    "id": "tts",
                    "stage": "tts",
                    "command": ["tts"],
                    "output_json_path": "tts.json",
                },
            }
        ),
        encoding="utf-8",
    )
    return profiles_path


def _add_approved_segment(project) -> None:
    from ivo.core.timeline import DubbingSegment

    project.timeline.add_segment(
        DubbingSegment(
            id="seg-001",
            start_ms=0,
            end_ms=1_000,
            speaker_id="speaker-1",
            source_language="en",
            source_text="Well, hi.",
            target_language="zh",
            target_text="\u4f60\u597d\u3002",
            emotion="warm",
            status="approved",
        )
    )
