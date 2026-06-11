from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def test_export_requires_rights_confirmation(tmp_path) -> None:
    from ivo.compliance.confirmation import ExportConfirmation
    from ivo.pipeline.mix_export import ExportRequest, RightsConfirmationRequired, export_dubbed_video

    request = ExportRequest(
        source_video=tmp_path / "source.mp4",
        background_audio=tmp_path / "background.wav",
        segment_audio=[],
        output_path=tmp_path / "final.mp4",
        metadata={"ai_dubbing": "true"},
        watermark_text=None,
    )

    with pytest.raises(RightsConfirmationRequired):
        export_dubbed_video(
            request,
            ExportConfirmation(accepted=False),
            ffmpeg_path="ffmpeg-test",
            runner=lambda command: None,
        )


def test_export_command_places_segments_metadata_and_watermark(tmp_path) -> None:
    from ivo.compliance.confirmation import ExportConfirmation
    from ivo.pipeline.mix_export import ExportRequest, SegmentAudio, export_dubbed_video

    source_video = tmp_path / "source.mp4"
    background_audio = tmp_path / "background.wav"
    segment_audio = tmp_path / "seg-001.wav"
    source_video.write_bytes(b"video")
    background_audio.write_bytes(b"background")
    segment_audio.write_bytes(b"dialogue")
    commands: list[list[str]] = []

    def runner(command: list[str]) -> None:
        commands.append(command)
        Path(command[-1]).write_bytes(b"final")

    output = export_dubbed_video(
        ExportRequest(
            source_video=source_video,
            background_audio=background_audio,
            segment_audio=[SegmentAudio(path=segment_audio, start_ms=250)],
            output_path=tmp_path / "final.mp4",
            metadata={"ai_dubbing": "true", "target_language": "zh"},
            watermark_text="AI 中文配音",
        ),
        ExportConfirmation(accepted=True),
        ffmpeg_path="ffmpeg-test",
        runner=runner,
    )

    command = commands[0]
    assert output.read_bytes() == b"final"
    assert command[0] == "ffmpeg-test"
    assert str(source_video) in command
    assert any("adelay=250|250" in part for part in command)
    assert any("drawtext" in part for part in command)
    assert "-metadata" in command
    assert "ai_dubbing=true" in command


def test_export_hides_ffmpeg_command_window_on_windows(monkeypatch, tmp_path) -> None:
    from ivo.compliance.confirmation import ExportConfirmation
    from ivo.pipeline.mix_export import ExportRequest, export_dubbed_video

    source_video = tmp_path / "source.mp4"
    background_audio = tmp_path / "background.wav"
    output_path = tmp_path / "final.mp4"
    source_video.write_bytes(b"video")
    background_audio.write_bytes(b"background")
    calls: list[dict[str, object]] = []

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        calls.append(kwargs)
        output_path.write_bytes(b"final")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("ivo.pipeline.mix_export.subprocess.run", fake_run)

    export_dubbed_video(
        ExportRequest(
            source_video=source_video,
            background_audio=background_audio,
            output_path=output_path,
            metadata={"ai_dubbing": "true"},
        ),
        ExportConfirmation(accepted=True),
        ffmpeg_path="ffmpeg-test",
    )

    assert calls[0]["check"] is True
    if sys.platform == "win32":
        assert calls[0]["creationflags"] & subprocess.CREATE_NO_WINDOW
        assert calls[0]["startupinfo"] is not None
