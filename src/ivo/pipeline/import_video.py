from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from ivo.core.project import DubbingProject
from ivo.environment import resolve_executable

CommandRunner = Callable[[list[str]], None]


class FFmpegNotFoundError(RuntimeError):
    """Raised when FFmpeg is required but unavailable."""


def require_ffmpeg() -> str:
    ffmpeg_path = resolve_executable("ffmpeg", env_var="IVO_FFMPEG_PATH")
    if ffmpeg_path is None:
        raise FFmpegNotFoundError("FFmpeg not found. Install FFmpeg and add it to PATH.")
    return ffmpeg_path


def import_source_media(
    project: DubbingProject, source_media: Path, content_type: str | None = None
) -> Path:
    if not source_media.is_file():
        raise FileNotFoundError(source_media)

    ct = content_type or project.content_type
    prefix = "source_video" if ct == "video" else "source_audio"
    destination = project.path / "assets" / f"{prefix}{source_media.suffix}"
    shutil.copy2(source_media, destination)
    return destination


def extract_normalized_audio(
    project: DubbingProject,
    source_media: Path,
    *,
    ffmpeg_path: str | None = None,
    runner: CommandRunner | None = None,
    content_type: str | None = None,
) -> Path:
    executable = ffmpeg_path or require_ffmpeg()
    output_path = project.path / "assets" / "extracted_audio.wav"
    ct = content_type or project.content_type
    command = [
        executable,
        "-y",
        "-i",
        str(source_media),
    ]
    # Video needs -vn to drop video track; audio has no video track
    if ct == "video":
        command.append("-vn")
    command += [
        "-ac",
        "1",
        "-ar",
        "16000",
        str(output_path),
    ]

    if runner is None:
        subprocess.run(command, check=True)
    else:
        runner(command)

    return output_path
