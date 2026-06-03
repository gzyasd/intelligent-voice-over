from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles


def test_example_asr_command_outputs_contract(tmp_path) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake")
    output = tmp_path / "asr.json"

    subprocess.run(
        [
            sys.executable,
            "examples/local_commands/mock_asr.py",
            "--audio",
            str(audio),
            "--language",
            "en",
            "--out",
            str(output),
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["segments"][0]["text"] == "Well, hi."


def test_example_tts_command_writes_wav_and_contract(tmp_path) -> None:
    audio = tmp_path / "speech.wav"
    output = tmp_path / "tts.json"

    subprocess.run(
        [
            sys.executable,
            "examples/local_commands/mock_tts.py",
            "--text",
            "你好。",
            "--speaker",
            "speaker-1",
            "--audio-out",
            str(audio),
            "--json-out",
            str(output),
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["audio_path"] == str(audio)
    with wave.open(str(audio), "rb") as wav_file:
        assert wav_file.getframerate() == 16000


def test_example_separation_command_writes_outputs_and_contract(tmp_path) -> None:
    source = tmp_path / "audio.wav"
    source.write_bytes(b"fake")
    vocals = tmp_path / "vocals.wav"
    background = tmp_path / "background.wav"
    output = tmp_path / "separation.json"

    subprocess.run(
        [
            sys.executable,
            "examples/local_commands/mock_separate.py",
            "--audio",
            str(source),
            "--vocals-out",
            str(vocals),
            "--background-out",
            str(background),
            "--json-out",
            str(output),
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["vocals_path"] == str(vocals)
    assert vocals.read_bytes() == b"fake"
    assert background.read_bytes() == b"fake"


def test_example_diarization_command_outputs_contract(tmp_path) -> None:
    source = tmp_path / "vocals.wav"
    source.write_bytes(b"fake")
    output = tmp_path / "diarization.json"

    subprocess.run(
        [
            sys.executable,
            "examples/local_commands/mock_diarization.py",
            "--audio",
            str(source),
            "--out",
            str(output),
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["segments"] == [
        {"start_ms": 0, "end_ms": 1200, "speaker_id": "speaker-1"}
    ]


def test_mock_local_command_profile_includes_diarization() -> None:
    profile = LocalCommandPipelineProfiles.model_validate(
        json.loads(Path("examples/local_command_profiles.mock.json").read_text(encoding="utf-8"))
    )

    assert profile.diarization is not None
    assert profile.diarization.stage == "diarization"
