from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, IO

from ivo.subprocess_utils import hidden_subprocess_kwargs, utf8_env


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
        self._stderr_file: IO[str] | None = None

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
        stdin.write(json.dumps(request, ensure_ascii=True) + "\n")
        stdin.flush()
        # 跳过非 JSON 行（worker 启动期间残留的日志噪声），直到读到合法 JSON 响应。
        response: dict[str, Any] | None = None
        for _ in range(100):
            response_line = stdout.readline()
            if not response_line:
                # worker 进程已退出。读取 stderr 尾部作为诊断信息，帮助定位
                # 模型加载失败、CUDA 错误等问题（stderr 默认会被 DEVNULL 丢弃）。
                raise RuntimeError(self._describe_worker_exit())
            response_line = response_line.strip()
            if not response_line:
                continue
            try:
                response = json.loads(response_line)
                break
            except json.JSONDecodeError:
                # 非 JSON 行（日志噪声），跳过继续读
                continue
        if response is None:
            raise RuntimeError(self._describe_worker_exit("no valid JSON response"))
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
                process.stdin.write(json.dumps({"type": "shutdown"}, ensure_ascii=True) + "\n")
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        if self._stderr_file is not None:
            self._stderr_file.close()
            self._stderr_file = None

    def _ensure_process(self) -> subprocess.Popen[str]:
        if self._process is not None and self._process.poll() is None:
            return self._process
        # 上一次进程已退出：关闭其 stderr 文件，准备重新捕获
        if self._stderr_file is not None:
            self._stderr_file.close()
            self._stderr_file = None
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
        # stderr 用临时文件捕获，而非 DEVNULL：worker 崩溃时（模型加载失败、CUDA OOM
        # 等）可通过读取尾部向用户暴露真实错误，避免只能看到 "exited without a response"。
        self._stderr_file = tempfile.TemporaryFile(  # noqa: SIM115 - 文件句柄由本类管理
            mode="w+", encoding="utf-8", errors="replace"
        )
        self._process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=self._stderr_file,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=utf8_env(),
            **hidden_subprocess_kwargs(),
        )
        return self._process

    def _describe_worker_exit(self, reason: str = "exited without a response") -> str:
        """构造 worker 退出错误信息，附带 stderr 尾部用于诊断。"""
        stderr_tail = self._read_stderr_tail(max_chars=2000)
        message = f"F5-TTS worker {reason}"
        if stderr_tail:
            message += f"\n--- worker stderr (tail) ---\n{stderr_tail}"
        return message

    def _read_stderr_tail(self, max_chars: int = 2000) -> str:
        if self._stderr_file is None:
            return ""
        try:
            self._stderr_file.seek(0)
            content = self._stderr_file.read()
        except (OSError, ValueError):
            return ""
        return content[-max_chars:] if len(content) > max_chars else content

    def __enter__(self) -> F5TtsWorkerAdapter:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()


def _require_pipe(pipe: IO[str] | None) -> IO[str]:
    if pipe is None:
        raise RuntimeError("F5-TTS worker pipe is unavailable")
    return pipe
