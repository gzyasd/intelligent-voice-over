from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from ivo.adapters.local import LocalCommandProfile
from ivo.compliance.confirmation import ExportConfirmation
from ivo.compliance.metadata import build_ai_dubbing_metadata
from ivo.core.project import DubbingProject
from ivo.pipeline.import_video import extract_normalized_audio, import_source_video
from ivo.pipeline.mix_export import ExportRequest, SegmentAudio, export_dubbed_video
from ivo.pipeline.separate_audio import LocalCommandSeparationAdapter, separate_audio
from ivo.pipeline.synthesize import LocalCommandTtsAdapter, synthesize_segment
from ivo.pipeline.transcribe import LocalCommandAsrAdapter, TranscriptionSegment, transcribe_audio
from ivo.pipeline.translate import (
    MockTranslationAdapter,
    TranslationAdapter,
    TranslationResult,
    translate_segments,
)


class LocalCommandPipelineProfiles(BaseModel):
    separation: LocalCommandProfile
    asr: LocalCommandProfile
    tts: LocalCommandProfile


class LocalCommandPreviewResult(BaseModel):
    final_video: Path
    metadata: dict[str, str]
    generated_segments: list[Path]


def run_local_command_preview(
    project: DubbingProject,
    *,
    source_video: Path,
    profiles: LocalCommandPipelineProfiles,
    translation_overrides: dict[str, str] | None = None,
    translation_adapter: TranslationAdapter | None = None,
    ffmpeg_path: str | None = None,
    watermark_text: str | None = "AI Dubbed",
) -> LocalCommandPreviewResult:
    imported_video = import_source_video(project, source_video)
    extracted_audio = extract_normalized_audio(project, imported_video, ffmpeg_path=ffmpeg_path)
    separation = separate_audio(
        project,
        extracted_audio,
        LocalCommandSeparationAdapter(profiles.separation),
    )
    source_segments = transcribe_audio(
        LocalCommandAsrAdapter(profiles.asr),
        separation.vocals_path,
        source_language=project.source_language,
    )
    adapter = translation_adapter or _build_override_translation_adapter(
        source_segments,
        translation_overrides=translation_overrides or {},
    )
    dubbed_segments = translate_segments(project, source_segments, adapter)

    generated_segments: list[Path] = []
    segment_audio: list[SegmentAudio] = []
    tts_adapter = LocalCommandTtsAdapter(profiles.tts)
    for segment in dubbed_segments:
        project.timeline.update_segment(segment.id, status="approved")
        synthesis = synthesize_segment(project, segment, tts_adapter)
        generated_segments.append(synthesis.audio_path)
        segment_audio.append(SegmentAudio(path=synthesis.audio_path, start_ms=segment.start_ms))

    metadata = build_ai_dubbing_metadata(
        source_language=project.source_language,
        target_language=project.target_language,
    )
    final_video = export_dubbed_video(
        ExportRequest(
            source_video=imported_video,
            background_audio=separation.background_path,
            segment_audio=segment_audio,
            output_path=project.path / "renders" / "local-preview.mp4",
            metadata=metadata,
            watermark_text=watermark_text,
        ),
        ExportConfirmation(accepted=True),
        ffmpeg_path=ffmpeg_path,
    )
    return LocalCommandPreviewResult(
        final_video=final_video,
        metadata=metadata,
        generated_segments=generated_segments,
    )


def _build_override_translation_adapter(
    source_segments: list[TranscriptionSegment],
    *,
    translation_overrides: dict[str, str],
) -> MockTranslationAdapter:
    translations = {
        segment.id: TranslationResult(
            segment_id=segment.id,
            target_text=translation_overrides.get(segment.id, segment.source_text),
        )
        for segment in source_segments
    }
    return MockTranslationAdapter(translations)
