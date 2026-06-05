from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
import wave
from pathlib import Path


def test_tts_engine_command_examples_are_valid_json_arrays() -> None:
    for path in (
        Path("examples/engine_commands/f5_tts_engine_command.example.json"),
        Path("examples/engine_commands/f5_tts_engine_command.cuda.example.json"),
        Path("examples/engine_commands/cosyvoice_engine_command.example.json"),
    ):
        command = json.loads(path.read_text(encoding="utf-8"))

        assert isinstance(command, list)
        assert command
        assert "{text}" in command
        assert "{audio_out}" in command or (
            "{audio_out_dir}" in command and "{audio_out_name}" in command
        )


def test_cosyvoice_engine_command_can_use_audio_output_dir_and_name() -> None:
    command = json.loads(
        Path("examples/engine_commands/cosyvoice_engine_command.example.json").read_text(
            encoding="utf-8"
        )
    )

    assert "{audio_out_dir}" in command
    assert "{audio_out_name}" in command
    assert "{reference_text}" in command
    assert "{text}" in command


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


def test_demucs_separate_accepts_two_stems_option_in_dry_run(tmp_path) -> None:
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
            "--model",
            "htdemucs_ft",
            "--two-stems",
            "vocals",
            "--dry-run",
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["vocals_path"] == str(vocals)
    assert data["background_path"] == str(background)


