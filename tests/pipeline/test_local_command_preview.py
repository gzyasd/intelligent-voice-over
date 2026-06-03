from __future__ import annotations

import subprocess
import sys
import shutil
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


def test_local_command_preview_can_use_custom_tts_adapter(tmp_path) -> None:
    import wave

    from ivo.core.project import DubbingProject
    from ivo.pipeline.import_video import FFmpegNotFoundError, require_ffmpeg
    from ivo.pipeline.local_command_preview import run_local_command_preview

    class RecordingTtsAdapter:
        def __init__(self) -> None:
            self.texts: list[str] = []

        def synthesize(
            self,
            *,
            text: str,
            speaker_id: str,
            output_path: Path,
            style_prompt: str | None,
            target_duration_ms: int,
        ) -> int:
            self.texts.append(text)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(output_path), "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(b"\x00\x00" * 16000)
            return target_duration_ms

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
            "sine=frequency=550:duration=1",
            "-shortest",
            str(source_video),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    project = DubbingProject.create(
        tmp_path / "custom-tts-preview.ivoproj",
        name="Custom TTS Preview",
        source_language="en",
        target_language="zh",
    )
    tts_adapter = RecordingTtsAdapter()

    result = run_local_command_preview(
        project,
        source_video=source_video,
        profiles=_mock_profiles(tmp_path),
        translation_overrides={"seg-001": "\u4f60\u597d\u3002"},
        tts_adapter=tts_adapter,
        ffmpeg_path=ffmpeg,
        watermark_text=None,
    )

    assert tts_adapter.texts == ["\u4f60\u597d\u3002"]
    assert result.generated_segments[0].is_file()
    assert project.timeline.get_segment("seg-001").status == "rendered"


def test_local_command_preview_can_use_custom_asr_adapter(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.import_video import FFmpegNotFoundError, require_ffmpeg
    from ivo.pipeline.local_command_preview import run_local_command_preview
    from ivo.pipeline.transcribe import TranscriptionSegment

    class RecordingAsrAdapter:
        def __init__(self) -> None:
            self.audio_paths: list[Path] = []

        def transcribe(
            self,
            audio_path: Path,
            *,
            source_language: str,
        ) -> list[TranscriptionSegment]:
            self.audio_paths.append(audio_path)
            return [
                TranscriptionSegment(
                    id="seg-001",
                    start_ms=0,
                    end_ms=1000,
                    source_language=source_language,
                    source_text="Hello from HTTP ASR.",
                    speaker_id="speaker-1",
                )
            ]

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
            "sine=frequency=330:duration=1",
            "-shortest",
            str(source_video),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    project = DubbingProject.create(
        tmp_path / "custom-asr-preview.ivoproj",
        name="Custom ASR Preview",
        source_language="en",
        target_language="zh",
    )
    asr_adapter = RecordingAsrAdapter()

    run_local_command_preview(
        project,
        source_video=source_video,
        profiles=_mock_profiles(tmp_path),
        asr_adapter=asr_adapter,
        translation_overrides={"seg-001": "\u4f60\u597d\u3002"},
        ffmpeg_path=ffmpeg,
        watermark_text=None,
    )

    assert asr_adapter.audio_paths
    assert project.timeline.get_segment("seg-001").source_text == "Hello from HTTP ASR."


def test_local_command_preview_can_use_custom_separation_adapter(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.import_video import FFmpegNotFoundError, require_ffmpeg
    from ivo.pipeline.local_command_preview import run_local_command_preview
    from ivo.pipeline.separate_audio import SeparationResult

    class RecordingSeparationAdapter:
        def __init__(self) -> None:
            self.input_paths: list[Path] = []

        def separate(
            self,
            input_audio: Path,
            *,
            vocals_path: Path,
            background_path: Path,
        ) -> SeparationResult:
            self.input_paths.append(input_audio)
            shutil.copy2(input_audio, vocals_path)
            shutil.copy2(input_audio, background_path)
            return SeparationResult(vocals_path=vocals_path, background_path=background_path)

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
            "sine=frequency=330:duration=1",
            "-shortest",
            str(source_video),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    project = DubbingProject.create(
        tmp_path / "custom-separation-preview.ivoproj",
        name="Custom Separation Preview",
        source_language="en",
        target_language="zh",
    )
    separation_adapter = RecordingSeparationAdapter()

    run_local_command_preview(
        project,
        source_video=source_video,
        profiles=_mock_profiles(tmp_path),
        separation_adapter=separation_adapter,
        translation_overrides={"seg-001": "\u4f60\u597d\u3002"},
        ffmpeg_path=ffmpeg,
        watermark_text=None,
    )

    assert separation_adapter.input_paths
    assert (project.path / "work" / "vocals.wav").is_file()


def test_local_command_preview_can_use_custom_diarization_adapter(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.import_video import FFmpegNotFoundError, require_ffmpeg
    from ivo.pipeline.local_command_preview import run_local_command_preview
    from ivo.pipeline.transcribe import DiarizationSegment

    class RecordingDiarizationAdapter:
        def __init__(self) -> None:
            self.audio_paths: list[Path] = []

        def diarize(self, audio_path: Path) -> list[DiarizationSegment]:
            self.audio_paths.append(audio_path)
            return [
                DiarizationSegment(
                    start_ms=0,
                    end_ms=2_000,
                    speaker_id="speaker-from-diarization",
                )
            ]

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
            "sine=frequency=330:duration=1",
            "-shortest",
            str(source_video),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    project = DubbingProject.create(
        tmp_path / "custom-diarization-preview.ivoproj",
        name="Custom Diarization Preview",
        source_language="en",
        target_language="zh",
    )
    diarization_adapter = RecordingDiarizationAdapter()

    run_local_command_preview(
        project,
        source_video=source_video,
        profiles=_mock_profiles(tmp_path),
        diarization_adapter=diarization_adapter,
        translation_overrides={"seg-001": "\u4f60\u597d\u3002"},
        ffmpeg_path=ffmpeg,
        watermark_text=None,
    )

    assert diarization_adapter.audio_paths
    assert project.timeline.get_segment("seg-001").speaker_id == "speaker-from-diarization"


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
