from __future__ import annotations

import math
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AsrSmokeProbeResult:
    audio_path: Path
    output_path: Path
    command: list[str]


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


def default_asr_smoke_output_path() -> Path:
    return Path(tempfile.gettempdir()) / "ivo_asr_smoke" / "asr-smoke.json"


def _write_probe_wav() -> Path:
    sample_rate = 16_000
    duration_seconds = 1.5
    output_dir = Path(tempfile.mkdtemp(prefix="ivo-asr-smoke-"))
    audio_path = output_dir / "input.wav"
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
