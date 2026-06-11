from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from ivo.adapters.local import CommandOutputCallback, LocalCommandProfile
from ivo.compliance.confirmation import ExportConfirmation
from ivo.compliance.metadata import build_ai_dubbing_metadata
from ivo.core.project import DubbingProject
from ivo.core.timeline import DubbingSegment
from ivo.pipeline.control import PipelineControl
from ivo.pipeline.import_video import extract_normalized_audio, import_source_video
from ivo.pipeline.mix_export import ExportRequest, SegmentAudio, export_dubbed_video
from ivo.pipeline.progress import PipelineProgressEvent, PipelineStage, STAGE_LABELS, stage_percent
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
    profiles: LocalCommandPipelineProfiles | None = None,
    translation_overrides: dict[str, str] | None = None,
    separation_adapter: SeparationAdapter | None = None,
    asr_adapter: AsrAdapter | None = None,
    diarization_adapter: DiarizationAdapter | None = None,
    translation_adapter: TranslationAdapter | None = None,
    tts_adapter: TtsAdapter | None = None,
    ffmpeg_path: str | None = None,
    watermark_text: str | None = "AI Dubbed",
    progress_callback: Callable[[PipelineProgressEvent], None] | None = None,
    command_output_callback: CommandOutputCallback | None = None,
    control: PipelineControl | None = None,
) -> LocalCommandPreviewResult:
    imported_video = _run_stage(
        project,
        "import",
        lambda: import_source_video(project, source_video),
        resume_from=lambda: _resume_file(project.path / "assets" / f"source_video{source_video.suffix}"),
        progress_callback=progress_callback,
        control=control,
    )
    extracted_audio = _run_stage(
        project,
        "audio_extract",
        lambda: extract_normalized_audio(project, imported_video, ffmpeg_path=ffmpeg_path),
        resume_from=lambda: _resume_file(project.path / "assets" / "extracted_audio.wav"),
        progress_callback=progress_callback,
        control=control,
    )
    # Ensure profiles is available when no adapter override is provided
    _need_profiles = (
        separation_adapter is None
        or asr_adapter is None
        or tts_adapter is None
    )
    if _need_profiles and profiles is None:
        raise ValueError(
            "profiles is required when separation/asr/tts adapter is not provided. "
            "Either supply a LocalCommandPipelineProfiles or provide all adapters."
        )
    assert profiles is not None or (separation_adapter and asr_adapter and tts_adapter)
    _sep_adapter: SeparationAdapter | None = separation_adapter
    if _sep_adapter is None and profiles is not None:
        _sep_adapter = LocalCommandSeparationAdapter(
            profiles.separation,
            command_output_callback=command_output_callback,
        )
    separation = _run_stage(
        project,
        "separation",
        lambda: separate_audio(
            project,
            extracted_audio,
            _sep_adapter,  # type: ignore[arg-type]
        ),
        resume_from=lambda: _resume_separation(project),
        progress_callback=progress_callback,
        control=control,
    )
    active_asr_adapter = asr_adapter
    if active_asr_adapter is None and profiles is not None:
        active_asr_adapter = LocalCommandAsrAdapter(
            profiles.asr,
            command_output_callback=command_output_callback,
        )
    assert active_asr_adapter is not None, "ASR adapter is required"
    source_segments = _run_stage(
        project,
        "asr",
        lambda: transcribe_audio(
            active_asr_adapter,
            separation.vocals_path,
            source_language=project.source_language,
        ),
        resume_from=lambda: _resume_source_segments(project),
        progress_callback=progress_callback,
        control=control,
    )
    active_diarization_adapter = diarization_adapter
    if active_diarization_adapter is None and profiles is not None and profiles.diarization is not None:
        active_diarization_adapter = LocalCommandDiarizationAdapter(
            profiles.diarization,
            command_output_callback=command_output_callback,
        )
    if active_diarization_adapter is not None:
        source_segments = _run_stage(
            project,
            "diarization",
            lambda: assign_speakers(
                source_segments,
                diarize_audio(active_diarization_adapter, separation.vocals_path),
            ),
            progress_callback=progress_callback,
            control=control,
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
        progress_callback=progress_callback,
        control=control,
    )

    generated_segments: list[Path] = []
    segment_audio: list[SegmentAudio] = []
    active_tts_adapter = tts_adapter
    if active_tts_adapter is None and profiles is not None:
        active_tts_adapter = LocalCommandTtsAdapter(
            profiles.tts,
            command_output_callback=command_output_callback,
        )
    assert active_tts_adapter is not None, "TTS adapter is required"
    _run_stage(
        project,
        "tts",
        lambda: _synthesize_segments(
            project,
            dubbed_segments,
            active_tts_adapter,
            generated_segments,
            segment_audio,
            progress_callback=progress_callback,
            control=control,
        ),
        progress_callback=progress_callback,
        control=control,
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
        progress_callback=progress_callback,
        control=control,
    )
    return LocalCommandPreviewResult(
        final_video=final_video,
        metadata=metadata,
        generated_segments=generated_segments,
    )


