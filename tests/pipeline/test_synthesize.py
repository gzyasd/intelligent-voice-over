from __future__ import annotations

import json
import wave
from pathlib import Path


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
    assert result.quality_flags == ["duration_mismatch"]
    assert project.timeline.get_segment("seg-001").quality_flags == ["duration_mismatch"]
    with wave.open(str(result.audio_path), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getframerate() == 16000


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


def _write_test_wav(output_path: Path, *, duration_ms: int) -> None:
    sample_rate = 16_000
    sample_count = int(sample_rate * duration_ms / 1000)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * sample_count)
