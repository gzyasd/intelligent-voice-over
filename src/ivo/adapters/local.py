from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable
from inspect import Parameter, signature
from pathlib import Path
from typing import Any

from jinja2 import StrictUndefined
from jinja2.sandbox import SandboxedEnvironment
from pydantic import BaseModel, Field

from ivo.adapters.base import AdapterContext, AdapterError, AdapterResult, MockStageAdapter
from ivo.subprocess_utils import hidden_subprocess_kwargs

CommandRunner = Callable[..., None]
CommandOutputCallback = Callable[["CommandExecutionLog"], None]


class CommandExecutionLog(BaseModel):
    stage: str
    provider: str
    command: list[str]
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0


class LocalCommandProfile(BaseModel):
    id: str
    stage: str
    command: list[str]
    output_json_path: str
    extra: dict[str, Any] = Field(default_factory=dict)


class LocalCommandAdapter:
    def __init__(
        self,
        profile: LocalCommandProfile,
        *,
        runner: CommandRunner | None = None,
        command_output_callback: CommandOutputCallback | None = None,
    ) -> None:
        self.profile = profile
        self.stage = profile.stage
        self.provider = profile.id
        self.runner = runner
        self.command_output_callback = command_output_callback
        self._environment = SandboxedEnvironment(undefined=StrictUndefined, autoescape=False)

    def validate_config(self) -> None:
        if not self.profile.command:
            raise ValueError("local command cannot be empty")

    def run(self, context: AdapterContext) -> AdapterResult:
        values = context.template_values()
        values.update(self.profile.extra)
        if not getattr(sys, "frozen", False):
            values.setdefault("python_executable", sys.executable)
        missing_interpreter = _missing_interpreter_variable(self.profile.command, values)
        if missing_interpreter is not None:
            return self._error(
                _missing_interpreter_message(missing_interpreter),
            )
        values["output_json_path"] = self._render_string(self.profile.output_json_path, values)
        command = [self._render_string(part, values) for part in self.profile.command]
        output_path = Path(str(values["output_json_path"]))
        working_dir = str(values["working_dir"]) if values.get("working_dir") else None
        env = _build_subprocess_env(working_dir)

        self._emit_command_output(
            command,
            stdout="",
            stderr="",
            exit_code=-1,
        )
        try:
            if self.runner is None:
                completed = subprocess.run(
                    command,
                    check=True,
                    capture_output=True,
                    text=True,
                    cwd=working_dir,
                    env=env,
                    **hidden_subprocess_kwargs(),
                )
                self._emit_command_output(
                    command,
                    stdout=completed.stdout,
                    stderr=completed.stderr,
                    exit_code=completed.returncode,
                )
            else:
                _run_with_optional_cwd(self.runner, command, working_dir)
            if not output_path.is_file():
                return self._error(
                    f"output JSON not found: {output_path}",
                    command=command,
                    output_path=output_path,
                )
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                return self._error(
                    "output JSON must be an object",
                    command=command,
                    output_path=output_path,
                )
            return AdapterResult(
                stage=self.stage,
                provider=self.provider,
                ok=True,
                payload=payload,
            )
        except subprocess.CalledProcessError as exc:
            self._emit_command_output(
                command,
                stdout=exc.stdout or "",
                stderr=exc.stderr or "",
                exit_code=exc.returncode,
            )
            return self._error(
                "local command failed",
                command=command,
                output_path=output_path,
                returncode=exc.returncode,
                stderr=exc.stderr,
            )
        except (OSError, json.JSONDecodeError) as exc:
            return self._error(str(exc), command=command, output_path=output_path)

    def _render_string(self, template: str, variables: dict[str, Any]) -> str:
        return self._environment.from_string(template).render(**variables)

    def _error(
        self,
        message: str,
        *,
        command: list[str] | None = None,
        output_path: Path | None = None,
        returncode: int | None = None,
        stderr: str | bytes | None = None,
    ) -> AdapterResult:
        stderr_summary = _summarize_stderr(stderr)
        output_json_path = str(output_path) if output_path is not None else None
        return AdapterResult(
            stage=self.stage,
            provider=self.provider,
            ok=False,
            error=AdapterError(
                provider=self.provider,
                stage=self.stage,
                message=self._format_error_message(
                    message,
                    command=command,
                    output_path=output_path,
                    returncode=returncode,
                    stderr_summary=stderr_summary,
                ),
                retryable=False,
                command=command,
                exit_code=returncode,
                stderr_summary=stderr_summary or None,
                output_json_path=output_json_path,
            ),
        )

    def _emit_command_output(
        self,
        command: list[str],
        *,
        stdout: str | bytes | None,
        stderr: str | bytes | None,
        exit_code: int,
    ) -> None:
        if self.command_output_callback is None:
            return
        self.command_output_callback(
            CommandExecutionLog(
                stage=self.stage,
                provider=self.provider,
                command=command,
                stdout=_decode_output(stdout),
                stderr=_decode_output(stderr),
                exit_code=exit_code,
            )
        )

    def _format_error_message(
        self,
        message: str,
        *,
        command: list[str] | None,
        output_path: Path | None,
        returncode: int | None,
        stderr_summary: str,
    ) -> str:
        lines = [
            message,
            f"stage: {self.stage}",
            f"provider: {self.provider}",
        ]
        if returncode is not None:
            lines.append(f"exit code: {returncode}")
        if command is not None:
            lines.append(f"command: {' '.join(command)}")
        if output_path is not None:
            lines.append(f"output JSON: {output_path}")
        if stderr_summary:
            lines.append(f"stderr: {stderr_summary}")
        return "\n".join(lines)


