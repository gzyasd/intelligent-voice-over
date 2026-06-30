from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import pytest


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


def test_f5_worker_adapter_surfaces_stderr_on_crash(tmp_path: Path) -> None:
    """worker 启动后立即崩溃并向 stderr 输出错误时，adapter 应把 stderr 尾部包含在异常里。"""
    from ivo.pipeline.f5_tts_worker_adapter import F5TtsWorkerAdapter

    # 构造一个会立即往 stderr 打印错误并退出的假 worker 脚本
    fake_worker = tmp_path / "crash_worker.py"
    fake_worker.write_text(
        textwrap.dedent(
            """
            import sys
            sys.stderr.write("CUDA out of memory: tried to allocate 2.0 GiB\\n")
            sys.stderr.flush()
            sys.exit(1)
            """
        ),
        encoding="utf-8",
    )

    adapter = F5TtsWorkerAdapter(
        python_executable=sys.executable,
        worker_script=fake_worker,
        model_dir=tmp_path / "model",
        vocoder_dir=tmp_path / "vocoder",
        device="cpu",
        dry_run=True,
    )

    with pytest.raises(RuntimeError) as exc_info:
        adapter.synthesize(
            text="x",
            speaker_id="SPEAKER_00",
            output_path=tmp_path / "out.wav",
            style_prompt=None,
            reference_audio_path=None,
            reference_text="",
            target_duration_ms=1000,
            speech_rate=1.0,
        )
    adapter.close()

    message = str(exc_info.value)
    assert "F5-TTS worker" in message
    assert "CUDA out of memory" in message
