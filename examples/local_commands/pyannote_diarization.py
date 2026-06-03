from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def main() -> int:
    parser = argparse.ArgumentParser(description="Speaker diarization adapter for pyannote.audio.")
    parser.add_argument("--audio", required=True)
    parser.add_argument("--model", default="pyannote/speaker-diarization-community-1")
    parser.add_argument("--hf-token-env", default="HF_TOKEN")
    parser.add_argument("--out", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    audio = Path(args.audio)
    if not audio.is_file():
        raise FileNotFoundError(audio)

    if args.dry_run:
        write_contract(
            Path(args.out),
            [{"start_ms": 0, "end_ms": 1200, "speaker_id": "speaker-1"}],
        )
        return 0

    token = os.getenv(args.hf_token_env)
    if not token:
        raise SystemExit(
            f"Missing Hugging Face token env var: {args.hf_token_env}. "
            "Run huggingface-cli login or set the token in the current shell, "
            "and accept the pyannote model terms before using this adapter."
        )

    try:
        from pyannote.audio import Pipeline  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: pyannote.audio. Install it in the command environment before "
            "running this adapter, for example: uv pip install pyannote.audio"
        ) from exc

    pipeline = Pipeline.from_pretrained(args.model, use_auth_token=token)
    diarization = pipeline(str(audio))
    segments: list[dict[str, Any]] = []
    for turn, _track, speaker in diarization.itertracks(yield_label=True):
        segments.append(
            {
                "start_ms": int(turn.start * 1000),
                "end_ms": int(turn.end * 1000),
                "speaker_id": str(speaker),
            }
        )
    write_contract(Path(args.out), segments)
    return 0


def write_contract(output_path: Path, segments: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"segments": segments}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
