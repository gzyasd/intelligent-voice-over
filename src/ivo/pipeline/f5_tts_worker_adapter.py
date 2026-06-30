from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Callable, IO

from ivo.subprocess_utils import hidden_subprocess_kwargs


class F5TtsWorkerAdapter:
    max_parallelism = 1

    def __init__(
        self,
        *,
        python_executable: str,
        worker_script: Path,
        model_dir: Path,
        vocoder_dir: Path | None = None,
        device: str = "auto",
        dry_run: bool = False,
        on_process_start: Callable[[list[str]], None] | None = None,
    ) -> None:
        self.python_executable = python_executable
        self.worker_script = worker_script
        self.model_dir = model_dir
        self.vocoder_dir = vocoder_dir
        self.device = device
        self.dry_run = dry_run
        self.on_process_start = on_process_start
        self._process: subprocess.Popen[str] | None = None

    def synthesize(
        self,
        *,
        text: str,
        speaker_id: str,
        output_path: Path,
        style_prompt: str | None,
        reference_audio_path: Path | None,
        reference_text: str,
        target_duration_ms: int,
        speech_rate: float,
    ) -> int:
        process = self._ensure_process()
        stdin = _require_pipe(process.stdin)
        stdout = _require_pipe(process.stdout)
        request = {
            "id": output_path.stem,
            "text": text,
            "speaker": speaker_id,
            "audio_out": str(output_path),
            "style_prompt": style_prompt or "",
            "reference_audio": str(reference_audio_path or ""),
            "reference_text": reference_text,
            "duration_ms": target_duration_ms,
            "speed": speech_rate,
        }
        stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
        stdin.flush()
        response_line = stdout.readline()
        if not response_line:
            raise RuntimeError("F5-TTS worker exited without a response")
        response = json.loads(response_line)
        if not response.get("ok"):
            raise RuntimeError(str(response.get("error") or "F5-TTS worker failed"))
        audio_path = Path(str(response.get("audio_path") or output_path))
        if audio_path != output_path:
            output_path.write_bytes(audio_path.read_bytes())
        if not output_path.is_file():
            raise RuntimeError(f"F5-TTS worker output audio not found: {output_path}")
        return int(response.get("duration_ms") or target_duration_ms)

    def close(self) -> None:
        process = self._process
        self._process = None
        if process is None:
            return
        if process.poll() is None and process.stdin is not None:
            try:
                process.stdin.write(json.dumps({"type": "shutdown"}) + "\n")
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def _ensure_process(self) -> subprocess.Popen[str]:
        if self._process is not None and self._process.poll() is None:
            return self._process
        command = [
            self.python_executable,
            str(self.worker_script),
            "--model-dir",
            str(self.model_dir),
            "--device",
            self.device,
        ]
        if self.vocoder_dir is not None:
            command.extend(["--vocoder-dir", str(self.vocoder_dir)])
        if self.dry_run:
            command.append("--dry-run")
        if self.on_process_start is not None:
            self.on_process_start(command)
        self._process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            **hidden_subprocess_kwargs(),
        )
        return self._process

    def __enter__(self) -> F5TtsWorkerAdapter:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()


def _require_pipe(pipe: IO[str] | None) -> IO[str]:
    if pipe is None:
        raise RuntimeError("F5-TTS worker pipe is unavailable")
    return pipe
