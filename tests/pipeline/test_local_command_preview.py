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
        source_media=source_video,
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
    assert result.final_output.is_file()
    assert result.final_output.stat().st_size > 0
    assert "AI generated dubbing" in result.metadata["comment"]
    assert result.generated_segments[0].is_file()
    assert segment.status == "rendered"
    assert segment.target_text == "Well, hello."
    assert {
        record.stage: record.status
        for record in project.jobs.list_records()
    } == {
        "import": "completed",
        "audio_extract": "completed",
        "separation": "completed",
        "asr": "completed",
        "translation": "completed",
        "tts": "completed",
        "export": "completed",
    }


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
        source_media=source_video,
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
            reference_audio_path: Path | None,
            reference_text: str,
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
        source_media=source_video,
        profiles=_mock_profiles(tmp_path),
        translation_overrides={"seg-001": "\u4f60\u597d\u3002"},
        tts_adapter=tts_adapter,
        ffmpeg_path=ffmpeg,
        watermark_text=None,
    )

    assert tts_adapter.texts == ["\u4f60\u597d\u3002"]
    assert result.generated_segments[0].is_file()
    assert project.timeline.get_segment("seg-001").status == "rendered"


def test_local_command_preview_marks_failed_stage_for_tts_error(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.import_video import FFmpegNotFoundError, require_ffmpeg
    from ivo.pipeline.local_command_preview import run_local_command_preview

    class FailingTtsAdapter:
        def synthesize(
            self,
            *,
            text: str,
            speaker_id: str,
            output_path: Path,
            style_prompt: str | None,
            reference_audio_path: Path | None,
            reference_text: str,
            target_duration_ms: int,
        ) -> int:
            raise RuntimeError("tts model crashed")

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
        tmp_path / "failed-tts-preview.ivoproj",
        name="Failed TTS Preview",
        source_language="en",
        target_language="zh",
    )

    with pytest.raises(RuntimeError, match="tts model crashed"):
        run_local_command_preview(
            project,
            source_media=source_video,
            profiles=_mock_profiles(tmp_path),
            translation_overrides={"seg-001": "\u4f60\u597d\u3002"},
            tts_adapter=FailingTtsAdapter(),
            ffmpeg_path=ffmpeg,
            watermark_text=None,
        )

    records = {record.stage: record for record in project.jobs.list_records()}
    assert records["translation"].status == "completed"
    assert records["tts"].status == "failed"
    assert records["tts"].message == "tts model crashed"
    assert "export" not in records


def test_local_command_preview_resumes_completed_file_stages(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.import_video import FFmpegNotFoundError, require_ffmpeg
    from ivo.pipeline.local_command_preview import run_local_command_preview
    from ivo.pipeline.separate_audio import SeparationResult
    from ivo.pipeline.transcribe import TranscriptionSegment

    class ExplodingSeparationAdapter:
        def separate(
            self,
            input_audio: Path,
            *,
            vocals_path: Path,
            background_path: Path,
        ) -> SeparationResult:
            raise AssertionError("separation should have been resumed from existing files")

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
                    end_ms=1_000,
                    source_language=source_language,
                    source_text="Previously separated audio.",
                    speaker_id="speaker-1",
                )
            ]

    class SilentTtsAdapter:
        def synthesize(
            self,
            *,
            text: str,
            speaker_id: str,
            output_path: Path,
            style_prompt: str | None,
            reference_audio_path: Path | None,
            reference_text: str,
            target_duration_ms: int,
        ) -> int:
            _write_silent_wav(output_path, duration_ms=target_duration_ms)
            return target_duration_ms

    try:
        ffmpeg = require_ffmpeg()
    except FFmpegNotFoundError:
        pytest.skip("FFmpeg is not visible in this shell; set IVO_FFMPEG_PATH or restart terminal.")

    project = DubbingProject.create(
        tmp_path / "resume-preview.ivoproj",
        name="Resume Preview",
        source_language="en",
        target_language="zh",
    )
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
            str(project.path / "assets" / "source_video.mp4"),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for audio_path in (
        project.path / "assets" / "extracted_audio.wav",
        project.path / "work" / "vocals.wav",
        project.path / "work" / "background.wav",
    ):
        _write_silent_wav(audio_path, duration_ms=1_000)
    for stage in ("import", "audio_extract", "separation"):
        project.jobs.mark_completed(stage, "completed")

    asr_adapter = RecordingAsrAdapter()
    result = run_local_command_preview(
        project,
        source_media=tmp_path / "source-does-not-need-to-exist.mp4",
        profiles=_mock_profiles(tmp_path),
        separation_adapter=ExplodingSeparationAdapter(),
        asr_adapter=asr_adapter,
        tts_adapter=SilentTtsAdapter(),
        translation_overrides={"seg-001": "\u4f60\u597d\u3002"},
        ffmpeg_path=ffmpeg,
        watermark_text=None,
    )

    assert asr_adapter.audio_paths == [project.path / "work" / "vocals.wav"]
    assert result.final_output.is_file()
    assert project.jobs.get("import").status == "completed"  # type: ignore[union-attr]
    assert project.jobs.get("audio_extract").status == "completed"  # type: ignore[union-attr]
    assert project.jobs.get("separation").status == "completed"  # type: ignore[union-attr]


