from __future__ import annotations

import sys
from pathlib import Path


def test_f5_worker_adapter_reuses_one_process_for_multiple_segments(tmp_path: Path) -> None:
    from ivo.pipeline.f5_tts_worker_adapter import F5TtsWorkerAdapter

    starts: list[list[str]] = []
    adapter = F5TtsWorkerAdapter(
        python_executable=sys.executable,
        worker_script=Path("examples/local_commands/f5_tts_worker.py"),
        model_dir=tmp_path / "model",
        vocoder_dir=tmp_path / "vocoder",
        device="cpu",
        dry_run=True,
        on_process_start=starts.append,
    )

    first = adapter.synthesize(
        text="一",
        speaker_id="SPEAKER_00",
        output_path=tmp_path / "one.wav",
        style_prompt=None,
        reference_audio_path=None,
        reference_text="",
        target_duration_ms=1000,
        speech_rate=0.9,
    )
    second = adapter.synthesize(
        text="二",
        speaker_id="SPEAKER_00",
        output_path=tmp_path / "two.wav",
        style_prompt=None,
        reference_audio_path=None,
        reference_text="",
        target_duration_ms=1200,
        speech_rate=0.9,
    )
    adapter.close()

    assert first == 1000
    assert second == 1200
    assert len(starts) == 1
