from __future__ import annotations

import json
import subprocess
import sys
import wave


def test_faster_whisper_asr_dry_run_writes_contract(tmp_path) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake")
    output = tmp_path / "asr.json"

    subprocess.run(
        [
            sys.executable,
            "examples/local_commands/faster_whisper_asr.py",
            "--audio",
            str(audio),
            "--language",
            "en",
            "--model",
            "base",
            "--out",
            str(output),
            "--dry-run",
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["segments"][0]["id"] == "seg-001"
    assert data["segments"][0]["text"]


def test_demucs_separate_dry_run_writes_contract(tmp_path) -> None:
    source = tmp_path / "audio.wav"
    source.write_bytes(b"fake")
    vocals = tmp_path / "vocals.wav"
    background = tmp_path / "background.wav"
    output = tmp_path / "separation.json"

    subprocess.run(
        [
            sys.executable,
            "examples/local_commands/demucs_separate.py",
            "--audio",
            str(source),
            "--vocals-out",
            str(vocals),
            "--background-out",
            str(background),
            "--json-out",
            str(output),
            "--dry-run",
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["vocals_path"] == str(vocals)
    assert data["background_path"] == str(background)
    assert vocals.read_bytes() == b"fake"


def test_f5_tts_dry_run_writes_contract(tmp_path) -> None:
    audio = tmp_path / "speech.wav"
    output = tmp_path / "tts.json"

    subprocess.run(
        [
            sys.executable,
            "examples/local_commands/f5_tts_command.py",
            "--text",
            "你好。",
            "--speaker",
            "speaker-1",
            "--audio-out",
            str(audio),
            "--json-out",
            str(output),
            "--dry-run",
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["audio_path"] == str(audio)
    assert data["duration_ms"] > 0
    with wave.open(str(audio), "rb") as wav_file:
        assert wav_file.getframerate() == 16000
