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


def test_real_asr_profile_uses_large_v3_without_dry_run() -> None:
    profile = LocalCommandPipelineProfiles.model_validate(
        json.loads(Path("examples/local_command_profiles.real_asr.json").read_text(encoding="utf-8"))
    )

    assert profile.asr.id == "faster-whisper-large-v3"
    assert "--dry-run" not in profile.asr.command
    assert "Systran/faster-whisper-large-v3" in profile.asr.command
    assert profile.separation.id == "demucs-dry-run"
    assert "--dry-run" in profile.separation.command
    assert profile.tts.id == "f5-tts-dry-run"


def test_real_separation_asr_profile_uses_demucs_and_faster_whisper() -> None:
    profile = LocalCommandPipelineProfiles.model_validate(
        json.loads(
            Path("examples/local_command_profiles.real_separation_asr.json").read_text(
                encoding="utf-8"
            )
        )
    )

    assert profile.separation.id == "demucs-htdemucs"
    assert "--dry-run" not in profile.separation.command
    assert "--two-stems" in profile.separation.command
    assert "htdemucs" in profile.separation.command
    assert profile.asr.id == "faster-whisper-large-v3"
    assert "--dry-run" not in profile.asr.command
    assert profile.tts.id == "f5-tts-dry-run"


def test_real_separation_asr_cpu_small_profile_is_fast_real_probe() -> None:
    profile = LocalCommandPipelineProfiles.model_validate(
        json.loads(
            Path("examples/local_command_profiles.real_separation_asr_cpu_small.json").read_text(
                encoding="utf-8"
            )
        )
    )

    assert profile.separation.id == "demucs-htdemucs-cpu"
    assert "--device" in profile.separation.command
    assert "cpu" in profile.separation.command
    assert "--dry-run" not in profile.separation.command
    assert profile.asr.id == "faster-whisper-small-cpu"
    assert "small" in profile.asr.command
    assert "int8" in profile.asr.command
    assert "--dry-run" not in profile.asr.command
    assert profile.tts.id == "f5-tts-dry-run"


def test_real_diarization_profile_uses_pyannote_command() -> None:
    profile = LocalCommandPipelineProfiles.model_validate(
        json.loads(
            Path("examples/local_command_profiles.real_diarization.json").read_text(
                encoding="utf-8"
            )
        )
    )

    assert profile.diarization is not None
    assert profile.diarization.id == "pyannote-community-1"
    assert "--dry-run" not in profile.diarization.command
    assert "--hf-token-env" in profile.diarization.command
    assert "pyannote/speaker-diarization-community-1" in profile.diarization.command


def test_real_translation_qwen_profile_keeps_model_stages_dry_run() -> None:
    profile = LocalCommandPipelineProfiles.model_validate(
        json.loads(
            Path("examples/local_command_profiles.real_translation_qwen.json").read_text(
                encoding="utf-8"
            )
        )
    )

    assert profile.separation.id == "demucs-dry-run"
    assert profile.asr.id == "faster-whisper-dry-run"
    assert profile.tts.id == "f5-tts-dry-run"
    assert "--dry-run" in profile.separation.command
    assert "--dry-run" in profile.asr.command
    assert "--dry-run" in profile.tts.command


def test_real_tts_cosyvoice_profile_uses_cosyvoice_command() -> None:
    profile = LocalCommandPipelineProfiles.model_validate(
        json.loads(
            Path("examples/local_command_profiles.real_tts_cosyvoice.json").read_text(
                encoding="utf-8"
            )
        )
    )

    assert profile.tts.id == "cosyvoice3-local"
    assert "examples/local_commands/cosyvoice_tts.py" in profile.tts.command
    assert "--model-dir" in profile.tts.command
    assert "models/tts/Fun-CosyVoice3-0.5B" in profile.tts.command
    assert "--dry-run" not in profile.tts.command


def test_real_tts_f5_profile_uses_f5_command_without_dry_run() -> None:
    profile = LocalCommandPipelineProfiles.model_validate(
        json.loads(Path("examples/local_command_profiles.real_tts_f5.json").read_text(encoding="utf-8"))
    )

    assert profile.tts.id == "f5-tts-local"
    assert "examples/local_commands/f5_tts_command.py" in profile.tts.command
    assert "--dry-run" not in profile.tts.command
