"""Subprocess runner for F5-TTS with torchaudio.load monkey-patch and trainer mock.

This script is invoked by f5_tts_command.py via subprocess to isolate
intermittent DLL loading crashes (access violation 0xC0000005).

Two critical patches are applied BEFORE importing f5_tts:
1. Mock f5_tts.model.trainer and f5_tts.model.dataset to avoid importing
   HuggingFace `datasets` -> `pyarrow` -> `arrow.dll` which crashes
   deterministically with 0xC0000005 on this environment.
   Inference does not need Trainer/DynamicBatchSampler/collate_fn.
2. Monkey-patch torchaudio.load to use soundfile instead of torchcodec
   (torchcodec DLLs are incompatible with torch cu128 nightly on Windows).

Usage:
    python _f5_tts_runner.py -- <f5-tts_infer-cli args...>
"""
from __future__ import annotations

import os
import runpy
import sys
import types

# Force offline mode before any HF-related imports
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def _mock_unneeded_training_modules() -> None:
    """Stub out f5_tts.model.trainer and f5_tts.model.dataset.

    The real trainer.py imports dataset.py which imports HuggingFace
    `datasets` -> `pyarrow` -> `arrow.dll`. The arrow.dll crashes
    deterministically with access violation 0xC0000005 on this environment
    (torch cu128 nightly + pyarrow on Windows). Inference only needs
    CFM/backbones/utils, not Trainer/DynamicBatchSampler/collate_fn.
    """
    fake_trainer = types.ModuleType("f5_tts.model.trainer")

    class FakeTrainer:
        pass

    fake_trainer.Trainer = FakeTrainer
    sys.modules["f5_tts.model.trainer"] = fake_trainer

    fake_dataset = types.ModuleType("f5_tts.model.dataset")

    def _fake_collate_fn(*args, **kwargs):
        raise RuntimeError("collate_fn should not be called during inference")

    class _FakeDynamicBatchSampler:
        pass

    fake_dataset.collate_fn = _fake_collate_fn
    fake_dataset.DynamicBatchSampler = _FakeDynamicBatchSampler
    sys.modules["f5_tts.model.dataset"] = fake_dataset


def load_audio_with_soundfile(
    uri,
    frame_offset: int = 0,
    num_frames: int = -1,
    normalize: bool = True,
    channels_first: bool = True,
    format=None,
    buffer_size: int = 4096,
    backend=None,
):
    """Load audio using soundfile instead of torchcodec.

    Drop-in replacement for torchaudio.load that bypasses the torchcodec
    DLL incompatibility with torch cu128 nightly on Windows.
    """
    import soundfile as sf
    import torch

    frames = -1 if num_frames is None or num_frames < 0 else num_frames
    data, sample_rate = sf.read(
        str(uri),
        start=frame_offset,
        frames=frames,
        dtype="float32",
        always_2d=True,
    )
    tensor = torch.from_numpy(data)
    if channels_first:
        tensor = tensor.transpose(0, 1).contiguous()
    return tensor, int(sample_rate)


def _patch_torchaudio_load() -> None:
    """Monkey-patch torchaudio.load to use soundfile instead of torchcodec.

    torchaudio 2.9+ requires torchcodec for audio loading, but torchcodec's
    DLLs fail to load with torch cu128 nightly on Windows. We bypass this
    by using soundfile directly.
    """
    import torchaudio

    torchaudio.load = load_audio_with_soundfile


def main() -> int:
    # Find "--" separator in argv
    try:
        sep_index = sys.argv.index("--")
        cli_args = sys.argv[sep_index + 1:]
    except ValueError:
        cli_args = sys.argv[1:]

    if not cli_args:
        print("Error: no F5-TTS CLI arguments provided after '--'", file=sys.stderr)
        return 1

    # Apply patches BEFORE importing f5_tts
    _mock_unneeded_training_modules()
    _patch_torchaudio_load()

    # Set up sys.argv for runpy
    sys.argv = ["f5-tts_infer-cli", *cli_args]

    try:
        runpy.run_module("f5_tts.infer.infer_cli", run_name="__main__")
        return 0
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 0
    except Exception as exc:
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
