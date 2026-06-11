from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Voice separation command adapter for Demucs.")
    parser.add_argument("--audio", required=True)
    parser.add_argument("--vocals-out", required=True)
    parser.add_argument("--background-out", required=True)
    parser.add_argument("--json-out", required=True)
    parser.add_argument("--model", default="htdemucs")
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--two-stems", default="vocals", choices=["vocals"])
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source = Path(args.audio)
    if not source.is_file():
        raise FileNotFoundError(source)

    vocals = Path(args.vocals_out)
    background = Path(args.background_out)
    vocals.parent.mkdir(parents=True, exist_ok=True)
    background.parent.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        shutil.copy2(source, vocals)
        shutil.copy2(source, background)
        write_contract(Path(args.json_out), vocals, background)
        return 0

    with tempfile.TemporaryDirectory() as temp_dir:
        command = [
            "-n",
            args.model,
            "-d",
            args.device,
            "--two-stems",
            args.two_stems,
            "-o",
            temp_dir,
            str(source),
        ]
        try:
            run_demucs_with_soundfile_save(command)
        except (OSError, RuntimeError, SystemExit) as exc:
            raise SystemExit(
                "Demucs command failed. Install demucs and verify CUDA/audio dependencies in this "
                "environment, for example: uv pip install demucs"
            ) from exc

        produced_vocals = next(Path(temp_dir).rglob("vocals.wav"), None)
        produced_background = next(Path(temp_dir).rglob("no_vocals.wav"), None)
        if produced_vocals is None or produced_background is None:
            raise SystemExit("Demucs did not produce vocals.wav and no_vocals.wav")
        shutil.copy2(produced_vocals, vocals)
        shutil.copy2(produced_background, background)

    write_contract(Path(args.json_out), vocals, background)
    return 0


def run_demucs_with_soundfile_save(command: list[str]) -> None:
    import demucs.audio
    import demucs.separate

    demucs.audio.save_audio = save_wav_with_soundfile
    demucs.separate.save_audio = save_wav_with_soundfile
    demucs.separate.main(command)


def save_wav_with_soundfile(
    wav: Any,
    path: str | Path,
    *,
    samplerate: int,
    bitrate: int = 320,
    clip: str = "rescale",
    bits_per_sample: int = 16,
    as_float: bool = False,
    preset: int = 2,
) -> None:
    del bitrate, preset

    import soundfile as sf
    from demucs.audio import prevent_clip

    output_path = Path(path)
    if output_path.suffix.lower() != ".wav":
        raise ValueError(f"Only WAV output is supported by this adapter: {output_path}")

    clipped = prevent_clip(wav.detach().cpu(), mode=clip)
    if clipped.ndim == 1:
        samples = clipped.numpy()
    else:
        samples = clipped.transpose(0, 1).contiguous().numpy()

    subtype = "FLOAT" if as_float or bits_per_sample == 32 else f"PCM_{bits_per_sample}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), samples, samplerate, subtype=subtype)


def write_contract(output_path: Path, vocals_path: Path, background_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "vocals_path": str(vocals_path),
                "background_path": str(background_path),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
