from __future__ import annotations

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
    candidates: list[Path] = []
    if models_dir is not None:
        candidates.append(models_dir.parent)
    if profiles_path.parent.name.lower() == "examples":
        candidates.append(profiles_path.parent.parent)
    candidates.append(profiles_path.parent)
    candidates.append(Path.cwd())

    for candidate in candidates:
        if (candidate / "examples" / "local_commands").is_dir():
            return candidate
    return candidates[0]


def prepare_local_command_profiles(
    profiles: LocalCommandPipelineProfiles,
    *,
    profiles_path: Path,
    models_dir: Path | None = None,
) -> LocalCommandPipelineProfiles:
    runtime_root = infer_local_runtime_root(profiles_path, models_dir=models_dir)
    python_executable = resolve_local_python(runtime_root)
    for profile in _iter_profiles(profiles):
        profile.extra.setdefault("working_dir", str(runtime_root))
        if python_executable is not None:
            profile.extra.setdefault("python_executable", str(python_executable))
        _resolve_extra_path(profile.extra, "pyannote_python_executable", runtime_root)
    return profiles


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
