from __future__ import annotations

import sys
from pathlib import Path
from collections.abc import Iterator

from ivo.adapters.local import LocalCommandProfile
from ivo.environment import resolve_local_python
from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles


def infer_local_runtime_root(
    profiles_path: Path,
    *,
    models_dir: Path | None = None,
) -> Path:
    resolved_profiles_path = profiles_path.resolve()
    candidates: list[Path] = []
    if resolved_profiles_path.parent.name.lower() == "examples":
        candidates.append(resolved_profiles_path.parent.parent)
    if models_dir is not None and models_dir.is_absolute():
        candidates.append(models_dir.resolve().parent)
    candidates.append(resolved_profiles_path.parent)
    candidates.append(Path.cwd().resolve())
    if getattr(sys, "frozen", False):
        # Electron 打包后: resources/python/ivo-server.exe
        # extraResources 把 examples 复制到 resources/examples/
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir.parent)  # resources/
        candidates.append(exe_dir / "_internal")  # PyInstaller onedir

    for candidate in candidates:
        if (candidate / "examples" / "local_commands").is_dir():
            return candidate.resolve()
    return candidates[0]


def prepare_local_command_profiles(
    profiles: LocalCommandPipelineProfiles,
    *,
    profiles_path: Path,
    models_dir: Path | None = None,
    python_executable: Path | None = None,
    pyannote_python_executable: Path | None = None,
) -> LocalCommandPipelineProfiles:
    runtime_root = infer_local_runtime_root(profiles_path, models_dir=models_dir)
    resolved_python = (
        python_executable
        if python_executable is not None and python_executable.is_file()
        else resolve_local_python(runtime_root)
    )
    resolved_pyannote = (
        pyannote_python_executable
        if pyannote_python_executable is not None
        and pyannote_python_executable.is_file()
        else None
    )
    for profile in _iter_profiles(profiles):
        profile.extra.setdefault("working_dir", str(runtime_root))
        if resolved_python is not None:
            profile.extra["python_executable"] = str(resolved_python)
        if profile.stage == "diarization" and resolved_pyannote is not None:
            profile.extra["pyannote_python_executable"] = str(resolved_pyannote)
        _resolve_extra_path(profile.extra, "pyannote_python_executable", runtime_root)
    return profiles


def resolve_local_model_root(models_dir: Path, runtime_root: Path) -> Path:
    if models_dir.is_absolute():
        return models_dir
    return runtime_root / models_dir


def _iter_profiles(profiles: LocalCommandPipelineProfiles) -> Iterator[LocalCommandProfile]:
    yield profiles.separation
    yield profiles.asr
    if profiles.diarization is not None:
        yield profiles.diarization
    yield profiles.tts


def _resolve_extra_path(extra: dict[str, object], key: str, runtime_root: Path) -> None:
    raw_value = extra.get(key)
    if raw_value is None:
        return
    path = Path(str(raw_value))
    if path.is_absolute():
        return
    extra[key] = str(runtime_root / path)
