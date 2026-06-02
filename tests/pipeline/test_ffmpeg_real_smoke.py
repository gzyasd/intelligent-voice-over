from __future__ import annotations

import subprocess

import pytest


def test_real_ffmpeg_extracts_audio_when_available(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.import_video import FFmpegNotFoundError, extract_normalized_audio, require_ffmpeg

    try:
        ffmpeg = require_ffmpeg()
    except FFmpegNotFoundError:
        pytest.skip("FFmpeg is not visible in this shell; set IVO_FFMPEG_PATH or restart terminal.")

    source = tmp_path / "sample.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=64x64:duration=1:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=1000:duration=1",
            "-shortest",
            str(source),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    project = DubbingProject.create(
        tmp_path / "real-ffmpeg.ivoproj",
        name="Real FFmpeg",
        source_language="en",
        target_language="zh",
    )

    audio = extract_normalized_audio(project, source, ffmpeg_path=ffmpeg)

    assert audio.is_file()
    assert audio.stat().st_size > 0