def _run_stage(
    project: DubbingProject,
    stage: PipelineStage,
    action: Callable[[], T],
    *,
    resume_from: Callable[[], T | None] | None = None,
    progress_callback: Callable[[PipelineProgressEvent], None] | None = None,
    control: PipelineControl | None = None,
) -> T:
    if control is not None:
        control.wait_if_paused()
    record = project.jobs.get(stage)
    if record is not None and record.status == "completed" and resume_from is not None:
        resumed = resume_from()
        if resumed is not None:
            _emit_progress(progress_callback, stage, "completed", output_path=_output_path(resumed))
            return resumed

    _emit_progress(progress_callback, stage, "started")
    project.jobs.mark_running(stage, "running")
    try:
        result = action()
    except Exception as exc:
        project.jobs.mark_failed(stage, str(exc))
        _emit_progress(progress_callback, stage, "failed", message=str(exc))
        raise
    project.jobs.mark_completed(stage, "completed")
    _emit_progress(progress_callback, stage, "completed", output_path=_output_path(result))
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
    progress_callback: Callable[[PipelineProgressEvent], None] | None = None,
    control: PipelineControl | None = None,
) -> None:
    total_items = len(dubbed_segments)
    for index, segment in enumerate(dubbed_segments, start=1):
        if control is not None:
            control.wait_if_paused()
        resumed_audio = _resume_segment_audio(project, segment)
        if resumed_audio is not None:
            generated_segments.append(resumed_audio)
            segment_audio.append(SegmentAudio(path=resumed_audio, start_ms=segment.start_ms))
            _emit_tts_progress(progress_callback, index, total_items, segment.id, resumed_audio)
            continue
        project.timeline.update_segment(segment.id, status="approved")
        synthesis = synthesize_segment(project, segment, active_tts_adapter)
        generated_segments.append(synthesis.audio_path)
        segment_audio.append(SegmentAudio(path=synthesis.audio_path, start_ms=segment.start_ms))
        _emit_tts_progress(progress_callback, index, total_items, segment.id, synthesis.audio_path)


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


def _emit_progress(
    callback: Callable[[PipelineProgressEvent], None] | None,
    stage: PipelineStage,
    status: str,
    *,
    message: str = "",
    current_item: int | None = None,
    total_items: int | None = None,
    output_path: Path | None = None,
) -> None:
    if callback is None:
        return
    callback(
        PipelineProgressEvent(
            stage=stage,
            stage_label=STAGE_LABELS[stage],
            status=status,  # type: ignore[arg-type]
            message=message,
            overall_percent=stage_percent(
                stage,
                status=status,  # type: ignore[arg-type]
                current_item=current_item,
                total_items=total_items,
            ),
            current_item=current_item,
            total_items=total_items,
            output_path=output_path,
        )
    )


def _emit_tts_progress(
    callback: Callable[[PipelineProgressEvent], None] | None,
    current_item: int,
    total_items: int,
    segment_id: str,
    output_path: Path,
) -> None:
    if callback is None or total_items == 0:
        return
    callback(
        PipelineProgressEvent(
            stage="tts",
            stage_label=STAGE_LABELS["tts"],
            status="progress",
            message=f"正在生成第 {current_item} / {total_items} 句：{segment_id}",
            overall_percent=stage_percent(
                "tts",
                status="progress",
                current_item=current_item,
                total_items=total_items,
            ),
            current_item=current_item,
            total_items=total_items,
            output_path=output_path,
        )
    )


def _output_path(result: object) -> Path | None:
    return result if isinstance(result, Path) else None
