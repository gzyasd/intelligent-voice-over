from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass
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
    stage: str
    import_name: str
    installed: bool
    install_hint: str
    download_hint: str
    license_hint: str
    model_dir: Path
    model_dir_exists: bool
    model_dir_required: bool = True
    verify_hint: str
    required_env_var: str | None = None
    env_var_set: bool | None = None


@dataclass(frozen=True)
class OptionalDependencySpec:
    name: str
    stage: str
    import_name: str
    install_hint: str
    download_hint: str
    license_hint: str
    model_subdir: Path
    verify_hint: str
    model_dir_required: bool = True
    required_env_var: str | None = None


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


def collect_optional_model_dependencies(
    model_root: Path | str = Path("models"),
) -> list[OptionalDependencyStatus]:
    root = Path(model_root)
    dependencies = [
        OptionalDependencySpec(
            name="faster-whisper",
            stage="asr",
            import_name="faster_whisper",
            install_hint="uv pip install faster-whisper",
            download_hint=(
                "huggingface-cli download Systran/faster-whisper-large-v3 "
                "--local-dir models/asr/faster-whisper-large-v3"
            ),
            license_hint="MIT package; confirm the selected Whisper checkpoint license.",
            model_subdir=Path("asr") / "faster-whisper-large-v3",
            verify_hint="uv run ivo model smoke-asr --dry-run",
            model_dir_required=False,
        ),
        OptionalDependencySpec(
            name="demucs",
            stage="separation",
            import_name="demucs",
            install_hint="uv sync --extra local-separation",
            download_hint="Demucs downloads named checkpoints on first use.",
            license_hint="MIT; confirm checkpoint terms before distribution.",
            model_subdir=Path("separation") / "demucs",
            verify_hint="uv run python examples/local_commands/demucs_separate.py --help",
            model_dir_required=False,
        ),
        OptionalDependencySpec(
            name="pyannote.audio",
            stage="diarization",
            import_name="pyannote.audio",
            install_hint="uv pip install pyannote.audio",
            download_hint=(
                "huggingface-cli download pyannote/speaker-diarization-community-1 "
                "--local-dir models/diarization/pyannote-community-1"
            ),
            license_hint=(
                "Requires Hugging Face login and accepted model terms; keep HF_TOKEN out of Git."
            ),
            model_subdir=Path("diarization") / "pyannote-community-1",
            verify_hint="uv run python examples/local_commands/pyannote_diarization.py --help",
            required_env_var="HF_TOKEN",
        ),
        OptionalDependencySpec(
            name="CosyVoice",
            stage="tts",
            import_name="cosyvoice",
            install_hint="install CosyVoice from https://github.com/FunAudioLLM/CosyVoice",
            download_hint=(
                "huggingface-cli download FunAudioLLM/Fun-CosyVoice3-0.5B-2512 "
                "--local-dir models/tts/Fun-CosyVoice3-0.5B"
            ),
            license_hint="Fun-CosyVoice3 model card currently lists Apache-2.0; re-check before use.",
            model_subdir=Path("tts") / "Fun-CosyVoice3-0.5B",
            verify_hint="uv run python examples/local_commands/cosyvoice_tts.py --help",
        ),
        OptionalDependencySpec(
            name="f5_tts",
            stage="tts",
            import_name="f5_tts",
            install_hint="uv sync --extra local-tts-f5",
            download_hint="huggingface-cli download SWivid/F5-TTS --local-dir models/tts/F5-TTS",
            license_hint="Code is MIT; pretrained checkpoints are CC-BY-NC.",
            model_subdir=Path("tts") / "F5-TTS",
            verify_hint="uv run f5-tts_infer-cli --help",
            model_dir_required=False,
        ),
        OptionalDependencySpec(
            name="Qwen local LLM",
            stage="translation",
            import_name="transformers",
            install_hint="uv pip install transformers accelerate",
            download_hint="huggingface-cli download Qwen/Qwen3-8B --local-dir models/llm/Qwen3-8B",
            license_hint=(
                "Confirm the selected Qwen model license before redistribution or commercial use."
            ),
            model_subdir=Path("llm") / "Qwen3-8B",
            verify_hint="Run Qwen through vLLM/SGLang/OpenAI-compatible HTTP profile first.",
        ),
        OptionalDependencySpec(
            name="vLLM",
            stage="translation",
            import_name="vllm",
            install_hint="install vLLM in a supported serving environment",
            download_hint="Uses the selected local LLM directory, for example models/llm/Qwen3-8B.",
            license_hint="Serving framework license differs from model license; confirm both.",
            model_subdir=Path("llm") / "Qwen3-8B",
            verify_hint="Start an OpenAI-compatible local server and use the HTTP translation profile.",
        ),
        OptionalDependencySpec(
            name="SGLang",
            stage="translation",
            import_name="sglang",
            install_hint="install SGLang in a supported serving environment",
            download_hint="Uses the selected local LLM directory, for example models/llm/Qwen3-8B.",
            license_hint="Serving framework license differs from model license; confirm both.",
            model_subdir=Path("llm") / "Qwen3-8B",
            verify_hint="Start an OpenAI-compatible local server and use the HTTP translation profile.",
        ),
    ]
    return [
        OptionalDependencyStatus(
            name=dependency.name,
            stage=dependency.stage,
            import_name=dependency.import_name,
            installed=_is_importable(dependency.import_name),
            install_hint=dependency.install_hint,
            download_hint=dependency.download_hint,
            license_hint=dependency.license_hint,
            model_dir=root / dependency.model_subdir,
            model_dir_exists=(root / dependency.model_subdir).is_dir(),
            model_dir_required=dependency.model_dir_required,
            verify_hint=dependency.verify_hint,
            required_env_var=dependency.required_env_var,
            env_var_set=(
                bool(getenv(dependency.required_env_var))
                if dependency.required_env_var is not None
                else None
            ),
        )
        for dependency in dependencies
    ]


def _is_importable(import_name: str) -> bool:
    try:
        return find_spec(import_name) is not None
    except ModuleNotFoundError:
        return False
