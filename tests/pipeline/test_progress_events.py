from __future__ import annotations

from pathlib import Path
from threading import Thread
from time import sleep


def test_local_command_preview_emits_stage_and_tts_progress_events(monkeypatch, tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.local_command_preview import run_local_command_preview
    from ivo.pipeline.separate_audio import SeparationResult
    from ivo.pipeline.synthesize import SynthesisResult
    from ivo.pipeline.transcribe import TranscriptionSegment

    import ivo.pipeline.local_command_preview as module

    project = DubbingProject.create(
        tmp_path / "progress.ivoproj",
        name="Progress",
        source_language="en",
        target_language="zh",
    )
    source_video = tmp_path / "source.mp4"
    source_video.write_bytes(b"video")

    def fake_import_source_video(project, source_video):
        output = project.path / "assets" / "source_video.mp4"
        output.write_bytes(source_video.read_bytes())
        return output

    def fake_extract_normalized_audio(project, imported_video, *, ffmpeg_path=None):
        output = project.path / "assets" / "extracted_audio.wav"
        output.write_bytes(b"audio")
        return output

    def fake_separate_audio(project, audio_path, adapter):
        vocals = project.path / "work" / "vocals.wav"
        background = project.path / "work" / "background.wav"
        vocals.parent.mkdir(parents=True, exist_ok=True)
        vocals.write_bytes(b"vocals")
        background.write_bytes(b"background")
        return SeparationResult(vocals_path=vocals, background_path=background)

    def fake_transcribe_audio(adapter, audio_path, *, source_language):
        return [
            TranscriptionSegment(
                id="seg-001",
                start_ms=0,
                end_ms=1_000,
                source_language=source_language,
                source_text="Line one.",
                speaker_id="speaker-1",
            ),
            TranscriptionSegment(
                id="seg-002",
                start_ms=1_000,
                end_ms=2_000,
                source_language=source_language,
                source_text="Line two.",
                speaker_id="speaker-1",
            ),
        ]

    def fake_translate_segments(project, source_segments, adapter):
        segments = [
            DubbingSegment(
                id=segment.id,
                start_ms=segment.start_ms,
                end_ms=segment.end_ms,
                speaker_id=segment.speaker_id,
                source_language=segment.source_language,
                source_text=segment.source_text,
                target_language="zh",
                target_text=f"ZH {segment.source_text}",
                status="needs_review",
            )
            for segment in source_segments
        ]
        for segment in segments:
            project.timeline.upsert_segment(segment)
        return segments

    def fake_synthesize_segment(project, segment, adapter):
        output = project.path / "work" / "generated_segments" / f"{segment.id}.wav"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"wav")
        project.timeline.update_segment(segment.id, status="rendered")
        return SynthesisResult(
            segment_id=segment.id,
            audio_path=output,
            generated_duration_ms=segment.end_ms - segment.start_ms,
            quality_flags=[],
        )

    def fake_export_dubbed_video(request, confirmation, *, ffmpeg_path=None):
        request.output_path.parent.mkdir(parents=True, exist_ok=True)
        request.output_path.write_bytes(b"mp4")
        return request.output_path

    monkeypatch.setattr(module, "import_source_video", fake_import_source_video)
    monkeypatch.setattr(module, "extract_normalized_audio", fake_extract_normalized_audio)
    monkeypatch.setattr(module, "separate_audio", fake_separate_audio)
    monkeypatch.setattr(module, "transcribe_audio", fake_transcribe_audio)
    monkeypatch.setattr(module, "translate_segments", fake_translate_segments)
    monkeypatch.setattr(module, "synthesize_segment", fake_synthesize_segment)
    monkeypatch.setattr(module, "export_dubbed_video", fake_export_dubbed_video)

    events = []

    result = run_local_command_preview(
        project,
        source_video=source_video,
        profiles=_profiles(tmp_path),
        progress_callback=events.append,
        watermark_text=None,
    )

    assert result.final_video.is_file()
    stage_statuses = [(event.stage, event.status) for event in events]
    assert stage_statuses == [
        ("import", "started"),
        ("import", "completed"),
        ("audio_extract", "started"),
        ("audio_extract", "completed"),
        ("separation", "started"),
        ("separation", "completed"),
        ("asr", "started"),
        ("asr", "completed"),
        ("translation", "started"),
        ("translation", "completed"),
        ("tts", "started"),
        ("tts", "progress"),
        ("tts", "progress"),
        ("tts", "completed"),
        ("export", "started"),
        ("export", "completed"),
    ]
    assert [event.current_item for event in events if event.status == "progress"] == [1, 2]
    assert [event.total_items for event in events if event.status == "progress"] == [2, 2]
    assert events[-1].output_path == result.final_video


def test_stage_percent_gives_tts_the_largest_progress_range() -> None:
    from ivo.pipeline.progress import stage_percent

    assert stage_percent("import", status="completed") == 5
    assert stage_percent("translation", status="completed") == 55
    assert stage_percent("tts", status="started") == 55
    assert stage_percent("tts", status="progress", current_item=1, total_items=2) == 72
    assert stage_percent("tts", status="completed") == 90
    assert stage_percent("export", status="completed") == 100


def test_run_stage_waits_while_pipeline_is_paused(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.control import PipelineControl
    from ivo.pipeline.local_command_preview import _run_stage

    project = DubbingProject.create(
        tmp_path / "paused.ivoproj",
        name="Paused",
        source_language="en",
        target_language="zh",
    )
    control = PipelineControl()
    control.pause()
    ran: list[str] = []

    def action() -> Path:
        ran.append("import")
        output = project.path / "assets" / "source.mp4"
        output.write_bytes(b"video")
        return output

    thread = Thread(target=lambda: _run_stage(project, "import", action, control=control))
    thread.start()
    sleep(0.1)

    assert ran == []
    control.resume()
    thread.join(timeout=2)
    assert ran == ["import"]


def _profiles(tmp_path: Path):
    from ivo.adapters.local import LocalCommandProfile
    from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles

    return LocalCommandPipelineProfiles(
        separation=LocalCommandProfile(
            id="sep",
            stage="separation",
            command=["sep"],
            output_json_path=str(tmp_path / "sep.json"),
        ),
        asr=LocalCommandProfile(
            id="asr",
            stage="asr",
            command=["asr"],
            output_json_path=str(tmp_path / "asr.json"),
        ),
        tts=LocalCommandProfile(
            id="tts",
            stage="tts",
            command=["tts"],
            output_json_path=str(tmp_path / "tts.json"),
        ),
    )
