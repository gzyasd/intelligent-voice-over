from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def test_local_command_preview_runs_from_video_to_preview_export(tmp_path) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.core.project import DubbingProject
    from ivo.pipeline.import_video import FFmpegNotFoundError, require_ffmpeg
    from ivo.pipeline.local_command_preview import (
        LocalCommandPipelineProfiles,
        run_local_command_preview,
    )

    try:
        ffmpeg = require_ffmpeg()
    except FFmpegNotFoundError:
        pytest.skip("FFmpeg is not visible in this shell; set IVO_FFMPEG_PATH or restart terminal.")

    source_video = tmp_path / "source.mp4"
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
            "sine=frequency=880:duration=1",
            "-shortest",
            str(source_video),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    project = DubbingProject.create(
        tmp_path / "local-preview.ivoproj",
        name="Local Preview",
        source_language="en",
        target_language="zh",
    )

    result = run_local_command_preview(
        project,
        source_video=source_video,
        profiles=LocalCommandPipelineProfiles(
            separation=LocalCommandProfile(
                id="mock-separate",
                stage="separation",
                command=[
                    sys.executable,
                    "examples/local_commands/mock_separate.py",
                    "--audio",
                    "{{ audio_path }}",
                    "--vocals-out",
                    "{{ vocals_path }}",
                    "--background-out",
                    "{{ background_path }}",
                    "--json-out",
                    "{{ output_json_path }}",
                ],
                output_json_path=str(tmp_path / "separation.json"),
            ),
            asr=LocalCommandProfile(
                id="mock-asr",
                stage="asr",
                command=[
                    sys.executable,
                    "examples/local_commands/mock_asr.py",
                    "--audio",
                    "{{ audio_path }}",
                    "--language",
                    "{{ source_language }}",
                    "--out",
                    "{{ output_json_path }}",
                ],
                output_json_path=str(tmp_path / "asr.json"),
            ),
            tts=LocalCommandProfile(
                id="mock-tts",
                stage="tts",
                command=[
                    sys.executable,
                    "examples/local_commands/mock_tts.py",
                    "--text",
                    "{{ segment_text }}",
                    "--speaker",
                    "{{ speaker_id }}",
                    "--audio-out",
                    "{{ output_audio_path }}",
                    "--duration-ms",
                    "{{ target_duration_ms }}",
                    "--json-out",
                    "{{ output_json_path }}",
                ],
                output_json_path=str(tmp_path / "tts.json"),
            ),
        ),
        translation_overrides={"seg-001": "Well, hello."},
        ffmpeg_path=ffmpeg,
        watermark_text="AI Dubbed",
    )

    segment = project.timeline.get_segment("seg-001")
    assert result.final_video.is_file()
    assert result.final_video.stat().st_size > 0
    assert result.metadata["ai_dubbing"] == "true"
    assert result.generated_segments[0].is_file()
    assert segment.status == "rendered"
    assert segment.target_text == "Well, hello."


def test_local_command_preview_uses_translation_adapter(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.import_video import FFmpegNotFoundError, require_ffmpeg
    from ivo.pipeline.local_command_preview import run_local_command_preview
    from ivo.pipeline.transcribe import TranscriptionSegment
    from ivo.pipeline.translate import TranslationResult

    class RecordingTranslationAdapter:
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def translate(self, segment: TranscriptionSegment, *, prompt: str) -> TranslationResult:
            self.prompts.append(prompt)
            return TranslationResult(
                segment_id=segment.id,
                target_text="嗯，你好。",
                emotion="warm",
            )

    try:
        ffmpeg = require_ffmpeg()
    except FFmpegNotFoundError:
        pytest.skip("FFmpeg is not visible in this shell; set IVO_FFMPEG_PATH or restart terminal.")

    source_video = tmp_path / "source.mp4"
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
            "sine=frequency=440:duration=1",
            "-shortest",
            str(source_video),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    project = DubbingProject.create(
        tmp_path / "local-preview-http.ivoproj",
        name="Local Preview HTTP",
        source_language="en",
        target_language="zh",
    )
    adapter = RecordingTranslationAdapter()

    run_local_command_preview(
        project,
        source_video=source_video,
        profiles=_mock_profiles(tmp_path),
        translation_adapter=adapter,
        ffmpeg_path=ffmpeg,
        watermark_text=None,
    )

    segment = project.timeline.get_segment("seg-001")
    assert adapter.prompts
    assert "Well, hi." in adapter.prompts[0]
    assert segment.target_text == "嗯，你好。"
    assert segment.emotion == "warm"


def _mock_profiles(tmp_path: Path):
    from ivo.adapters.local import LocalCommandProfile
    from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles

    return LocalCommandPipelineProfiles(
        separation=LocalCommandProfile(
            id="mock-separate",
            stage="separation",
            command=[
                sys.executable,
                "examples/local_commands/mock_separate.py",
                "--audio",
                "{{ audio_path }}",
                "--vocals-out",
                "{{ vocals_path }}",
                "--background-out",
                "{{ background_path }}",
                "--json-out",
                "{{ output_json_path }}",
            ],
            output_json_path=str(tmp_path / "separation.json"),
        ),
        asr=LocalCommandProfile(
            id="mock-asr",
            stage="asr",
            command=[
                sys.executable,
                "examples/local_commands/mock_asr.py",
                "--audio",
                "{{ audio_path }}",
                "--language",
                "{{ source_language }}",
                "--out",
                "{{ output_json_path }}",
            ],
            output_json_path=str(tmp_path / "asr.json"),
        ),
        tts=LocalCommandProfile(
            id="mock-tts",
            stage="tts",
            command=[
                sys.executable,
                "examples/local_commands/mock_tts.py",
                "--text",
                "{{ segment_text }}",
                "--speaker",
                "{{ speaker_id }}",
                "--audio-out",
                "{{ output_audio_path }}",
                "--duration-ms",
                "{{ target_duration_ms }}",
                "--json-out",
                "{{ output_json_path }}",
            ],
            output_json_path=str(tmp_path / "tts.json"),
        ),
    )
