from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


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
            sys.executable,
            "-m",
            "demucs.separate",
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
            subprocess.run(command, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
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