def _summarize_stderr(stderr: str | bytes | None) -> str:
    if stderr is None:
        return ""
    if isinstance(stderr, bytes):
        text = stderr.decode("utf-8", errors="replace")
    else:
        text = stderr
    return " ".join(text.split())[:500]


def _decode_output(output: str | bytes | None) -> str:
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output


def _run_with_optional_cwd(
    runner: CommandRunner,
    command: list[str],
    cwd: str | None,
) -> None:
    parameters = signature(runner).parameters
    accepts_kwargs = any(
        parameter.kind == Parameter.VAR_KEYWORD
        for parameter in parameters.values()
    )
    if accepts_kwargs or "cwd" in parameters:
        runner(command, cwd=cwd)
        return
    runner(command)


def _build_subprocess_env(working_dir: str | None) -> dict[str, str]:
    env = os.environ.copy()
    if working_dir is None:
        return env
    ffmpeg_bin = _find_bundled_ffmpeg_bin(Path(working_dir))
    if ffmpeg_bin is None:
        return env
    current_path = env.get("PATH", "")
    entries = current_path.split(os.pathsep) if current_path else []
    ffmpeg_entry = str(ffmpeg_bin)
    if ffmpeg_entry not in entries:
        env["PATH"] = os.pathsep.join([ffmpeg_entry, *entries]) if entries else ffmpeg_entry
    return env


def _find_bundled_ffmpeg_bin(runtime_root: Path) -> Path | None:
    for candidate in (
        runtime_root / "_internal" / "ffmpeg" / "bin",
        runtime_root / "ffmpeg" / "bin",
        runtime_root / "_internal" / "ffmpeg",
        runtime_root / "ffmpeg",
    ):
        if (candidate / "ffmpeg.exe").is_file() or (candidate / "ffmpeg").is_file():
            return candidate
    return None


def _missing_interpreter_variable(
    command: list[str],
    values: dict[str, Any],
) -> str | None:
    for variable_name in ("python_executable", "pyannote_python_executable"):
        marker = f"{{{{ {variable_name} }}}}"
        if any(marker in part for part in command) and not values.get(variable_name):
            return variable_name
    return None


def _missing_interpreter_message(variable_name: str) -> str:
    if variable_name == "pyannote_python_executable":
        return (
            "pyannote Python interpreter is not configured. Configure the "
            "custom pyannote Python path in Settings or set IVO_PYANNOTE_PYTHON."
        )
    return (
        "local Python interpreter is not configured. Configure the custom "
        "virtual-environment Python path in Settings or set IVO_LOCAL_PYTHON."
    )


__all__ = [
    "CommandExecutionLog",
    "LocalCommandAdapter",
    "LocalCommandProfile",
    "MockStageAdapter",
]
