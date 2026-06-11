from __future__ import annotations

import shutil
from pathlib import Path

import pytest


def test_require_ffmpeg_reports_clear_setup_error(monkeypatch) -> None:
    from ivo.pipeline.import_video import FFmpegNotFoundError, require_ffmpeg

    monkeypatch.setattr(shutil, "which", lambda name: None)

    with pytest.raises(FFmpegNotFoundError, match="FFmpeg"):
        require_ffmpeg()


def test_require_ffmpeg_accepts_explicit_environment_path(monkeypatch, tmp_path) -> None:
    from ivo.pipeline.import_video import require_ffmpeg

    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_text("fake", encoding="utf-8")
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setenv("IVO_FFMPEG_PATH", str(ffmpeg))

    assert require_ffmpeg() == str(ffmpeg)


def test_import_video_copies_source_into_project_assets(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.import_video import import_source_video

    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake-video")
    project = DubbingProject.create(
        tmp_path / "copy.ivoproj",
        name="Copy",
        source_language="en",
        target_language="zh",
    )

    imported = import_source_video(project, source)

    assert imported == project.path / "assets" / "source_video.mp4"
    assert imported.read_bytes() == b"fake-video"


def test_extract_normalized_audio_invokes_ffmpeg_runner(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.import_video import extract_normalized_audio

    project = DubbingProject.create(
        tmp_path / "audio.ivoproj",
        name="Audio",
        source_language="ja",
        target_language="zh",
    )
    source = project.path / "assets" / "source_video.mp4"
    source.write_bytes(b"fake-video")
    commands: list[list[str]] = []

    def runner(command: list[str]) -> None:
        commands.append(command)
        Path(command[-1]).write_bytes(b"fake-wav")

    output = extract_normalized_audio(project, source, ffmpeg_path="ffmpeg-test", runner=runner)

    assert output == project.path / "assets" / "extracted_audio.wav"
    assert output.read_bytes() == b"fake-wav"
    assert commands == [
        [
            "ffmpeg-test",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(output),
        ]
    ]
