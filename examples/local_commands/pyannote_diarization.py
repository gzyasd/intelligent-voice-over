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
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
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

    model_reference = resolve_model_reference(args.model)
    uses_local_model = Path(model_reference).exists()
    token = os.getenv(args.hf_token_env)
    if not token and not uses_local_model:
        raise SystemExit(
            f"Missing Hugging Face token env var: {args.hf_token_env}. "
            "Run huggingface-cli login or set the token in the current shell, "
            "accept the pyannote model terms, or pass a local model directory."
        )

    try:
        patch_torchaudio_metadata_type()
        from pyannote.audio import Pipeline  # type: ignore[import-not-found]
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency: pyannote.audio. Install it in the command environment before "
            "running this adapter, for example in .venv-pyannote with pyannote.audio>=4,<5"
        ) from exc

    pipeline = (
        Pipeline.from_pretrained(model_reference, use_auth_token=token)
        if token
        else Pipeline.from_pretrained(model_reference)
    )
    device = resolve_device(args.device)
    if device is not None:
        pipeline.to(device)
    diarization = pipeline(load_audio_in_memory(audio))
    segments = normalize_diarization_output(diarization)
    write_contract(Path(args.out), segments)
    return 0


def write_contract(output_path: Path, segments: list[dict[str, Any]]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps({"segments": segments}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def normalize_diarization_output(diarization: Any) -> list[dict[str, Any]]:
    annotation = getattr(diarization, "exclusive_speaker_diarization", None)
    if annotation is None:
        annotation = getattr(diarization, "speaker_diarization", None)
    if annotation is None:
        annotation = diarization

    segments: list[dict[str, Any]] = []
    if hasattr(annotation, "itertracks"):
        for turn, _track, speaker in annotation.itertracks(yield_label=True):
            segments.append(_segment_to_dict(turn, speaker))
        return segments

    for item in annotation:
        if len(item) != 2:
            continue
        turn, speaker = item
        segments.append(_segment_to_dict(turn, speaker))
    return segments


def _segment_to_dict(turn: Any, speaker: Any) -> dict[str, Any]:
    return {
        "start_ms": int(turn.start * 1000),
        "end_ms": int(turn.end * 1000),
        "speaker_id": str(speaker),
    }


def resolve_model_reference(model: str) -> str:
    model_path = Path(model)
    if model_path.is_dir():
        config_path = model_path / "config.yaml"
        if not config_path.is_file():
            raise FileNotFoundError(config_path)
        return str(config_path)
    return model


def resolve_device(device: str) -> Any | None:
    try:
        import torch
    except ImportError:
        return None
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested for pyannote diarization but torch.cuda is unavailable")
    return torch.device(device)


def load_audio_in_memory(audio: Path) -> dict[str, Any]:
    import soundfile as sf
    import torch

    waveform, sample_rate = sf.read(str(audio), always_2d=True, dtype="float32")
    tensor = torch.from_numpy(waveform.T)
    return {"waveform": tensor, "sample_rate": sample_rate}


def patch_torchaudio_metadata_type() -> None:
    try:
        import torchaudio  # type: ignore[import-untyped]
    except ImportError:
        return
    if hasattr(torchaudio, "AudioMetaData"):
        pass
    else:
        torchaudio.AudioMetaData = object  # type: ignore[attr-defined]
    if not hasattr(torchaudio, "list_audio_backends"):
        torchaudio.list_audio_backends = lambda: ["soundfile"]  # type: ignore[attr-defined]


if __name__ == "__main__":
    raise SystemExit(main())