def test_local_command_preview_resumes_completed_timeline_and_export_artifacts(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.local_command_preview import run_local_command_preview
    from ivo.pipeline.transcribe import TranscriptionSegment

    class ExplodingAsrAdapter:
        def transcribe(
            self,
            audio_path: Path,
            *,
            source_language: str,
        ) -> list[TranscriptionSegment]:
            raise AssertionError("asr should have been resumed from timeline")

    class ExplodingTtsAdapter:
        def synthesize(
            self,
            *,
            text: str,
            speaker_id: str,
            output_path: Path,
            style_prompt: str | None,
            reference_audio_path: Path | None,
            reference_text: str,
            target_duration_ms: int,
        ) -> int:
            raise AssertionError("rendered segment audio should have been reused")

    project = DubbingProject.create(
        tmp_path / "resume-complete.ivoproj",
        name="Resume Complete",
        source_language="en",
        target_language="zh",
    )
    (project.path / "assets" / "source_video.mp4").write_bytes(b"source video")
    for audio_path in (
        project.path / "assets" / "extracted_audio.wav",
        project.path / "work" / "vocals.wav",
        project.path / "work" / "background.wav",
        project.path / "work" / "generated_segments" / "seg-001.wav",
    ):
        _write_silent_wav(audio_path, duration_ms=1_000)
    final_video = project.path / "renders" / "local-preview.mp4"
    final_video.write_bytes(b"existing final")
    project.timeline.add_segment(
        DubbingSegment(
            id="seg-001",
            start_ms=0,
            end_ms=1_000,
            speaker_id="speaker-1",
            source_language="en",
            source_text="Already transcribed.",
            target_language="zh",
            target_text="Already translated.",
            status="rendered",
        )
    )
    for stage in ("import", "audio_extract", "separation", "asr", "translation", "tts", "export"):
        project.jobs.mark_completed(stage, "completed")

    result = run_local_command_preview(
        project,
        source_media=tmp_path / "missing-source.mp4",
        profiles=_mock_profiles(tmp_path),
        asr_adapter=ExplodingAsrAdapter(),
        tts_adapter=ExplodingTtsAdapter(),
        watermark_text=None,
    )

    assert result.final_output == final_video
    assert final_video.read_bytes() == b"existing final"
    assert result.generated_segments == [project.path / "work" / "generated_segments" / "seg-001.wav"]


def test_local_command_preview_resumes_failed_tts_from_rendered_segments(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.pipeline.import_video import FFmpegNotFoundError, require_ffmpeg
    from ivo.pipeline.local_command_preview import run_local_command_preview
    from ivo.pipeline.transcribe import TranscriptionSegment

    class TwoSegmentAsrAdapter:
        def transcribe(
            self,
            audio_path: Path,
            *,
            source_language: str,
        ) -> list[TranscriptionSegment]:
            return [
                TranscriptionSegment(
                    id="seg-001",
                    start_ms=0,
                    end_ms=1_000,
                    source_language=source_language,
                    source_text="Line one.",
                    speaker_id="speaker-1",
                ),
                TranscriptionSegment(
                    id="seg-002",
                    start_ms=1_000,
                    end_ms=2_000,
                    source_language=source_language,
                    source_text="Line two.",
                    speaker_id="speaker-1",
                ),
            ]

    class FailSecondTtsAdapter:
        def synthesize(
            self,
            *,
            text: str,
            speaker_id: str,
            output_path: Path,
            style_prompt: str | None,
            reference_audio_path: Path | None,
            reference_text: str,
            target_duration_ms: int,
        ) -> int:
            if text == "第二句。":
                raise RuntimeError("second segment failed")
            _write_silent_wav(output_path, duration_ms=target_duration_ms)
            return target_duration_ms

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
            reference_audio_path: Path | None,
            reference_text: str,
            target_duration_ms: int,
        ) -> int:
            self.texts.append(text)
            _write_silent_wav(output_path, duration_ms=target_duration_ms)
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
            "testsrc=size=64x64:duration=2:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=550:duration=2",
            "-shortest",
            str(source_video),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    project = DubbingProject.create(
        tmp_path / "failed-second-tts.ivoproj",
        name="Failed Second TTS",
        source_language="en",
        target_language="zh",
    )

    with pytest.raises(RuntimeError, match="second segment failed"):
        run_local_command_preview(
            project,
            source_media=source_video,
            profiles=_mock_profiles(tmp_path),
            asr_adapter=TwoSegmentAsrAdapter(),
            tts_adapter=FailSecondTtsAdapter(),
            translation_overrides={"seg-001": "第一句。", "seg-002": "第二句。"},
            ffmpeg_path=ffmpeg,
            watermark_text=None,
        )

    assert project.timeline.get_segment("seg-001").status == "rendered"
    assert project.jobs.get("translation").status == "completed"  # type: ignore[union-attr]
    assert project.jobs.get("tts").status == "failed"  # type: ignore[union-attr]

    recording_tts = RecordingTtsAdapter()
    result = run_local_command_preview(
        project,
        source_media=source_video,
        profiles=_mock_profiles(tmp_path),
        asr_adapter=TwoSegmentAsrAdapter(),
        tts_adapter=recording_tts,
        translation_overrides={"seg-001": "第一句。", "seg-002": "第二句。"},
        ffmpeg_path=ffmpeg,
        watermark_text=None,
    )

    assert recording_tts.texts == ["第二句。"]
    assert result.final_output.is_file()
    assert project.timeline.get_segment("seg-001").status == "rendered"
    assert project.timeline.get_segment("seg-002").status == "rendered"


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
        source_media=source_video,
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
        source_media=source_video,
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
        source_media=source_video,
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


def _write_silent_wav(output_path: Path, *, duration_ms: int) -> None:
    import wave

    sample_rate = 16_000
    sample_count = int(sample_rate * (duration_ms / 1000))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * sample_count)


