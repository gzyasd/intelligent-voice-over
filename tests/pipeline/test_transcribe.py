from __future__ import annotations


def test_mock_asr_returns_timestamped_source_segments(tmp_path) -> None:
    from ivo.pipeline.transcribe import MockAsrAdapter, TranscriptionSegment, transcribe_audio

    audio = tmp_path / "vocals.wav"
    audio.write_bytes(b"fake-wav")
    adapter = MockAsrAdapter(
        [
            TranscriptionSegment(
                id="seg-001",
                start_ms=0,
                end_ms=1_000,
                source_language="en",
                source_text="Well, hi.",
            )
        ]
    )

    segments = transcribe_audio(adapter, audio, source_language="en")

    assert segments[0].id == "seg-001"
    assert segments[0].source_language == "en"
    assert segments[0].source_text == "Well, hi."


def test_assign_speakers_maps_diarization_ranges_to_asr_segments() -> None:
    from ivo.pipeline.transcribe import DiarizationSegment, TranscriptionSegment, assign_speakers

    segments = [
        TranscriptionSegment(
            id="seg-001",
            start_ms=0,
            end_ms=1_000,
            source_language="ja",
            source_text="えっと、こんにちは。",
        ),
        TranscriptionSegment(
            id="seg-002",
            start_ms=1_200,
            end_ms=2_000,
            source_language="ja",
            source_text="元気？",
        ),
    ]
    diarization = [
        DiarizationSegment(start_ms=0, end_ms=1_100, speaker_id="speaker-a"),
        DiarizationSegment(start_ms=1_100, end_ms=2_500, speaker_id="speaker-b"),
    ]

    assigned = assign_speakers(segments, diarization)

    assert [segment.speaker_id for segment in assigned] == ["speaker-a", "speaker-b"]


def test_assign_speakers_prefers_largest_overlap_over_midpoint() -> None:
    from ivo.pipeline.transcribe import DiarizationSegment, TranscriptionSegment, assign_speakers

    segments = [
        TranscriptionSegment(
            id="seg-001",
            start_ms=0,
            end_ms=1_000,
            source_language="ko",
            source_text="안녕.",
        )
    ]
    diarization = [
        DiarizationSegment(start_ms=0, end_ms=400, speaker_id="speaker-a"),
        DiarizationSegment(start_ms=450, end_ms=550, speaker_id="speaker-b"),
    ]

    assigned = assign_speakers(segments, diarization)

    assert assigned[0].speaker_id == "speaker-a"
    assert assigned[0].quality_flags == []


def test_assign_speakers_flags_segments_without_diarization_overlap() -> None:
    from ivo.pipeline.transcribe import DiarizationSegment, TranscriptionSegment, assign_speakers

    segments = [
        TranscriptionSegment(
            id="seg-001",
            start_ms=0,
            end_ms=1_000,
            source_language="en",
            source_text="Well, hi.",
            speaker_id="unknown",
        )
    ]
    diarization = [DiarizationSegment(start_ms=1_500, end_ms=2_000, speaker_id="speaker-a")]

    assigned = assign_speakers(segments, diarization)

    assert assigned[0].speaker_id == "unknown"
    assert assigned[0].quality_flags == ["speaker_unmatched"]


def test_local_command_asr_adapter_reads_segments_from_json(tmp_path) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.pipeline.transcribe import LocalCommandAsrAdapter, transcribe_audio

    audio = tmp_path / "vocals.wav"
    audio.write_bytes(b"fake-wav")
    output = tmp_path / "asr.json"
    commands: list[list[str]] = []

    def runner(command: list[str]) -> None:
        commands.append(command)
        output.write_text(
            """
            {
              "segments": [
                {
                  "id": "seg-001",
                  "start_ms": 0,
                  "end_ms": 1200,
                  "text": "Well, hi.",
                  "speaker_id": "speaker-1"
                }
              ]
            }
            """,
            encoding="utf-8",
        )

    adapter = LocalCommandAsrAdapter(
        LocalCommandProfile(
            id="whisper-local",
            stage="asr",
            command=[
                "python",
                "asr.py",
                "--audio",
                "{{ audio_path }}",
                "--language",
                "{{ source_language }}",
                "--out",
                "{{ output_json_path }}",
            ],
            output_json_path=str(output),
        ),
        runner=runner,
    )

    segments = transcribe_audio(adapter, audio, source_language="en")

    assert segments[0].id == "seg-001"
    assert segments[0].source_text == "Well, hi."
    assert segments[0].speaker_id == "speaker-1"
    assert commands == [
        [
            "python",
            "asr.py",
            "--audio",
            str(audio),
            "--language",
            "en",
            "--out",
            str(output),
        ]
    ]


def test_local_command_diarization_adapter_reads_segments_from_json(tmp_path) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.pipeline.transcribe import LocalCommandDiarizationAdapter, diarize_audio

    audio = tmp_path / "vocals.wav"
    audio.write_bytes(b"fake-wav")
    output = tmp_path / "diarization.json"
    commands: list[list[str]] = []

    def runner(command: list[str]) -> None:
        commands.append(command)
        output.write_text(
            """
            {
              "segments": [
                {
                  "start_ms": 0,
                  "end_ms": 1200,
                  "speaker_id": "speaker-a"
                }
              ]
            }
            """,
            encoding="utf-8",
        )

    adapter = LocalCommandDiarizationAdapter(
        LocalCommandProfile(
            id="pyannote-local",
            stage="diarization",
            command=[
                "python",
                "diarize.py",
                "--audio",
                "{{ audio_path }}",
                "--out",
                "{{ output_json_path }}",
            ],
            output_json_path=str(output),
        ),
        runner=runner,
    )

    segments = diarize_audio(adapter, audio)

    assert segments[0].speaker_id == "speaker-a"
    assert commands == [
        [
            "python",
            "diarize.py",
            "--audio",
            str(audio),
            "--out",
            str(output),
        ]
    ]
