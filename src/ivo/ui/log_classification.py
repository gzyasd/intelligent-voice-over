from __future__ import annotations

from dataclasses import dataclass

from ivo.adapters.local import CommandExecutionLog


@dataclass(frozen=True)
class DisplayLogEntry:
    level: str
    title: str
    text: str
    full_text: str | None = None


def classify_command_log(log: CommandExecutionLog) -> list[DisplayLogEntry]:
    """Classify a CommandExecutionLog into display entries with semantic levels."""
    command = " ".join(log.command)
    entries: list[DisplayLogEntry] = []
    stdout = log.stdout.strip()
    stderr = log.stderr.strip()

    def full_command_text(title: str, body: str) -> str:
        lines = [
            f"[{log.stage}] {title}：{log.provider}",
            f"命令：{command}",
        ]
        if log.exit_code:
            lines.append(f"退出码：{log.exit_code}")
        if log.stdout.strip():
            lines.append("stdout:")
            lines.append(log.stdout.strip())
        if log.stderr.strip():
            lines.append("stderr:")
            lines.append(log.stderr.strip())
        if not log.stderr.strip() and (not log.stdout.strip() or log.exit_code):
            lines.append(body)
        return "\n".join(lines)

    if stdout:
        entries.append(
            DisplayLogEntry(
                level="info",
                title="命令输出",
                text=f"[{log.stage}] 命令输出：{log.provider}\n命令：{command}\n{stdout}",
                full_text=full_command_text("命令输出", stdout),
            )
        )

    if log.exit_code:
        failure_output = stderr or "没有错误输出。命令以非 0 退出码结束，请检查上方命令输出或运行环境。"
        entries.append(
            DisplayLogEntry(
                level="error",
                title="命令执行失败",
                text=(
                    f"[{log.stage}] 命令执行失败：{log.provider}\n"
                    f"退出码：{log.exit_code}\n"
                    f"命令：{command}\n"
                    f"{failure_output}"
                ),
                full_text=full_command_text("命令执行失败", failure_output),
            )
        )
        return entries

    if not stderr:
        return entries

    # Exit code 0: classify stderr by content

    if _is_tqdm_progress(stderr):
        entries.append(
            DisplayLogEntry(
                level="progress",
                title="命令进度",
                text=f"[{log.stage}] 命令进度：{log.provider}\n命令：{command}\n{stderr}",
                full_text=full_command_text("命令进度", stderr),
            )
        )
        return entries

    if _is_pyannote_torchcodec_warning(stderr):
        entries.append(
            DisplayLogEntry(
                level="warning",
                title="环境提示",
                text=(
                    f"[{log.stage}] 环境提示：{log.provider}\n"
                    f"命令：{command}\n"
                    "pyannote 检测到 torchcodec/FFmpeg DLL 不完整，内置音频解码可能不可用。\n"
                    "当前流程已使用 soundfile 预加载音频，因此这条提示通常不影响本次说话人识别。\n"
                    "如后续说话人识别失败，再检查 .venv-pyannote 中 torchcodec 与 FFmpeg 的兼容性。"
                ),
                full_text=full_command_text("环境提示", stderr),
            )
        )
        return entries

    if _is_google_python_future_warning(stderr):
        entries.append(
            DisplayLogEntry(
                level="warning",
                title="依赖提示",
                text=(
                    f"[{log.stage}] 依赖提示：{log.provider}\n"
                    f"命令：{command}\n"
                    "Google API 依赖提示 Python 3.10 未来支持周期。这不影响当前 TTS 生成。\n"
                    "项目当前约束为 Python >=3.10,<3.11，后续统一评估 Python 版本升级。"
                ),
                full_text=full_command_text("依赖提示", stderr),
            )
        )
        return entries

    # Generic stderr with exit code 0
    is_warning = _looks_like_warning(stderr)
    title = "命令警告" if is_warning else "命令附加输出"
    entries.append(
        DisplayLogEntry(
            level="warning" if is_warning else "info",
            title=title,
            text=(
                f"[{log.stage}] {title}：{log.provider}\n"
                f"命令：{command}\n"
                f"{stderr}"
            ),
            full_text=full_command_text(title, stderr),
        )
    )
    return entries


def _is_tqdm_progress(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    progress_lines = [
        line
        for line in lines
        if "%" in line
        and "|" in line
        and ("it/s" in line or "seconds/s" in line or "?it/s" in line)
    ]
    return len(progress_lines) == len(lines)


def _looks_like_warning(text: str) -> bool:
    markers = (
        "warning",
        "FutureWarning",
        "UserWarning",
        "ReproducibilityWarning",
        "warnings.warn",
    )
    lower = text.lower()
    return any(marker.lower() in lower for marker in markers)


def _is_pyannote_torchcodec_warning(text: str) -> bool:
    lower = text.lower()
    return (
        "torchcodec is not installed correctly" in lower
        and "built-in audio decoding will fail" in lower
        and "libtorchcodec" in lower
    )


def _is_google_python_future_warning(text: str) -> bool:
    lower = text.lower()
    return (
        "google" in lower
        and "api_core" in lower
        and "futurewarning" in lower
        and "python version" in lower
    )