def test_demucs_soundfile_save_writes_tensor_as_wav(tmp_path) -> None:
    import torch

    spec = importlib.util.spec_from_file_location(
        "demucs_separate", "examples/local_commands/demucs_separate.py"
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    output = tmp_path / "vocals.wav"
    module.save_wav_with_soundfile(
        torch.zeros((2, 1600)),
        output,
        samplerate=16000,
        clip="clamp",
        bits_per_sample=16,
        as_float=False,
    )

    with wave.open(str(output), "rb") as wav_file:
        assert wav_file.getnchannels() == 2
        assert wav_file.getframerate() == 16000
        assert wav_file.getnframes() == 1600


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


def test_f5_soundfile_load_returns_torchaudio_compatible_shape(tmp_path) -> None:
    import numpy as np

    spec = importlib.util.spec_from_file_location(
        "f5_tts_command", "examples/local_commands/f5_tts_command.py"
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    audio = tmp_path / "reference.wav"
    with wave.open(str(audio), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(np.zeros((1600, 2), dtype=np.int16).tobytes())

    wav, sample_rate = module.load_audio_with_soundfile(audio)

    assert sample_rate == 16000
    assert tuple(wav.shape) == (2, 1600)


def test_pyannote_diarization_dry_run_writes_contract(tmp_path) -> None:
    audio = tmp_path / "vocals.wav"
    audio.write_bytes(b"fake")
    output = tmp_path / "diarization.json"

    subprocess.run(
        [
            sys.executable,
            "examples/local_commands/pyannote_diarization.py",
            "--audio",
            str(audio),
            "--model",
            "pyannote/speaker-diarization-community-1",
            "--hf-token-env",
            "HF_TOKEN",
            "--out",
            str(output),
            "--dry-run",
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["segments"] == [
        {"start_ms": 0, "end_ms": 1200, "speaker_id": "speaker-1"}
    ]


def test_f5_tts_command_can_delegate_to_engine_command_json(tmp_path) -> None:
    engine_script = tmp_path / "engine.py"
    engine_script.write_text(
        """
from __future__ import annotations

import argparse
import wave

parser = argparse.ArgumentParser()
parser.add_argument("--text", required=True)
parser.add_argument("--speaker", required=True)
parser.add_argument("--audio-out", required=True)
args = parser.parse_args()

with wave.open(args.audio_out, "wb") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(16000)
    wav_file.writeframes(b"\\x00\\x00" * 1600)
""",
        encoding="utf-8",
    )
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
            "--duration-ms",
            "100",
            "--engine-command-json",
            json.dumps(
                [
                    sys.executable,
                    str(engine_script),
                    "--text",
                    "{text}",
                    "--speaker",
                    "{speaker}",
                    "--audio-out",
                    "{audio_out}",
                ]
            ),
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data == {"audio_path": str(audio), "duration_ms": 100}
    with wave.open(str(audio), "rb") as wav_file:
        assert wav_file.getframerate() == 16000


def test_f5_tts_command_can_delegate_to_engine_command_json_file(tmp_path) -> None:
    engine_script = tmp_path / "engine_file.py"
    engine_script.write_text(
        """
from __future__ import annotations

import argparse
import wave

parser = argparse.ArgumentParser()
parser.add_argument("--text", required=True)
parser.add_argument("--audio-out", required=True)
args = parser.parse_args()

with wave.open(args.audio_out, "wb") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(16000)
    wav_file.writeframes(b"\\x00\\x00" * 1600)
""",
        encoding="utf-8",
    )
    command_file = tmp_path / "engine-command.json"
    command_file.write_text(
        json.dumps(
            [
                sys.executable,
                str(engine_script),
                "--text",
                "{text}",
                "--audio-out",
                "{audio_out}",
            ]
        ),
        encoding="utf-8",
    )
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
            "--duration-ms",
            "100",
            "--engine-command-json-file",
            str(command_file),
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data == {"audio_path": str(audio), "duration_ms": 100}


def test_f5_tts_engine_command_can_use_audio_output_dir_and_name(tmp_path) -> None:
    engine_script = tmp_path / "engine_dir.py"
    engine_script.write_text(
        """
from __future__ import annotations

import argparse
from pathlib import Path
import wave

parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", required=True)
parser.add_argument("--output-file", required=True)
args = parser.parse_args()

audio_out = Path(args.output_dir) / args.output_file
audio_out.parent.mkdir(parents=True, exist_ok=True)
with wave.open(str(audio_out), "wb") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(16000)
    wav_file.writeframes(b"\\x00\\x00" * 1600)
""",
        encoding="utf-8",
    )
    audio = tmp_path / "nested" / "speech.wav"
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
            "--duration-ms",
            "100",
            "--engine-command-json",
            json.dumps(
                [
                    sys.executable,
                    str(engine_script),
                    "--output-dir",
                    "{audio_out_dir}",
                    "--output-file",
                    "{audio_out_name}",
                ]
            ),
        ],
        check=True,
    )

    assert audio.is_file()
    data = json.loads(output.read_text(encoding="utf-8"))
    assert data == {"audio_path": str(audio), "duration_ms": 100}


def test_cosyvoice_tts_dry_run_writes_contract(tmp_path) -> None:
    audio = tmp_path / "speech.wav"
    output = tmp_path / "tts.json"

    subprocess.run(
        [
            sys.executable,
            "examples/local_commands/cosyvoice_tts.py",
            "--text",
            "你好。",
            "--speaker",
            "speaker-1",
            "--audio-out",
            str(audio),
            "--json-out",
            str(output),
            "--model-dir",
            "models/tts/Fun-CosyVoice3-0.5B",
            "--dry-run",
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data["audio_path"] == str(audio)
    assert data["duration_ms"] > 0
    with wave.open(str(audio), "rb") as wav_file:
        assert wav_file.getframerate() == 16000


def test_cosyvoice_tts_command_can_delegate_to_engine_command_json(tmp_path) -> None:
    engine_script = tmp_path / "cosy_engine.py"
    engine_script.write_text(
        """
from __future__ import annotations

import argparse
import wave

parser = argparse.ArgumentParser()
parser.add_argument("--text", required=True)
parser.add_argument("--model-dir", required=True)
parser.add_argument("--audio-out", required=True)
args = parser.parse_args()

with wave.open(args.audio_out, "wb") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(16000)
    wav_file.writeframes(b"\\x00\\x00" * 1600)
""",
        encoding="utf-8",
    )
    audio = tmp_path / "speech.wav"
    output = tmp_path / "tts.json"

    subprocess.run(
        [
            sys.executable,
            "examples/local_commands/cosyvoice_tts.py",
            "--text",
            "你好。",
            "--speaker",
            "speaker-1",
            "--audio-out",
            str(audio),
            "--json-out",
            str(output),
            "--duration-ms",
            "100",
            "--model-dir",
            "models/tts/Fun-CosyVoice3-0.5B",
            "--engine-command-json",
            json.dumps(
                [
                    sys.executable,
                    str(engine_script),
                    "--text",
                    "{text}",
                    "--model-dir",
                    "{model_dir}",
                    "--audio-out",
                    "{audio_out}",
                ]
            ),
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data == {"audio_path": str(audio), "duration_ms": 100}
    with wave.open(str(audio), "rb") as wav_file:
        assert wav_file.getframerate() == 16000


def test_cosyvoice_tts_command_can_delegate_to_engine_command_json_file(tmp_path) -> None:
    engine_script = tmp_path / "cosy_engine_file.py"
    engine_script.write_text(
        """
from __future__ import annotations

import argparse
import wave

parser = argparse.ArgumentParser()
parser.add_argument("--text", required=True)
parser.add_argument("--model-dir", required=True)
parser.add_argument("--audio-out", required=True)
args = parser.parse_args()

with wave.open(args.audio_out, "wb") as wav_file:
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(16000)
    wav_file.writeframes(b"\\x00\\x00" * 1600)
""",
        encoding="utf-8",
    )
    command_file = tmp_path / "cosy-engine-command.json"
    command_file.write_text(
        json.dumps(
            [
                sys.executable,
                str(engine_script),
                "--text",
                "{text}",
                "--model-dir",
                "{model_dir}",
                "--audio-out",
                "{audio_out}",
            ]
        ),
        encoding="utf-8",
    )
    audio = tmp_path / "speech.wav"
    output = tmp_path / "tts.json"

    subprocess.run(
        [
            sys.executable,
            "examples/local_commands/cosyvoice_tts.py",
            "--text",
            "你好。",
            "--speaker",
            "speaker-1",
            "--audio-out",
            str(audio),
            "--json-out",
            str(output),
            "--duration-ms",
            "100",
            "--model-dir",
            "models/tts/Fun-CosyVoice3-0.5B",
            "--engine-command-json-file",
            str(command_file),
        ],
        check=True,
    )

    data = json.loads(output.read_text(encoding="utf-8"))
    assert data == {"audio_path": str(audio), "duration_ms": 100}
