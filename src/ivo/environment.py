from __future__ import annotations

import shutil
import sys
from importlib.util import find_spec
from os import getenv
from pathlib import Path

from pydantic import BaseModel


class EnvironmentDiagnostics(BaseModel):
    python_version: str
    ffmpeg_path: str | None
    nvidia_smi_path: str | None
    ffmpeg_hint: str
    nvidia_hint: str


class OptionalDependencyStatus(BaseModel):
    name: str
    import_name: str
    installed: bool
    install_hint: str


def collect_environment_diagnostics() -> EnvironmentDiagnostics:
    ffmpeg_path = resolve_executable("ffmpeg", env_var="IVO_FFMPEG_PATH")
    nvidia_smi_path = shutil.which("nvidia-smi")
    return EnvironmentDiagnostics(
        python_version=sys.version.split()[0],
        ffmpeg_path=ffmpeg_path,
        nvidia_smi_path=nvidia_smi_path,
        ffmpeg_hint=(
            "FFmpeg 可用。"
            if ffmpeg_path
            else "未找到 FFmpeg；Windows 可尝试 winget install Gyan.FFmpeg 后重新打开终端。"
        ),
        nvidia_hint=(
            "NVIDIA GPU 工具可用。"
            if nvidia_smi_path
            else "未找到 nvidia-smi；本地高质量模型通常需要 NVIDIA 驱动和 CUDA 环境。"
        ),
    )


def resolve_executable(name: str, *, env_var: str | None = None) -> str | None:
    if env_var:
        configured = getenv(env_var)
        if configured and Path(configured).is_file():
            return configured
    return shutil.which(name)


def collect_optional_model_dependencies() -> list[OptionalDependencyStatus]:
    dependencies = [
        ("faster-whisper", "faster_whisper", "uv pip install faster-whisper"),
        ("demucs", "demucs", "uv pip install demucs"),
        (
            "f5_tts",
            "f5_tts",
            "install the F5-TTS package matching your chosen checkpoint and inference script",
        ),
    ]
    return [
        OptionalDependencyStatus(
            name=name,
            import_name=import_name,
            installed=find_spec(import_name) is not None,
            install_hint=hint,
        )
        for name, import_name, hint in dependencies
    ]
