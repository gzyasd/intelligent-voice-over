from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from ivo.adapters.local import LocalCommandProfile
from ivo.compliance.confirmation import ExportConfirmation
from ivo.compliance.metadata import build_ai_dubbing_metadata
from ivo.core.project import DubbingProject
from ivo.core.timeline import DubbingSegment
from ivo.pipeline.import_video import extract_normalized_audio, import_source_video
from ivo.pipeline.mix_export import ExportRequest, SegmentAudio, export_dubbed_video
from ivo.pipeline.separate_audio import (
    LocalCommandSeparationAdapter,
    SeparationAdapter,
    SeparationResult,
    separate_audio,
)
from ivo.pipeline.synthesize import LocalCommandTtsAdapter, TtsAdapter, synthesize_segment
from ivo.pipeline.transcribe import (
    AsrAdapter,
    DiarizationAdapter,
    LocalCommandAsrAdapter,
    LocalCommandDiarizationAdapter,
    TranscriptionSegment,
    assign_speakers,
    diarize_audio,
    transcribe_audio,
)
from ivo.pipeline.translate import (
    MockTranslationAdapter,
    TranslationAdapter,
    TranslationResult,
    translate_segments,
)


class LocalCommandPipelineProfiles(BaseModel):
    separation: LocalCommandProfile
    asr: LocalCommandProfile
    diarization: LocalCommandProfile | None = None
    tts: LocalCommandProfile


class LocalCommandPreviewResult(BaseModel):
    final_video: Path
    metadata: dict[str, str]
    generated_segments: list[Path]


T = TypeVar("T")


def run_local_command_preview(
    project: DubbingProject,
    *,
    source_video: Path,
    profiles: LocalCommandPipelineProfiles,
    translation_overrides: dict[str, str] | None = None,
    separation_adapter: SeparationAdapter | None = None,
    asr_adapter: AsrAdapter | None = None,
    diarization_adapter: DiarizationAdapter | None = None,
    translation_adapter: TranslationAdapter | None = None,
    tts_adapter: TtsAdapter | None = None,
    ffmpeg_path: str | None = None,
    watermark_text: str | None = "AI Dubbed",
) -> LocalCommandPreviewResult:
    imported_video = _run_stage(
        project,
        "import",
        lambda: import_source_video(project, source_video),
        resume_from=lambda: _resume_file(project.path / "assets" / f"source_video{source_video.suffix}"),
    )
    extracted_audio = _run_stage(
        project,
        "audio_extract",
        lambda: extract_normalized_audio(project, imported_video, ffmpeg_path=ffmpeg_path),
        resume_from=lambda: _resume_file(project.path / "assets" / "extracted_audio.wav"),
    )
    separation = _run_stage(
        project,
        "separation",
        lambda: separate_audio(
            project,
            extracted_audio,
            separation_adapter or LocalCommandSeparationAdapter(profiles.separation),
        ),
        resume_from=lambda: _resume_separation(project),
    )
    active_asr_adapter = asr_adapter or LocalCommandAsrAdapter(profiles.asr)
    source_segments = _run_stage(
        project,
        "asr",
        lambda: transcribe_audio(
            active_asr_adapter,
            separation.vocals_path,
            source_language=project.source_language,
        ),
        resume_from=lambda: _resume_source_segments(project),
    )
    active_diarization_adapter = diarization_adapter
    if active_diarization_adapter is None and profiles.diarization is not None:
        active_diarization_adapter = LocalCommandDiarizationAdapter(profiles.diarization)
    if active_diarization_adapter is not None:
        source_segments = _run_stage(
            project,
            "diarization",
            lambda: assign_speakers(
                source_segments,
                diarize_audio(active_diarization_adapter, separation.vocals_path),
            ),
        )
    adapter = translation_adapter or _build_override_translation_adapter(
        source_segments,
        translation_overrides=translation_overrides or {},
    )
    dubbed_segments = _run_stage(
        project,
        "translation",
        lambda: translate_segments(project, source_segments, adapter),
        resume_from=lambda: _resume_translated_segments(project),
    )

    generated_segments: list[Path] = []
    segment_audio: list[SegmentAudio] = []
    active_tts_adapter = tts_adapter or LocalCommandTtsAdapter(profiles.tts)
    _run_stage(
        project,
        "tts",
        lambda: _synthesize_segments(
            project,
            dubbed_segments,
            active_tts_adapter,
            generated_segments,
            segment_audio,
        ),
    )

    metadata = build_ai_dubbing_metadata(
        source_language=project.source_language,
        target_language=project.target_language,
    )
    final_video = _run_stage(
        project,
        "export",
        lambda: export_dubbed_video(
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
        ),
        resume_from=lambda: _resume_file(project.path / "renders" / "local-preview.mp4"),
    )
    return LocalCommandPreviewResult(
        final_video=final_video,
        metadata=metadata,
        generated_segments=generated_segments,
    )


