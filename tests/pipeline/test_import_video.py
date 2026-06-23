from __future__ import annotations

import shutil
from pathlib import Path

import pytest


def test_require_ffmpeg_reports_clear_setup_error(monkeypatch) -> None:
    from ivo.pipeline import import_video
    from ivo.pipeline.import_video import FFmpegNotFoundError, require_ffmpeg

    # Project ships a bundled ffmpeg/, so mock the resolver to simulate a fully
    # missing FFmpeg (no env override, no bundled copy, nothing on PATH).
    monkeypatch.setattr(import_video, "resolve_executable", lambda *a, **k: None)
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
    from ivo.pipeline.import_video import import_source_media

    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake-video")
    project = DubbingProject.create(
        tmp_path / "copy.ivoproj",
        name="Copy",
        source_language="en",
        target_language="zh",
    )

    imported = import_source_media(project, source)

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


def test_import_audio_uses_source_audio_prefix(tmp_path: Path) -> None:
    """import_source_media with audio creates source_audio{ext} file."""
    from ivo.core.project import DubbingProject
    from ivo.pipeline.import_video import import_source_media

    project_path = tmp_path / "audio_import.ivoproj"
    source_audio = tmp_path / "music.mp3"
    source_audio.write_bytes(b"fake mp3 data")

    project = DubbingProject.create(
        project_path,
        name="Import Test",
        source_language="en",
        target_language="zh",
        source_media=source_audio,
        content_type="audio",
    )
    result = import_source_media(project, source_audio)
    assert result.name == "source_audio.mp3"
    assert (project_path / "assets" / "source_audio.mp3").is_file()


def test_extract_audio_for_audio_input_omits_vn(tmp_path: Path) -> None:
    """extract_normalized_audio with audio content_type uses ffmpeg without -vn."""
    from ivo.core.project import DubbingProject
    from ivo.pipeline.import_video import extract_normalized_audio, import_source_media

    project_path = tmp_path / "audio_extract.ivoproj"
    source_audio = tmp_path / "song.wav"
    # Write a minimal WAV header so ffprobe can parse it
    source_audio.write_bytes(
        b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
    )

    project = DubbingProject.create(
        project_path,
        name="Extract Test",
        source_language="en",
        target_language="zh",
        source_media=source_audio,
        content_type="audio",
    )
    imported = import_source_media(project, source_audio)
    result = extract_normalized_audio(project, imported)
    assert result.is_file()
    assert result.name == "extracted_audio.wav"
