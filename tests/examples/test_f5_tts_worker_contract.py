from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_f5_tts_worker_dry_run_contract(tmp_path: Path) -> None:
    worker = Path("examples/local_commands/f5_tts_worker.py")
    output = tmp_path / "seg-001.wav"

    process = subprocess.Popen(
        [sys.executable, str(worker), "--dry-run"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    assert process.stdin is not None
    assert process.stdout is not None

    request = {
        "id": "seg-001",
        "text": "你好",
        "speaker": "SPEAKER_00",
        "audio_out": str(output),
        "duration_ms": 1000,
        "speed": 0.9,
        "reference_audio": "",
        "reference_text": "",
    }
    process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
    process.stdin.write(json.dumps({"type": "shutdown"}) + "\n")
    process.stdin.flush()

    response = json.loads(process.stdout.readline())
    process.wait(timeout=5)

    assert process.returncode == 0
    assert response["ok"] is True
    assert response["id"] == "seg-001"
    assert response["audio_path"] == str(output)
    assert response["duration_ms"] == 1000
    assert output.is_file()