def _run_stage(
    project: DubbingProject,
    stage: str,
    action: Callable[[], T],
    *,
    resume_from: Callable[[], T | None] | None = None,
) -> T:
    record = project.jobs.get(stage)
    if record is not None and record.status == "completed" and resume_from is not None:
        resumed = resume_from()
        if resumed is not None:
            return resumed

    project.jobs.mark_running(stage, "running")
    try:
        result = action()
    except Exception as exc:
        project.jobs.mark_failed(stage, str(exc))
        raise
    project.jobs.mark_completed(stage, "completed")
    return result


def _resume_file(path: Path) -> Path | None:
    return path if path.is_file() else None


def _resume_separation(project: DubbingProject) -> SeparationResult | None:
    vocals_path = project.path / "work" / "vocals.wav"
    background_path = project.path / "work" / "background.wav"
    if not vocals_path.is_file() or not background_path.is_file():
        return None
    return SeparationResult(vocals_path=vocals_path, background_path=background_path)


def _resume_translated_segments(project: DubbingProject) -> list[DubbingSegment] | None:
    segments = project.timeline.list_segments()
    return segments or None


def _resume_source_segments(project: DubbingProject) -> list[TranscriptionSegment] | None:
    translation_record = project.jobs.get("translation")
    if translation_record is None or translation_record.status != "completed":
        return None
    segments = project.timeline.list_segments()
    if not segments:
        return None
    return [
        TranscriptionSegment(
            id=segment.id,
            start_ms=segment.start_ms,
            end_ms=segment.end_ms,
            source_language=segment.source_language,
            source_text=segment.source_text,
            speaker_id=segment.speaker_id,
            quality_flags=segment.quality_flags,
        )
        for segment in segments
    ]


def _synthesize_segments(
    project: DubbingProject,
    dubbed_segments: list[DubbingSegment],
    active_tts_adapter: TtsAdapter,
    generated_segments: list[Path],
    segment_audio: list[SegmentAudio],
) -> None:
    for segment in dubbed_segments:
        resumed_audio = _resume_segment_audio(project, segment)
        if resumed_audio is not None:
            generated_segments.append(resumed_audio)
            segment_audio.append(SegmentAudio(path=resumed_audio, start_ms=segment.start_ms))
            continue
        project.timeline.update_segment(segment.id, status="approved")
        synthesis = synthesize_segment(project, segment, active_tts_adapter)
        generated_segments.append(synthesis.audio_path)
        segment_audio.append(SegmentAudio(path=synthesis.audio_path, start_ms=segment.start_ms))


def _resume_segment_audio(project: DubbingProject, segment: DubbingSegment) -> Path | None:
    audio_path = project.path / "work" / "generated_segments" / f"{segment.id}.wav"
    if segment.status != "rendered" or not audio_path.is_file():
        return None
    return audio_path


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
