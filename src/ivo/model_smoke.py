from __future__ import annotations

import math
import json
import subprocess
import sys
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path

from ivo.workspace_paths import default_work_dir


@dataclass(frozen=True)
class AsrSmokeProbeResult:
    audio_path: Path
    output_path: Path
    command: list[str]


@dataclass(frozen=True)
class LocalAdapterSmokeProbeResult:
    output_path: Path
    work_dir: Path
    probes: list[dict[str, object]]


def run_asr_smoke_probe(
    *,
    output_path: Path,
    adapter_script: Path = Path("examples/local_commands/faster_whisper_asr.py"),
    language: str = "en",
    model: str = "tiny",
    device: str = "cpu",
    compute_type: str = "int8",
    dry_run: bool = False,
) -> AsrSmokeProbeResult:
    """Generate a tiny WAV and run the faster-whisper command adapter contract."""
    script = adapter_script.resolve()
    if not script.is_file():
        raise FileNotFoundError(f"ASR adapter script not found: {script}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    audio_path = _write_probe_wav()
    command = [
        sys.executable,
        str(script),
        "--audio",
        str(audio_path),
        "--language",
        language,
        "--model",
        model,
        "--device",
        device,
        "--compute-type",
        compute_type,
        "--out",
        str(output_path),
    ]
    if dry_run:
        command.append("--dry-run")
    subprocess.run(command, check=True)
    return AsrSmokeProbeResult(audio_path=audio_path, output_path=output_path, command=command)


def run_local_adapter_smoke_probe(
    *,
    output_path: Path,
    separation_script: Path = Path("examples/local_commands/demucs_separate.py"),
    asr_script: Path = Path("examples/local_commands/faster_whisper_asr.py"),
    f5_tts_script: Path = Path("examples/local_commands/f5_tts_command.py"),
    cosyvoice_tts_script: Path = Path("examples/local_commands/cosyvoice_tts.py"),
) -> LocalAdapterSmokeProbeResult:
    work_dir = default_work_dir() / "smoke" / "adapters" / uuid.uuid4().hex
    audio_path = _write_probe_wav(work_dir / "input.wav")
    probes: list[dict[str, object]] = []

    separation_json = work_dir / "separation.json"
    vocals_path = work_dir / "vocals.wav"
    background_path = work_dir / "background.wav"
    _run_command(
        [
            sys.executable,
            str(_require_script(separation_script)),
            "--audio",
            str(audio_path),
            "--vocals-out",
            str(vocals_path),
            "--background-out",
            str(background_path),
            "--json-out",
            str(separation_json),
            "--dry-run",
        ]
    )
    probes.append(
        {
            "stage": "separation",
            "provider": "demucs",
            "json_path": str(separation_json),
            "artifacts": [str(vocals_path), str(background_path)],
        }
    )

    asr_json = work_dir / "asr.json"
    _run_command(
        [
            sys.executable,
            str(_require_script(asr_script)),
            "--audio",
            str(vocals_path),
            "--language",
            "en",
            "--out",
            str(asr_json),
            "--dry-run",
        ]
    )
    probes.append(
        {
            "stage": "asr",
            "provider": "faster-whisper",
            "json_path": str(asr_json),
            "artifacts": [],
        }
    )

    f5_audio = work_dir / "f5-tts.wav"
    f5_json = work_dir / "f5-tts.json"
    _run_command(
        [
            sys.executable,
            str(_require_script(f5_tts_script)),
            "--text",
            "你好。",
            "--speaker",
            "speaker-1",
            "--audio-out",
            str(f5_audio),
            "--json-out",
            str(f5_json),
            "--duration-ms",
            "500",
            "--dry-run",
        ]
    )
    probes.append(
        {
            "stage": "tts",
            "provider": "f5-tts",
            "json_path": str(f5_json),
            "artifacts": [str(f5_audio)],
        }
    )

    cosyvoice_model_dir = work_dir / "cosyvoice-model"
    cosyvoice_model_dir.mkdir(parents=True, exist_ok=True)
    cosyvoice_audio = work_dir / "cosyvoice-tts.wav"
    cosyvoice_json = work_dir / "cosyvoice-tts.json"
    _run_command(
        [
            sys.executable,
            str(_require_script(cosyvoice_tts_script)),
            "--text",
            "你好。",
            "--speaker",
            "speaker-1",
            "--model-dir",
            str(cosyvoice_model_dir),
            "--audio-out",
            str(cosyvoice_audio),
            "--json-out",
            str(cosyvoice_json),
            "--duration-ms",
            "500",
            "--dry-run",
        ]
    )
    probes.append(
        {
            "stage": "tts",
            "provider": "cosyvoice",
            "json_path": str(cosyvoice_json),
            "artifacts": [str(cosyvoice_audio)],
        }
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "work_dir": str(work_dir),
                "probes": probes,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return LocalAdapterSmokeProbeResult(
        output_path=output_path,
        work_dir=work_dir,
        probes=probes,
    )


def default_asr_smoke_output_path() -> Path:
    return default_work_dir() / "smoke" / "asr" / "asr-smoke.json"


def default_adapter_smoke_output_path() -> Path:
    return default_work_dir() / "smoke" / "adapters" / "adapter-smoke.json"


def _write_probe_wav(output_path: Path | None = None) -> Path:
    sample_rate = 16_000
    duration_seconds = 1.5
    audio_path = output_path or default_work_dir() / "smoke" / "asr" / uuid.uuid4().hex / "input.wav"
    audio_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(audio_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = bytearray()
        for sample_index in range(int(sample_rate * duration_seconds)):
            sample = int(
                0.2
                * 32767
                * math.sin(2 * math.pi * 440 * sample_index / sample_rate)
            )
            frames.extend(sample.to_bytes(2, "little", signed=True))
        wav.writeframes(bytes(frames))
    return audio_path


def _require_script(script: Path) -> Path:
    resolved = script.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Local command script not found: {resolved}")
    return resolved


def _run_command(command: list[str]) -> None:
    subprocess.run(command, check=True)
