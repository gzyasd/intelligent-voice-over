"""Local model service definitions for Demucs, faster-whisper, pyannote, F5-TTS, CosyVoice3.

Each local model service contains:
- Recommended model directory
- Dependency packages or dedicated venv
- GPU/CPU support information
- Minimal smoke command
- License hints for UI display
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from packaging.version import InvalidVersion, Version


def is_newer_version(latest: str, current: str) -> bool:
    if not latest or not current:
        return False
    try:
        return Version(latest) > Version(current)
    except InvalidVersion:
        return False


@dataclass
class DependencyStatus:
    """Status of a single dependency package."""

    package_name: str
    import_name: str
    status: str  # "installed", "missing", "broken"
    version: str = ""  # Empty if missing
    latest_version: str = ""  # Empty if unknown; populated asynchronously
    venv_name: str = ".venv"  # Which venv it belongs to
    pip_install_hint: str = ""

    @property
    def can_upgrade(self) -> bool:
        return is_newer_version(self.latest_version, self.version)

    @property
    def action_label(self) -> str:
        if self.status == "missing":
            return "安装"
        if self.status == "broken":
            return "修复"
        if self.can_upgrade:
            return "升级"
        return ""


@dataclass
class LocalModelDependency:
    """Describes a Python package or runtime dependency."""

    package_name: str
    import_name: str
    pip_install_hint: str = ""
    requires_cuda: bool = False
    optional: bool = False


@dataclass
class LocalModelService:
    """Definition of a local model service."""

    provider_key: str
    display_name: str
    stage: str  # separation, asr, diarization, tts
    model_dir_name: str  # Relative to models/ root
    model_dir_aliases: list[str] = field(default_factory=list)
    default_device: str = "auto"  # auto, cuda, cpu
    supported_devices: list[str] = field(default_factory=lambda: ["auto", "cuda", "cpu"])
    precision_options: list[str] = field(default_factory=lambda: ["auto", "float16", "float32", "int8"])
    dependencies: list[LocalModelDependency] = field(default_factory=list)
    license_name: str = ""
    license_url: str = ""
    license_notes: str = ""  # UI-visible license hint
    commercial_ok: bool | None = None  # None = unknown
    huggingface_repo: str = ""
    source_url: str = ""
    smoke_command: list[str] = field(default_factory=list)
    extra_info: dict[str, str] = field(default_factory=dict)
    recommended: bool = False  # 是否为该阶段的推荐模型
    tags: list[str] = field(default_factory=list)  # UI 标签：推荐/快速/高质量/测试

    def check_model_dir(self, models_root: Path) -> bool:
        """Check if the model directory exists under models_root."""
        return self.resolve_model_path(models_root).is_dir()

    def candidate_model_paths(self, models_root: Path) -> list[Path]:
        """Return supported model directory locations under models_root."""
        names = [self.model_dir_name, *self.model_dir_aliases]
        return [models_root / name for name in names]

    def resolve_model_path(self, models_root: Path) -> Path:
        """Return the first existing model path, or the canonical path."""
        candidates = self.candidate_model_paths(models_root)
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return candidates[0]

    def check_dependencies(
        self,
        *,
        custom_pythons: dict[str, Path] | None = None,
    ) -> list[str]:
        """Return list of missing dependency package names.

        Checks the current Python environment first, then falls back to
        external venvs (.venv-pyannote for pyannote.audio, .venv for others)
        located next to the executable (frozen) or project root (dev).
        """
        missing: list[str] = []
        for dep in self.dependencies:
            if _is_importable(dep.import_name):
                continue
            # Try external venvs (works in both frozen and dev mode)
            venv_python = _find_venv_python_for_dep(dep, custom_pythons=custom_pythons)
            if venv_python is not None and _is_importable_in_python(dep.import_name, venv_python):
                continue
            missing.append(dep.package_name)
        return missing

    def check_dependency_status(
        self,
        *,
        custom_pythons: dict[str, Path] | None = None,
    ) -> list[DependencyStatus]:
        """Return detailed status for each dependency.

        Checks importability and version in the appropriate venv.
        """
        results: list[DependencyStatus] = []
        for dep in self.dependencies:
            venv_name = _VENV_MAPPING.get(dep.import_name, ".venv")
            venv_python = _find_venv_python_for_dep(dep, custom_pythons=custom_pythons)

            # Determine which python to check
            check_python: Path | None = None
            if _is_importable(dep.import_name):
                # Available in current process
                check_python = Path(sys.executable)
            elif venv_python is not None and _is_importable_in_python(dep.import_name, venv_python):
                check_python = venv_python

            if check_python is None:
                # Not importable anywhere — check if package is installed but broken
                version = _get_package_version(dep.package_name, venv_python or Path(sys.executable))
                if version:
                    results.append(DependencyStatus(
                        package_name=dep.package_name,
                        import_name=dep.import_name,
                        status="broken",
                        version=version,
                        venv_name=venv_name,
                        pip_install_hint=dep.pip_install_hint,
                    ))
                else:
                    results.append(DependencyStatus(
                        package_name=dep.package_name,
                        import_name=dep.import_name,
                        status="missing",
                        venv_name=venv_name,
                        pip_install_hint=dep.pip_install_hint,
                    ))
            else:
                version = _get_package_version(dep.package_name, check_python)
                results.append(DependencyStatus(
                    package_name=dep.package_name,
                    import_name=dep.import_name,
                    status="installed",
                    version=version,
                    venv_name=venv_name,
                    pip_install_hint=dep.pip_install_hint,
                ))
        return results

    def readiness_check(self, models_root: Path) -> LocalModelReadinessResult:
        """Perform a comprehensive readiness check."""
        model_exists = self.check_model_dir(models_root)
        missing_deps = self.check_dependencies()

        messages: list[str] = []
        status = "ready"

        if not model_exists:
            status = "missing"
            if self.huggingface_repo:
                messages.append(
                    f"Model directory '{self.model_dir_name}' not found. "
                    f"Download from: {self.huggingface_repo}"
                )
            else:
                messages.append(f"Model directory '{self.model_dir_name}' not found.")

        if missing_deps:
            status = "missing"
            for pkg in missing_deps:
                dep = next((d for d in self.dependencies if d.package_name == pkg), None)
                hint = dep.pip_install_hint if dep else f"pip install {pkg}"
                messages.append(f"Missing dependency: {pkg}. Install: {hint}")

        if self.license_notes:
            messages.append(f"License: {self.license_notes}")

        return LocalModelReadinessResult(
            provider_key=self.provider_key,
            stage=self.stage,
            status=status,
            model_dir_exists=model_exists,
            missing_dependencies=missing_deps,
            messages=messages,
        )


@dataclass
class LocalModelReadinessResult:
    """Result of a local model readiness check."""

    provider_key: str
    stage: str
    status: str  # ready, missing, warning
    model_dir_exists: bool
    missing_dependencies: list[str]
    messages: list[str]

    @property
    def is_ready(self) -> bool:
        return self.status == "ready"


# -- Built-in local model services --

DEMUCS_SERVICE = LocalModelService(
    provider_key="demucs",
    display_name="Demucs (人声分离)",
    stage="separation",
    model_dir_name="separation/demucs",
    dependencies=[
        LocalModelDependency(
            package_name="demucs",
            import_name="demucs",
            pip_install_hint="pip install demucs",
        ),
        LocalModelDependency(
            package_name="torch",
            import_name="torch",
            pip_install_hint="pip install torch",
        ),
        LocalModelDependency(
            package_name="torchaudio",
            import_name="torchaudio",
            pip_install_hint="pip install torchaudio",
        ),
        LocalModelDependency(
            package_name="soundfile",
            import_name="soundfile",
            pip_install_hint="pip install soundfile",
        ),
    ],
    license_name="MIT",
    license_url="https://github.com/facebookresearch/demucs/blob/main/LICENSE",
    license_notes="MIT License - 可商用",
    commercial_ok=True,
    source_url="https://github.com/facebookresearch/demucs",
    extra_info={"note": "官方仓库已归档但仍可用；CLI 支持 --two-stems=vocals"},
    recommended=True,
    tags=["推荐"],
)

FASTER_WHISPER_LARGE_V3_SERVICE = LocalModelService(
    provider_key="faster-whisper-large-v3",
    display_name="faster-whisper-large-v3 (高质量 ASR)",
    stage="asr",
    model_dir_name="asr/faster-whisper-large-v3",
    dependencies=[
        LocalModelDependency(
            package_name="faster-whisper",
            import_name="faster_whisper",
            pip_install_hint="pip install faster-whisper",
            requires_cuda=False,
        ),
        LocalModelDependency(
            package_name="torch",
            import_name="torch",
            pip_install_hint="pip install torch",
        ),
    ],
    license_name="MIT",
    license_url="https://huggingface.co/Systran/faster-whisper-large-v3",
    license_notes="CTranslate2 格式, MIT License - 可商用",
    commercial_ok=True,
    huggingface_repo="https://huggingface.co/Systran/faster-whisper-large-v3",
    source_url="https://github.com/SYSTRAN/faster-whisper",
    extra_info={"note": "优先 GPU，需检测 CUDA/compute_type"},
    recommended=True,
    tags=["推荐", "高质量"],
)

FASTER_WHISPER_SMALL_SERVICE = LocalModelService(
    provider_key="faster-whisper-small",
    display_name="faster-whisper-small (速度优先 ASR)",
    stage="asr",
    model_dir_name="asr/faster-whisper-small",
    dependencies=[
        LocalModelDependency(
            package_name="faster-whisper",
            import_name="faster_whisper",
            pip_install_hint="pip install faster-whisper",
        ),
        LocalModelDependency(
            package_name="torch",
            import_name="torch",
            pip_install_hint="pip install torch",
        ),
    ],
    license_name="MIT",
    license_url="https://huggingface.co/Systran/faster-whisper-small",
    license_notes="CTranslate2 格式, MIT License - 可商用",
    commercial_ok=True,
    huggingface_repo="https://huggingface.co/Systran/faster-whisper-small",
    extra_info={"note": "低显存/速度优先，质量低于 large-v3"},
    tags=["速度优先"],
)

FASTER_WHISPER_TINY_SERVICE = LocalModelService(
    provider_key="faster-whisper-tiny",
    display_name="faster-whisper-tiny (快速测试 ASR)",
    stage="asr",
    model_dir_name="asr/faster-whisper-tiny",
    dependencies=[
        LocalModelDependency(
            package_name="faster-whisper",
            import_name="faster_whisper",
            pip_install_hint="pip install faster-whisper",
        ),
        LocalModelDependency(
            package_name="torch",
            import_name="torch",
            pip_install_hint="pip install torch",
        ),
    ],
    license_name="MIT",
    license_url="https://huggingface.co/Systran/faster-whisper-tiny",
    license_notes="CTranslate2 格式, MIT License - 可商用",
    commercial_ok=True,
    huggingface_repo="https://huggingface.co/Systran/faster-whisper-tiny",
    extra_info={"note": "快速 smoke 测试或极低显存兜底，正式作品质量不推荐作为默认"},
    tags=["快速测试"],
)

WHISPER_LARGE_V3_TURBO_SERVICE = LocalModelService(
    provider_key="whisper-large-v3-turbo",
    display_name="whisper-large-v3-turbo (快速 Whisper)",
    stage="asr",
    model_dir_name="asr/whisper-large-v3-turbo",
    dependencies=[
        LocalModelDependency(
            package_name="transformers",
            import_name="transformers",
            pip_install_hint="pip install transformers accelerate",
        ),
        LocalModelDependency(
            package_name="torch",
            import_name="torch",
            pip_install_hint="pip install torch",
        ),
    ],
    license_name="MIT",
    license_url="https://huggingface.co/openai/whisper-large-v3-turbo",
    license_notes="Transformers 格式模型，需独立运行时",
    commercial_ok=True,
    huggingface_repo="https://huggingface.co/openai/whisper-large-v3-turbo",
    extra_info={
        "note": (
            "官方模型是 Transformers 格式；若要走 faster-whisper，"
            "需要 CTranslate2 转换或选择已转换的模型仓库"
        )
    },
    tags=["快速"],
)

PYANNOTE_COMMUNITY_1_SERVICE = LocalModelService(
    provider_key="pyannote-community-1",
    display_name="pyannote-community-1 (说话人识别)",
    stage="diarization",
    model_dir_name="diarization/pyannote-community-1",
    dependencies=[
        LocalModelDependency(
            package_name="pyannote.audio",
            import_name="pyannote.audio",
            pip_install_hint="pip install pyannote.audio",
        ),
    ],
    license_name="MIT (code) / Academic (model)",
    license_url="https://huggingface.co/pyannote/speaker-diarization-community-1",
    license_notes="需要 Hugging Face token 和模型条款接受",
    commercial_ok=None,
    huggingface_repo="https://huggingface.co/pyannote/speaker-diarization-community-1",
    source_url="https://www.pyannote.ai/blog/community-1",
    extra_info={"note": "UI 需给出 Hugging Face 授权状态检查"},
    recommended=True,
    tags=["推荐"],
)

F5_TTS_SERVICE = LocalModelService(
    provider_key="f5-tts",
    display_name="F5-TTS (本地音色克隆)",
    stage="tts",
    model_dir_name="tts/f5-tts",
    model_dir_aliases=["tts/F5-TTS"],
    dependencies=[
        LocalModelDependency(
            package_name="f5-tts",
            import_name="f5_tts",
            pip_install_hint="pip install f5-tts",
        ),
        LocalModelDependency(
            package_name="torch",
            import_name="torch",
            pip_install_hint="pip install torch",
        ),
    ],
    license_name="CC-BY-NC (pretrained) / MIT (code)",
    license_url="https://github.com/SWivid/F5-TTS",
    license_notes="预训练权重 CC-BY-NC，非商业限制",
    commercial_ok=False,
    source_url="https://github.com/SWivid/F5-TTS",
    extra_info={"note": "预训练模型 CC-BY-NC，UI 必须提示非商业限制"},
    recommended=True,
    tags=["推荐", "音色克隆"],
)

COSYVOICE3_SERVICE = LocalModelService(
    provider_key="cosyvoice3",
    display_name="CosyVoice3 (多语种 TTS)",
    stage="tts",
    model_dir_name="tts/cosyvoice3",
    model_dir_aliases=["tts/Fun-CosyVoice3-0.5B"],
    dependencies=[
        LocalModelDependency(
            package_name="cosyvoice",
            import_name="cosyvoice",
            pip_install_hint="按 CosyVoice 官方仓库安装",
        ),
        LocalModelDependency(
            package_name="modelscope",
            import_name="modelscope",
            pip_install_hint="pip install modelscope",
        ),
    ],
    license_name="Varies by model",
    license_url="https://github.com/FunAudioLLM/CosyVoice",
    license_notes="需按模型卡核实具体权重许可",
    commercial_ok=None,
    source_url="https://github.com/FunAudioLLM/CosyVoice",
    extra_info={
        "note": "默认支持 FunAudioLLM/Fun-CosyVoice3-0.5B-2512，不对商业可用性做默认承诺",
    },
    tags=["多语种"],
)

# Registry of all built-in local model services
ALL_LOCAL_MODEL_SERVICES: list[LocalModelService] = [
    DEMUCS_SERVICE,
    FASTER_WHISPER_LARGE_V3_SERVICE,
    FASTER_WHISPER_SMALL_SERVICE,
    FASTER_WHISPER_TINY_SERVICE,
    WHISPER_LARGE_V3_TURBO_SERVICE,
    PYANNOTE_COMMUNITY_1_SERVICE,
    F5_TTS_SERVICE,
    COSYVOICE3_SERVICE,
]


def get_local_service(provider_key: str) -> LocalModelService | None:
    """Look up a local model service by provider_key."""
    for service in ALL_LOCAL_MODEL_SERVICES:
        if service.provider_key == provider_key:
            return service
    return None


def list_local_services_for_stage(stage: str) -> list[LocalModelService]:
    """Return all local model services for a given pipeline stage."""
    return [s for s in ALL_LOCAL_MODEL_SERVICES if s.stage == stage]


def compute_shared_dep_counts() -> dict[str, int]:
    """Return {package_name: count_of_models_using_it}.

    Used by UI to show "shared by N models" hint for common dependencies
    like torch (used by 6 models) and faster-whisper (used by 3 ASR models).
    """
    counts: dict[str, int] = {}
    for svc in ALL_LOCAL_MODEL_SERVICES:
        for dep in svc.dependencies:
            counts[dep.package_name] = counts.get(dep.package_name, 0) + 1
    return counts


# ── Venv-aware import checking helpers ──────────────────────────────────────

# pyannote.audio lives in .venv-pyannote; everything else in .venv
_VENV_MAPPING: dict[str, str] = {
    "pyannote.audio": ".venv-pyannote",
}


def _is_importable(import_name: str) -> bool:
    """Check if a module can be imported in the current process."""
    try:
        __import__(import_name)
    except (ImportError, ModuleNotFoundError):
        return False
    return True


def _is_importable_in_python(import_name: str, python_executable: Path) -> bool:
    """Check if a module can be imported in an external Python interpreter."""
    code = f"from importlib import import_module; import_module({import_name!r})"
    try:
        result = subprocess.run(
            [str(python_executable), "-c", code],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _get_package_version(package_name: str, python_executable: Path) -> str:
    """Get installed version of a package via importlib.metadata in the target Python."""
    code = (
        "import importlib.metadata as m; "
        f"v=m.version({package_name!r}); print(v)"
    )
    try:
        result = subprocess.run(
            [str(python_executable), "-c", code],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _get_latest_version(package_name: str, mirror_url: str = "") -> str:
    """Get latest version from PyPI JSON API, with optional mirror fallback.

    Always tries official PyPI first for accuracy; falls back to mirror
    if mirror_url is provided and official PyPI is unreachable.
    """
    import json
    import urllib.request

    urls = [f"https://pypi.org/pypi/{package_name}/json"]
    if mirror_url:
        # Derive JSON API base from mirror simple index URL
        json_base = mirror_url.rstrip("/").removesuffix("/simple").rstrip("/")
        if json_base:
            urls.append(f"{json_base}/pypi/{package_name}/json")

    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ivo"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data: dict[str, object] = json.loads(resp.read())
                info = data.get("info")
                if isinstance(info, dict):
                    version = info.get("version", "")
                    return str(version) if version else ""
        except Exception:
            continue
    return ""


def find_venv_python(
    venv_name: str,
    *,
    custom_python: Path | None = None,
) -> Path | None:
    """Find the Python executable in a venv by name.

    Searches for .venv-pyannote or .venv next to the executable (frozen)
    or at the project root (dev mode).

    优先级：
    1. custom_python 参数（用户在设置中配置的自定义路径）
    2. IVO_LOCAL_PYTHON 环境变量（用户显式指定 Python 解释器路径）
    3. frozen 模式下 resources/ 目录中的 venv
    4. dev 模式下项目根目录中的 venv
    """
    # 优先使用自定义路径（来自 UserSettings）
    if custom_python is not None and Path(custom_python).is_file():
        return Path(custom_python)

    # 其次读取环境变量（与 resolve_local_python 保持一致）
    env_var = (
        "IVO_PYANNOTE_PYTHON"
        if venv_name == ".venv-pyannote"
        else "IVO_LOCAL_PYTHON"
    )
    configured = os.getenv(env_var)
    if configured and Path(configured).is_file():
        return Path(configured)

    exe_dir = Path(sys.executable).resolve().parent

    # Candidate base directories to search
    candidates: list[Path] = [exe_dir]

    # Electron 打包后: resources/python/ivo-server.exe
    # .venv 和 .venv-pyannote 通过 extraResources 复制到 resources/
    if getattr(sys, "frozen", False):
        candidates.append(exe_dir.parent)  # resources/

    # In dev mode (running from .venv/Scripts/python.exe), the project root
    # is typically two levels up from the Scripts directory.
    # Detect this by checking for pyvenv.cfg in the parent.
    if (exe_dir.parent / "pyvenv.cfg").is_file():
        candidates.append(exe_dir.parent.parent)

    for base in candidates:
        venv_python = base / venv_name / "Scripts" / "python.exe"
        if venv_python.is_file():
            return venv_python
    return None


def _find_venv_python_for_dep(
    dep: LocalModelDependency,
    *,
    custom_pythons: dict[str, Path] | None = None,
) -> Path | None:
    """Find the Python executable in the appropriate venv for a dependency."""
    venv_name = _VENV_MAPPING.get(dep.import_name, ".venv")
    custom_python: Path | None = None
    if custom_pythons is not None:
        custom_python = custom_pythons.get(venv_name)
    return find_venv_python(venv_name, custom_python=custom_python)
