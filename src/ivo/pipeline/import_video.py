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


def import_source_video(project: DubbingProject, source_video: Path) -> Path:
    if not source_video.is_file():
        raise FileNotFoundError(source_video)

    destination = project.path / "assets" / f"source_video{source_video.suffix}"
    shutil.copy2(source_video, destination)
    return destination


def extract_normalized_audio(
    project: DubbingProject,
    source_video: Path,
    *,
    ffmpeg_path: str | None = None,
    runner: CommandRunner | None = None,
) -> Path:
    executable = ffmpeg_path or require_ffmpeg()
    output_path = project.path / "assets" / "extracted_audio.wav"
    command = [
        executable,
        "-y",
        "-i",
        str(source_video),
        "-vn",
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
