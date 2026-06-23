from __future__ import annotations

import shutil
import sys
from pathlib import Path


GPU_F5_SMALL_PROFILE = Path("examples/local_command_profiles.real_separation_asr_tts_f5_gpu_small.json")
CPU_F5_SMALL_PROFILE = Path("examples/local_command_profiles.real_separation_asr_tts_f5_cpu_small.json")


def default_local_command_profiles_path(
    *,
    root: Path = Path("."),
    nvidia_tool_available: bool | None = None,
) -> Path | None:
    has_nvidia_tool = (
        shutil.which("nvidia-smi") is not None
        if nvidia_tool_available is None
        else nvidia_tool_available
    )
    search_roots: list[Path] = [root]
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        search_roots.append(exe_dir.parent)  # resources/
        search_roots.append(exe_dir / "_internal")  # PyInstaller onedir
        search_roots.append(exe_dir)
    for search_root in search_roots:
        gpu_path = search_root / GPU_F5_SMALL_PROFILE
        cpu_path = search_root / CPU_F5_SMALL_PROFILE
        if has_nvidia_tool and gpu_path.is_file():
            return gpu_path
        if cpu_path.is_file():
            return cpu_path
        if gpu_path.is_file():
            return gpu_path
    return None