def test_synthesize_segments_parallel_preserves_order_and_reports_elapsed(tmp_path) -> None:
    """max_parallelism>1 时并发合成，结果按原始顺序输出，progress 依次发出且带 elapsed_seconds。"""
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.local_command_preview import _synthesize_segments
    from ivo.pipeline.mix_export import SegmentAudio
    from ivo.pipeline.progress import PipelineProgressEvent

    class ParallelSilentTtsAdapter:
        max_parallelism = 2

        def synthesize(
            self,
            *,
            text: str,
            speaker_id: str,
            output_path: Path,
            style_prompt: str | None,
            reference_audio_path: Path | None,
            reference_text: str,
            target_duration_ms: int,
        ) -> int:
            _write_silent_wav(output_path, duration_ms=target_duration_ms)
            return target_duration_ms

    project = DubbingProject.create(
        tmp_path / "parallel-tts.ivoproj",
        name="Parallel TTS",
        source_language="en",
        target_language="zh",
    )
    segments = [
        DubbingSegment(
            id=f"seg-00{i}",
            start_ms=i * 1000,
            end_ms=(i + 1) * 1000,
            speaker_id="speaker-1",
            source_language="en",
            source_text=f"Line {i}.",
            target_language="zh",
            target_text=f"第{i}句。",
            status="approved",
        )
        for i in range(3)
    ]
    for seg in segments:
        project.timeline.add_segment(seg)

    generated: list[Path] = []
    audio: list[SegmentAudio] = []
    events: list[PipelineProgressEvent] = []

    _synthesize_segments(
        project,
        dubbed_segments=segments,
        active_tts_adapter=ParallelSilentTtsAdapter(),
        generated_segments=generated,
        segment_audio=audio,
        progress_callback=events.append,
    )

    # segment_audio 按原始 start_ms 顺序
    assert [sa.start_ms for sa in audio] == [0, 1000, 2000]
    # progress 依次发出 1/3, 2/3, 3/3
    assert [e.current_item for e in events] == [1, 2, 3]
    assert all(e.total_items == 3 for e in events)
    # 每个事件都有非负 elapsed_seconds
    assert all(e.elapsed_seconds is not None and e.elapsed_seconds >= 0 for e in events)
    # 生成了 3 个 wav 文件
    assert len(generated) == 3
    assert all(p.is_file() for p in generated)


def test_synthesize_segments_serial_reports_elapsed_seconds(tmp_path) -> None:
    """串行模式（max_parallelism=1）下 progress 事件也应带 elapsed_seconds。"""
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.local_command_preview import _synthesize_segments
    from ivo.pipeline.mix_export import SegmentAudio
    from ivo.pipeline.progress import PipelineProgressEvent

    class SerialSilentTtsAdapter:
        def synthesize(
            self,
            *,
            text: str,
            speaker_id: str,
            output_path: Path,
            style_prompt: str | None,
            reference_audio_path: Path | None,
            reference_text: str,
            target_duration_ms: int,
        ) -> int:
            _write_silent_wav(output_path, duration_ms=target_duration_ms)
            return target_duration_ms

    project = DubbingProject.create(
        tmp_path / "serial-tts.ivoproj",
        name="Serial TTS",
        source_language="en",
        target_language="zh",
    )
    segment = DubbingSegment(
        id="seg-001",
        start_ms=0,
        end_ms=1000,
        speaker_id="speaker-1",
        source_language="en",
        source_text="Line one.",
        target_language="zh",
        target_text="第一句。",
        status="approved",
    )
    project.timeline.add_segment(segment)

    generated: list[Path] = []
    audio: list[SegmentAudio] = []
    events: list[PipelineProgressEvent] = []

    _synthesize_segments(
        project,
        dubbed_segments=[segment],
        active_tts_adapter=SerialSilentTtsAdapter(),
        generated_segments=generated,
        segment_audio=audio,
        progress_callback=events.append,
    )

    assert len(events) == 1
    assert events[0].current_item == 1
    assert events[0].total_items == 1
    assert events[0].elapsed_seconds is not None
    assert events[0].elapsed_seconds >= 0
