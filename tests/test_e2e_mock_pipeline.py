from __future__ import annotations

from pathlib import Path


def test_mock_pipeline_creates_final_video_with_metadata(tmp_path) -> None:
    from ivo.compliance.confirmation import ExportConfirmation
    from ivo.compliance.metadata import build_ai_dubbing_metadata
    from ivo.core.project import DubbingProject
    from ivo.pipeline.import_video import extract_normalized_audio, import_source_video
    from ivo.pipeline.mix_export import ExportRequest, SegmentAudio, export_dubbed_video
    from ivo.pipeline.separate_audio import MockSeparationAdapter, separate_audio
    from ivo.pipeline.synthesize import MockTtsAdapter, synthesize_segment
    from ivo.pipeline.transcribe import MockAsrAdapter, TranscriptionSegment, transcribe_audio
    from ivo.pipeline.translate import MockTranslationAdapter, TranslationResult, translate_segments

    project = DubbingProject.create(
        tmp_path / "e2e.ivoproj",
        name="E2E",
        source_language="en",
        target_language="zh",
    )
    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    imported = import_source_video(project, source)

    def audio_runner(command: list[str]) -> None:
        Path(command[-1]).write_bytes(b"wav")

    extracted_audio = extract_normalized_audio(
        project,
        imported,
        ffmpeg_path="ffmpeg-test",
        runner=audio_runner,
    )
    separation = separate_audio(project, extracted_audio, MockSeparationAdapter())
    source_segments = transcribe_audio(
        MockAsrAdapter(
            [
                TranscriptionSegment(
                    id="seg-001",
                    start_ms=100,
                    end_ms=1_100,
                    source_language="en",
                    source_text="Well, hi.",
                    speaker_id="speaker-1",
                )
            ]
        ),
        separation.vocals_path,
        source_language="en",
    )
    dubbed_segments = translate_segments(
        project,
        source_segments,
        MockTranslationAdapter(
            {
                "seg-001": TranslationResult(
                    segment_id="seg-001",
                    target_text="嗯，你好。",
                    emotion="warm",
                )
            }
        ),
    )
    project.timeline.update_segment("seg-001", status="approved")
    synthesis = synthesize_segment(project, dubbed_segments[0], MockTtsAdapter())
    metadata = build_ai_dubbing_metadata(source_language="en", target_language="zh")

    def export_runner(command: list[str]) -> None:
        Path(command[-1]).write_bytes(b"final-video")

    final_video = export_dubbed_video(
        ExportRequest(
            source_video=imported,
            background_audio=separation.background_path,
            segment_audio=[SegmentAudio(path=synthesis.audio_path, start_ms=100)],
            output_path=project.path / "renders" / "final.mp4",
            metadata=metadata,
            watermark_text="AI Dubbed",
        ),
        ExportConfirmation(accepted=True),
        ffmpeg_path="ffmpeg-test",
        runner=export_runner,
    )

    assert final_video.read_bytes() == b"final-video"
    assert metadata["ai_dubbing"] == "true"
    assert project.timeline.get_segment("seg-001").status == "rendered"
