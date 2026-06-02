from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from ivo.compliance.confirmation import ExportConfirmation
from ivo.compliance.metadata import build_ai_dubbing_metadata
from ivo.core.project import DubbingProject
from ivo.pipeline.import_video import extract_normalized_audio, import_source_video
from ivo.pipeline.mix_export import ExportRequest, SegmentAudio, export_dubbed_video
from ivo.pipeline.separate_audio import MockSeparationAdapter, separate_audio
from ivo.pipeline.synthesize import MockTtsAdapter, synthesize_segment
from ivo.pipeline.transcribe import MockAsrAdapter, TranscriptionSegment, transcribe_audio
from ivo.pipeline.translate import MockTranslationAdapter, TranslationResult, translate_segments


class MockPipelineResult(BaseModel):
    final_video: Path
    metadata: dict[str, str]


def run_mock_dubbing_pipeline(
    project: DubbingProject,
    *,
    source_video: Path,
    watermark_text: str = "AI Dubbed",
) -> MockPipelineResult:
    imported = import_source_video(project, source_video)
    extracted_audio = extract_normalized_audio(
        project,
        imported,
        ffmpeg_path="ffmpeg-mock",
        runner=_write_mock_audio,
    )
    separation = separate_audio(project, extracted_audio, MockSeparationAdapter())
    source_segments = transcribe_audio(
        MockAsrAdapter(
            [
                TranscriptionSegment(
                    id="seg-001",
                    start_ms=100,
                    end_ms=1_100,
                    source_language=project.source_language,
                    source_text="Well, hi.",
                    speaker_id="speaker-1",
                )
            ]
        ),
        separation.vocals_path,
        source_language=project.source_language,
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
    metadata = build_ai_dubbing_metadata(
        source_language=project.source_language,
        target_language=project.target_language,
    )
    final_video = export_dubbed_video(
        ExportRequest(
            source_video=imported,
            background_audio=separation.background_path,
            segment_audio=[SegmentAudio(path=synthesis.audio_path, start_ms=100)],
            output_path=project.path / "renders" / "preview.mp4",
            metadata=metadata,
            watermark_text=watermark_text,
        ),
        ExportConfirmation(accepted=True),
        ffmpeg_path="ffmpeg-mock",
        runner=_write_mock_video,
    )
    return MockPipelineResult(final_video=final_video, metadata=metadata)


def _write_mock_audio(command: list[str]) -> None:
    Path(command[-1]).write_bytes(b"mock-wav")


def _write_mock_video(command: list[str]) -> None:
    Path(command[-1]).write_bytes(b"mock-final-video")
