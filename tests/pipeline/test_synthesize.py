from __future__ import annotations

import json
import wave
from pathlib import Path


def test_tts_duration_retry_only_happens_for_large_mismatch() -> None:
    from ivo.pipeline.synthesize import should_retry_duration_mismatch

    assert should_retry_duration_mismatch(
        generated_duration_ms=1250,
        target_duration_ms=1000,
        tolerance_ms=300,
        retry_ratio_threshold=0.35,
    ) is False
    assert should_retry_duration_mismatch(
        generated_duration_ms=1600,
        target_duration_ms=1000,
        tolerance_ms=300,
        retry_ratio_threshold=0.35,
    ) is True


def test_select_reference_segments_returns_approved_speaker_segments(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import select_reference_segments

    project = DubbingProject.create(
        tmp_path / "refs.ivoproj",
        name="Refs",
        source_language="en",
        target_language="zh",
    )
    project.timeline.add_segment(
        DubbingSegment(
            id="seg-001",
            start_ms=0,
            end_ms=1_000,
            speaker_id="speaker-1",
            source_language="en",
            source_text="Hello.",
            target_language="zh",
            target_text="你好。",
            status="approved",
        )
    )
    project.timeline.add_segment(
        DubbingSegment(
            id="seg-002",
            start_ms=1_100,
            end_ms=2_000,
            speaker_id="speaker-1",
            source_language="en",
            source_text="Bye.",
            target_language="zh",
            target_text="再见。",
            status="needs_review",
        )
    )

    references = select_reference_segments(project.timeline, speaker_id="speaker-1")

    assert [segment.id for segment in references] == ["seg-001"]


def test_mock_tts_generates_wav_and_duration_quality_flags(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import MockTtsAdapter, synthesize_segment

    project = DubbingProject.create(
        tmp_path / "tts.ivoproj",
        name="TTS",
        source_language="ja",
        target_language="zh",
    )
    segment = DubbingSegment(
        id="seg-001",
        start_ms=0,
        end_ms=1_000,
        speaker_id="speaker-1",
        source_language="ja",
        source_text="こんにちは。",
        target_language="zh",
        target_text="你好。",
        status="approved",
    )
    project.timeline.add_segment(segment)

    result = synthesize_segment(
        project,
        segment,
        MockTtsAdapter(generated_duration_ms=1_500),
        tolerance_ms=200,
    )

    assert result.audio_path == project.path / "work" / "generated_segments" / "seg-001.wav"
    assert result.quality_flags == [
        "duration_too_long",
        "tts_retried",
        "missing_reference_audio",
        "silent_audio",
    ]
    assert project.timeline.get_segment("seg-001").quality_flags == [
        "duration_too_long",
        "tts_retried",
        "missing_reference_audio",
        "silent_audio",
    ]
    with wave.open(str(result.audio_path), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getframerate() == 16000


def test_synthesize_segment_marks_short_audio(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import MockTtsAdapter, synthesize_segment

    project = DubbingProject.create(
        tmp_path / "tts-short.ivoproj",
        name="TTS Short",
        source_language="en",
        target_language="zh",
    )
    segment = DubbingSegment(
        id="seg-001",
        start_ms=0,
        end_ms=2_000,
        speaker_id="speaker-1",
        source_language="en",
        source_text="Hello.",
        target_language="zh",
        target_text="Hello.",
        status="approved",
    )
    project.timeline.add_segment(segment)

    result = synthesize_segment(
        project,
        segment,
        MockTtsAdapter(generated_duration_ms=1_000),
        tolerance_ms=200,
        max_duration_retries=0,
    )

    assert "duration_too_short" in result.quality_flags
    assert "duration_mismatch" not in result.quality_flags


def test_synthesize_retries_once_for_long_audio_with_faster_style_prompt(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import synthesize_segment

    class RetryingTtsAdapter:
        def __init__(self) -> None:
            self.durations = [1_600, 1_000]
            self.style_prompts: list[str | None] = []

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
            self.style_prompts.append(style_prompt)
            duration_ms = self.durations.pop(0)
            _write_test_wav(output_path, duration_ms=duration_ms, silent=False)
            return duration_ms

    project = DubbingProject.create(
        tmp_path / "tts-retry.ivoproj",
        name="TTS Retry",
        source_language="ja",
        target_language="zh",
    )
    segment = DubbingSegment(
        id="seg-001",
        start_ms=0,
        end_ms=1_000,
        speaker_id="speaker-1",
        source_language="ja",
        source_text="konnichiwa",
        target_language="zh",
        target_text="你好。",
        style_prompt="自然、克制",
        status="approved",
    )
    project.timeline.add_segment(segment)
    adapter = RetryingTtsAdapter()

    result = synthesize_segment(project, segment, adapter, tolerance_ms=100, max_duration_retries=1)

    assert result.generated_duration_ms == 1_000
    assert "duration_ok" in result.quality_flags
    assert "tts_retried" in result.quality_flags
    assert adapter.style_prompts[0] == "自然、克制"
    assert adapter.style_prompts[1] is not None
    assert "语速稍快" in adapter.style_prompts[1]


def test_synthesize_preserves_existing_quality_flags(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import MockTtsAdapter, synthesize_segment

    project = DubbingProject.create(
        tmp_path / "quality-flags.ivoproj",
        name="Quality Flags",
        source_language="en",
        target_language="zh",
    )
    segment = DubbingSegment(
        id="seg-001",
        start_ms=0,
        end_ms=1_000,
        speaker_id="unknown",
        source_language="en",
        source_text="Hello.",
        target_language="zh",
        target_text="你好。",
        status="approved",
        quality_flags=["speaker_unmatched"],
    )
    project.timeline.add_segment(segment)

    result = synthesize_segment(project, segment, MockTtsAdapter())

    assert result.quality_flags == [
        "speaker_unmatched",
        "duration_ok",
        "missing_reference_audio",
        "silent_audio",
    ]
    assert project.timeline.get_segment("seg-001").quality_flags == result.quality_flags


def test_synthesize_segment_passes_default_chinese_speech_rate(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import DEFAULT_CHINESE_TTS_SPEED, synthesize_segment

    class CapturingRateTtsAdapter:
        def __init__(self) -> None:
            self.speech_rates: list[float] = []

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
            speech_rate: float,
        ) -> int:
            self.speech_rates.append(speech_rate)
            _write_test_wav(output_path, duration_ms=target_duration_ms, silent=False)
            return target_duration_ms

    project = DubbingProject.create(
        tmp_path / "tts-speed-default.ivoproj",
        name="TTS Speed Default",
        source_language="ja",
        target_language="zh",
    )
    segment = DubbingSegment(
        id="seg-001",
        start_ms=0,
        end_ms=1_000,
        speaker_id="speaker-1",
        source_language="ja",
        source_text="konnichiwa",
        target_language="zh",
        target_text="ni hao",
        status="approved",
    )
    project.timeline.add_segment(segment)
    adapter = CapturingRateTtsAdapter()

    synthesize_segment(project, segment, adapter)

    assert adapter.speech_rates == [DEFAULT_CHINESE_TTS_SPEED]


def test_synthesize_segment_passes_explicit_speech_rate(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import synthesize_segment

    class CapturingRateTtsAdapter:
        def __init__(self) -> None:
            self.speech_rates: list[float] = []

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
            speech_rate: float,
        ) -> int:
            self.speech_rates.append(speech_rate)
            _write_test_wav(output_path, duration_ms=target_duration_ms, silent=False)
            return target_duration_ms

    project = DubbingProject.create(
        tmp_path / "tts-speed-explicit.ivoproj",
        name="TTS Speed Explicit",
        source_language="en",
        target_language="zh",
    )
    segment = DubbingSegment(
        id="seg-001",
        start_ms=0,
        end_ms=1_000,
        speaker_id="speaker-1",
        source_language="en",
        source_text="Hello.",
        target_language="zh",
        target_text="Hello.",
        status="approved",
    )
    project.timeline.add_segment(segment)
    adapter = CapturingRateTtsAdapter()

    synthesize_segment(project, segment, adapter, speech_rate=0.75)

    assert adapter.speech_rates == [0.75]


def test_local_command_tts_adapter_generates_audio_from_json_contract(tmp_path) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import LocalCommandTtsAdapter, synthesize_segment

    project = DubbingProject.create(
        tmp_path / "local-tts.ivoproj",
        name="Local TTS",
        source_language="en",
        target_language="zh",
    )
    segment = DubbingSegment(
        id="seg-001",
        start_ms=0,
        end_ms=1_000,
        speaker_id="speaker-1",
        source_language="en",
        source_text="Hello.",
        target_language="zh",
        target_text="你好。",
        status="approved",
    )
    project.timeline.add_segment(segment)
    output_json = tmp_path / "tts-result.json"
    commands: list[list[str]] = []

    def runner(command: list[str]) -> None:
        commands.append(command)
        audio_path = command[command.index("--audio-out") + 1]
        with wave.open(audio_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 16000)
        output_json.write_text(
            json.dumps({"audio_path": audio_path, "duration_ms": 1000}),
            encoding="utf-8",
        )

    adapter = LocalCommandTtsAdapter(
        LocalCommandProfile(
            id="cosyvoice-command",
            stage="tts",
            command=[
                "python",
                "tts.py",
                "--text",
                "{{ segment_text }}",
                "--speaker",
                "{{ speaker_id }}",
                "--audio-out",
                "{{ output_audio_path }}",
                "--speed",
                "{{ speech_rate }}",
                "--json-out",
                "{{ output_json_path }}",
            ],
            output_json_path=str(output_json),
        ),
        runner=runner,
    )

    result = synthesize_segment(project, segment, adapter)

    assert result.generated_duration_ms == 1000
    assert result.audio_path.is_file()
    assert commands[0][commands[0].index("--text") + 1] == segment.target_text
    assert commands[0][commands[0].index("--speed") + 1] == "0.9"


def test_local_command_tts_adapter_adds_speed_to_legacy_f5_command(tmp_path) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import LocalCommandTtsAdapter, synthesize_segment

    project = DubbingProject.create(
        tmp_path / "legacy-f5-tts.ivoproj",
        name="Legacy F5 TTS",
        source_language="ja",
        target_language="zh",
    )
    segment = DubbingSegment(
        id="seg-001",
        start_ms=0,
        end_ms=1_000,
        speaker_id="speaker-1",
        source_language="ja",
        source_text="konnichiwa",
        target_language="zh",
        target_text="ni hao",
        status="approved",
    )
    project.timeline.add_segment(segment)
    output_json = tmp_path / "tts-result.json"
    commands: list[list[str]] = []

    def runner(command: list[str]) -> None:
        commands.append(command)
        audio_path = Path(command[command.index("--audio-out") + 1])
        _write_test_wav(audio_path, duration_ms=1000)
        output_json.write_text(
            json.dumps({"audio_path": str(audio_path), "duration_ms": 1000}),
            encoding="utf-8",
        )

    adapter = LocalCommandTtsAdapter(
        LocalCommandProfile(
            id="legacy-f5-command",
            stage="tts",
            command=[
                "python",
                "examples/local_commands/f5_tts_command.py",
                "--text",
                "{{ segment_text }}",
                "--speaker",
                "{{ speaker_id }}",
                "--audio-out",
                "{{ output_audio_path }}",
                "--json-out",
                "{{ output_json_path }}",
            ],
            output_json_path=str(output_json),
        ),
        runner=runner,
    )

    synthesize_segment(project, segment, adapter, speech_rate=0.75)

    assert commands[0][commands[0].index("--speed") + 1] == "0.75"


def test_local_command_tts_receives_extracted_reference_audio(tmp_path) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import LocalCommandTtsAdapter, synthesize_segment

    project = DubbingProject.create(
        tmp_path / "reference-tts.ivoproj",
        name="Reference TTS",
        source_language="en",
        target_language="zh",
    )
    source_audio = project.path / "assets" / "extracted_audio.wav"
    _write_test_wav(source_audio, duration_ms=2_000)
    segment = DubbingSegment(
        id="seg-001",
        start_ms=500,
        end_ms=1_500,
        speaker_id="speaker-1",
        source_language="en",
        source_text="Hello.",
        target_language="zh",
        target_text="Hello.",
        status="approved",
    )
    project.timeline.add_segment(segment)
    output_json = tmp_path / "tts-result.json"
    captured_reference_paths: list[Path] = []

    def runner(command: list[str]) -> None:
        reference_path = Path(command[command.index("--reference-audio") + 1])
        captured_reference_paths.append(reference_path)
        assert reference_path.is_file()
        audio_path = command[command.index("--audio-out") + 1]
        _write_test_wav(Path(audio_path), duration_ms=1000)
        output_json.write_text(
            json.dumps({"audio_path": audio_path, "duration_ms": 1000}),
            encoding="utf-8",
        )

    adapter = LocalCommandTtsAdapter(
        LocalCommandProfile(
            id="voice-clone-command",
            stage="tts",
            command=[
                "python",
                "tts.py",
                "--text",
                "{{ segment_text }}",
                "--speaker",
                "{{ speaker_id }}",
                "--reference-audio",
                "{{ reference_audio_path }}",
                "--audio-out",
                "{{ output_audio_path }}",
                "--json-out",
                "{{ output_json_path }}",
            ],
            output_json_path=str(output_json),
        ),
        runner=runner,
    )

    synthesize_segment(project, segment, adapter)

    assert len(captured_reference_paths) == 1
    with wave.open(str(captured_reference_paths[0]), "rb") as wav_file:
        duration_ms = int(wav_file.getnframes() / wav_file.getframerate() * 1000)
    assert duration_ms == 1000


def test_local_command_tts_receives_source_text_as_reference_text(tmp_path) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import LocalCommandTtsAdapter, synthesize_segment

    project = DubbingProject.create(
        tmp_path / "reference-text-tts.ivoproj",
        name="Reference Text TTS",
        source_language="ja",
        target_language="zh",
    )
    segment = DubbingSegment(
        id="seg-001",
        start_ms=0,
        end_ms=1_000,
        speaker_id="speaker-1",
        source_language="ja",
        source_text="konnichiwa",
        target_language="zh",
        target_text="ni hao",
        status="approved",
    )
    project.timeline.add_segment(segment)
    output_json = tmp_path / "tts-result.json"
    captured_reference_texts: list[str] = []

    def runner(command: list[str]) -> None:
        captured_reference_texts.append(command[command.index("--reference-text") + 1])
        audio_path = command[command.index("--audio-out") + 1]
        _write_test_wav(Path(audio_path), duration_ms=1000)
        output_json.write_text(
            json.dumps({"audio_path": audio_path, "duration_ms": 1000}),
            encoding="utf-8",
        )

    adapter = LocalCommandTtsAdapter(
        LocalCommandProfile(
            id="voice-clone-command",
            stage="tts",
            command=[
                "python",
                "tts.py",
                "--text",
                "{{ segment_text }}",
                "--reference-text",
                "{{ reference_text }}",
                "--audio-out",
                "{{ output_audio_path }}",
                "--json-out",
                "{{ output_json_path }}",
            ],
            output_json_path=str(output_json),
        ),
        runner=runner,
    )

    synthesize_segment(project, segment, adapter)

    assert captured_reference_texts == [segment.source_text]


def test_extract_reference_audio_falls_back_to_current_unapproved_segment(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import extract_reference_audio

    project = DubbingProject.create(
        tmp_path / "preview-reference.ivoproj",
        name="Preview Reference",
        source_language="en",
        target_language="zh",
    )
    _write_test_wav(project.path / "assets" / "extracted_audio.wav", duration_ms=2_000)
    segment = DubbingSegment(
        id="seg-001",
        start_ms=250,
        end_ms=1_250,
        speaker_id="speaker-1",
        source_language="en",
        source_text="Hello.",
        target_language="zh",
        target_text="Hello.",
        status="needs_review",
    )
    project.timeline.add_segment(segment)

    reference_path = extract_reference_audio(project, segment)

    assert reference_path is not None
    assert reference_path.is_file()
    with wave.open(str(reference_path), "rb") as wav_file:
        duration_ms = int(wav_file.getnframes() / wav_file.getframerate() * 1000)
    assert duration_ms == 1000


def test_extract_reference_audio_prefers_speaker_profile_reference_segment(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.speakers import SpeakerProfile
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import extract_reference_audio

    project = DubbingProject.create(
        tmp_path / "profile-reference.ivoproj",
        name="Profile Reference",
        source_language="en",
        target_language="zh",
    )
    _write_test_wav(project.path / "assets" / "extracted_audio.wav", duration_ms=3_000)
    reference_segment = DubbingSegment(
        id="seg-ref",
        start_ms=0,
        end_ms=500,
        speaker_id="speaker-1",
        source_language="en",
        source_text="Reference.",
        target_language="zh",
        target_text="Reference.",
        status="needs_review",
    )
    current_segment = DubbingSegment(
        id="seg-current",
        start_ms=1_000,
        end_ms=2_000,
        speaker_id="speaker-1",
        source_language="en",
        source_text="Current.",
        target_language="zh",
        target_text="Current.",
        status="needs_review",
    )
    project.timeline.add_segment(reference_segment)
    project.timeline.add_segment(current_segment)
    project.speakers.upsert(
        SpeakerProfile(
            id="speaker-1",
            display_name="Speaker 1",
            reference_segment_ids=["seg-ref"],
        )
    )

    reference_path = extract_reference_audio(project, current_segment)

    assert reference_path == project.path / "work" / "reference_segments" / "speaker-1-seg-ref.wav"
    assert reference_path.is_file()
    with wave.open(str(reference_path), "rb") as wav_file:
        duration_ms = int(wav_file.getnframes() / wav_file.getframerate() * 1000)
    assert duration_ms == 500


def test_reference_sample_keeps_audio_and_source_text_from_same_segment(tmp_path) -> None:
    from ivo.core.project import DubbingProject
    from ivo.core.speakers import SpeakerProfile
    from ivo.core.timeline import DubbingSegment
    from ivo.pipeline.synthesize import extract_reference_sample

    project = DubbingProject.create(
        tmp_path / "reference-sample.ivoproj",
        name="Reference Sample",
        source_language="en",
        target_language="zh",
    )
    _write_test_wav(project.path / "assets" / "extracted_audio.wav", duration_ms=3_000)
    reference = DubbingSegment(
        id="seg-ref",
        start_ms=0,
        end_ms=500,
        speaker_id="speaker-1",
        source_language="en",
        source_text="Reference transcript.",
        target_language="zh",
        target_text="参考文本。",
        status="approved",
    )
    current = reference.model_copy(
        update={
            "id": "seg-current",
            "start_ms": 1_000,
            "end_ms": 2_000,
            "source_text": "Current transcript.",
        }
    )
    project.timeline.add_segment(reference)
    project.timeline.add_segment(current)
    project.speakers.upsert(
        SpeakerProfile(
            id="speaker-1",
            display_name="Speaker 1",
            reference_segment_ids=["seg-ref"],
        )
    )

    sample = extract_reference_sample(project, current)

    assert sample is not None
    assert sample.segment_id == reference.id
    assert sample.source_text == reference.source_text
    assert sample.audio_path.name == "speaker-1-seg-ref.wav"


def _write_test_wav(output_path: Path, *, duration_ms: int, silent: bool = True) -> None:
    sample_rate = 16_000
    sample_count = int(sample_rate * duration_ms / 1000)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame = b"\x00\x00" if silent else b"\x01\x00"
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frame * sample_count)
