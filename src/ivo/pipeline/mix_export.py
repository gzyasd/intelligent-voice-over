from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from ivo.compliance.confirmation import ExportConfirmation
from ivo.compliance.watermark import WatermarkOptions, build_watermark_filter
from ivo.pipeline.import_video import require_ffmpeg
from ivo.subprocess_utils import hidden_subprocess_kwargs

CommandRunner = Callable[[list[str]], None]


class RightsConfirmationRequired(RuntimeError):
    """Raised when final export is attempted without rights confirmation."""


class SegmentAudio(BaseModel):
    path: Path
    start_ms: int


class ExportRequest(BaseModel):
    source_video: Path
    background_audio: Path
    segment_audio: list[SegmentAudio] = Field(default_factory=list)
    output_path: Path
    metadata: dict[str, str]
    watermark_text: str | None = None


class AudioExportRequest(BaseModel):
    background_audio: Path
    segment_audio: list[SegmentAudio] = Field(default_factory=list)
    output_path: Path
    metadata: dict[str, str]
    format: Literal["wav", "mp3"] = "wav"
    # Audio exports have no source_video (no video track) and no watermark


def export_dubbed_video(
    request: ExportRequest,
    confirmation: ExportConfirmation,
    *,
    ffmpeg_path: str | None = None,
    runner: CommandRunner | None = None,
) -> Path:
    if not confirmation.accepted:
        raise RightsConfirmationRequired("Export requires rights confirmation.")

    executable = ffmpeg_path or require_ffmpeg()
    command = build_export_command(executable, request)
    if runner is None:
        subprocess.run(command, check=True, **hidden_subprocess_kwargs())
    else:
        runner(command)
    return request.output_path


def build_export_command(ffmpeg_path: str, request: ExportRequest) -> list[str]:
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(request.source_video),
        "-i",
        str(request.background_audio),
    ]
    for segment in request.segment_audio:
        command.extend(["-i", str(segment.path)])

    has_watermark = bool(request.watermark_text)
    filter_complex = _build_filter_complex(request)
    if filter_complex:
        command.extend(["-filter_complex", filter_complex])
        command.extend(["-map", "[vout]" if has_watermark else "0:v", "-map", "[aout]"])
    else:
        command.extend(["-map", "0:v", "-map", "1:a"])

    for key, value in request.metadata.items():
        command.extend(["-metadata", f"{key}={value}"])

    command.extend(["-c:v", "libx264", "-c:a", "aac", str(request.output_path)])
    return command


def _build_filter_complex(request: ExportRequest) -> str:
    audio_filters: list[str] = []
    mix_inputs = ["[1:a]"]
    for index, segment in enumerate(request.segment_audio, start=2):
        label = f"seg{index - 2}"
        audio_filters.append(f"[{index}:a]adelay={segment.start_ms}|{segment.start_ms}[{label}]")
        mix_inputs.append(f"[{label}]")
    audio_filters.append(f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:normalize=0[aout]")

    watermark_filter = (
        build_watermark_filter(WatermarkOptions(enabled=True, text=request.watermark_text))
        if request.watermark_text
        else None
    )
    if watermark_filter:
        return ";".join([f"[0:v]{watermark_filter}[vout]", *audio_filters])
    return ";".join(audio_filters)


def _resolve_audio_output_path(request: AudioExportRequest) -> Path:
    """Return the actual output path, correcting suffix if it doesn't match the format."""
    expected_suffix = f".{request.format}"
    if request.output_path.suffix.lower() != expected_suffix:
        return request.output_path.with_suffix(expected_suffix)
    return request.output_path


def export_dubbed_audio(
    request: AudioExportRequest,
    confirmation: ExportConfirmation,
    *,
    ffmpeg_path: str | None = None,
    runner: CommandRunner | None = None,
) -> Path:
    if not confirmation.accepted:
        raise RightsConfirmationRequired("Export requires rights confirmation.")

    executable = ffmpeg_path or require_ffmpeg()
    command = build_audio_export_command(executable, request)
    if runner is None:
        subprocess.run(command, check=True, **hidden_subprocess_kwargs())
    else:
        runner(command)
    return _resolve_audio_output_path(request)


def build_audio_export_command(ffmpeg_path: str, request: AudioExportRequest) -> list[str]:
    command = [
        ffmpeg_path,
        "-y",
        "-i",
        str(request.background_audio),
    ]
    for segment in request.segment_audio:
        command.extend(["-i", str(segment.path)])

    filter_complex = _build_audio_filter_complex(request)
    command.extend(["-filter_complex", filter_complex])
    command.extend(["-map", "[aout]"])

    for key, value in request.metadata.items():
        command.extend(["-metadata", f"{key}={value}"])

    # Encode based on requested format
    if request.format == "mp3":
        command.extend(["-c:a", "libmp3lame", "-b:a", "192k"])
    else:
        command.extend(["-c:a", "pcm_s16le"])
    command.append(str(_resolve_audio_output_path(request)))
    return command


def _build_audio_filter_complex(request: AudioExportRequest) -> str:
    audio_filters: list[str] = []
    mix_inputs = ["[0:a]"]
    for index, segment in enumerate(request.segment_audio, start=1):
        label = f"seg{index - 1}"
        audio_filters.append(f"[{index}:a]adelay={segment.start_ms}|{segment.start_ms}[{label}]")
        mix_inputs.append(f"[{label}]")
    audio_filters.append(f"{''.join(mix_inputs)}amix=inputs={len(mix_inputs)}:duration=longest:normalize=0[aout]")
    return ";".join(audio_filters)
