from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel, Field

from ivo.compliance.confirmation import ExportConfirmation
from ivo.compliance.watermark import WatermarkOptions, build_watermark_filter
from ivo.pipeline.import_video import require_ffmpeg

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
        subprocess.run(command, check=True)
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
