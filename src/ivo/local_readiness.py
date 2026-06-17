from __future__ import annotations

import json
import shutil
from pathlib import Path

from pydantic import BaseModel, Field

from ivo.adapters.local import LocalCommandProfile
from ivo.environment import OptionalDependencyStatus, collect_optional_model_dependencies
from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles
from ivo.profile_runtime import (
    infer_local_runtime_root,
    prepare_local_command_profiles,
    resolve_local_model_root,
)


class ReadinessResult(BaseModel):
    stage: str
    provider: str
    status: str
    message: str


class LocalReadinessReport(BaseModel):
    ok: bool
    checked_profiles: list[str]
    skipped_dry_run_profiles: list[str]
    missing: list[str]
    ui_results: list[ReadinessResult] = Field(default_factory=list)


def build_local_readiness_report(
    profiles: LocalCommandPipelineProfiles,
    *,
    dependencies: list[OptionalDependencyStatus],
    nvidia_tool_available: bool | None = None,
    base_dir: Path | None = None,
) -> LocalReadinessReport:
    dependency_by_stage = _index_dependencies(dependencies)
    has_nvidia_tool = (
        shutil.which("nvidia-smi") is not None
        if nvidia_tool_available is None
        else nvidia_tool_available
    )
    checked_profiles: list[str] = []
    skipped_dry_run_profiles: list[str] = []
    missing: list[str] = []
    ui_results: list[ReadinessResult] = []

    for profile in _iter_profiles(profiles):
        label = f"{profile.stage}:{profile.id}"
        if _is_dry_run_profile(profile):
            skipped_dry_run_profiles.append(label)
            ui_results.append(
                ReadinessResult(
                    stage=profile.stage,
                    provider=profile.id,
                    status="skipped",
                    message="dry-run profile skipped",
                )
            )
            continue

        checked_profiles.append(label)
        if _uses_cuda(profile) and not has_nvidia_tool:
            message = (
                f"{profile.stage}/{profile.id}: NVIDIA tooling not detected for CUDA profile; "
                "use the CPU small profile if this machine has no NVIDIA GPU."
            )
            missing.append(message)
            ui_results.append(
                ReadinessResult(
                    stage=profile.stage,
                    provider=profile.id,
                    status="missing",
                    message=message,
                )
            )
        profile_missing = [
            *_missing_engine_command_file_messages(profile, base_dir=base_dir),
            *_missing_external_python_messages(profile, base_dir=base_dir),
        ]
        missing.extend(profile_missing)
        ui_results.extend(
            ReadinessResult(
                stage=profile.stage,
                provider=profile.id,
                status="missing",
                message=message,
            )
            for message in profile_missing
        )
        dependency_matched = False
        for dependency in dependency_by_stage.get(profile.stage, []):
            if _profile_uses_dependency(profile, dependency):
                dependency_matched = True
                dependency_missing = _missing_dependency_messages(dependency, profile)
                missing.extend(dependency_missing)
                if dependency_missing:
                    ui_results.extend(
                        ReadinessResult(
                            stage=dependency.stage,
                            provider=dependency.name,
                            status="missing",
                            message=message,
                        )
                        for message in dependency_missing
                    )
                else:
                    ui_results.append(
                        ReadinessResult(
                            stage=dependency.stage,
                            provider=dependency.name,
                            status="ok",
                            message="ready",
                        )
                    )
        if not profile_missing and not dependency_matched:
            ui_results.append(
                ReadinessResult(
                    stage=profile.stage,
                    provider=profile.id,
                    status="ok",
                    message="ready",
                )
            )

    ui_results.extend(check_optional_runtime_warning(dependencies))

    return LocalReadinessReport(
        ok=not missing,
        checked_profiles=checked_profiles,
        skipped_dry_run_profiles=skipped_dry_run_profiles,
        missing=missing,
        ui_results=ui_results,
    )


def check_profiles_readiness(
    profiles_path: Path,
    *,
    models_dir: Path,
) -> LocalReadinessReport:
    profiles = LocalCommandPipelineProfiles.model_validate(
        json.loads(profiles_path.read_text(encoding="utf-8"))
    )
    runtime_root = infer_local_runtime_root(profiles_path, models_dir=models_dir)
    model_root = resolve_local_model_root(models_dir, runtime_root)
    profiles = prepare_local_command_profiles(
        profiles,
        profiles_path=profiles_path,
        models_dir=model_root,
    )
    python_executable = profiles.separation.extra.get("python_executable")
    return build_local_readiness_report(
        profiles,
        dependencies=collect_optional_model_dependencies(
            model_root,
            python_executable=(
                Path(str(python_executable)) if python_executable is not None else None
            ),
        ),
        base_dir=runtime_root,
    )


def _iter_profiles(profiles: LocalCommandPipelineProfiles) -> list[LocalCommandProfile]:
    stage_profiles = [profiles.separation, profiles.asr, profiles.tts]
    if profiles.diarization is not None:
        stage_profiles.append(profiles.diarization)
    return stage_profiles


def _index_dependencies(
    dependencies: list[OptionalDependencyStatus],
) -> dict[str, list[OptionalDependencyStatus]]:
    indexed: dict[str, list[OptionalDependencyStatus]] = {}
    for dependency in dependencies:
        indexed.setdefault(dependency.stage, []).append(dependency)
    return indexed


def _is_dry_run_profile(profile: LocalCommandProfile) -> bool:
    return "--dry-run" in profile.command


def _uses_cuda(profile: LocalCommandProfile) -> bool:
    return any(item.lower() == "cuda" for item in profile.command)


def _profile_uses_dependency(
    profile: LocalCommandProfile,
    dependency: OptionalDependencyStatus,
) -> bool:
    command_text = " ".join(profile.command).lower()
    tokens = {
        dependency.name.lower(),
        dependency.import_name.lower(),
        dependency.import_name.replace("_", "-").lower(),
    }
    if dependency.name == "CosyVoice":
        tokens.add("cosyvoice")
    return any(token and token in command_text for token in tokens)


def _missing_dependency_messages(
    dependency: OptionalDependencyStatus,
    profile: LocalCommandProfile,
) -> list[str]:
    missing: list[str] = []
    prefix = f"{dependency.stage}/{dependency.name}"
    if dependency.model_dir_required and not dependency.model_dir_exists:
        missing.append(f"{prefix}: model dir missing")
    if not dependency.installed and not _profile_uses_external_python(profile):
        missing.append(f"{prefix}: package missing")
    if (
        dependency.required_env_var is not None
        and not dependency.env_var_set
        and not _profile_uses_local_model_dir(profile, dependency)
    ):
        missing.append(f"{prefix}: env {dependency.required_env_var} missing")
    return missing


def _profile_uses_local_model_dir(
    profile: LocalCommandProfile,
    dependency: OptionalDependencyStatus,
) -> bool:
    if not dependency.model_dir_exists:
        return False
    model_dir = str(dependency.model_dir).replace("\\", "/").lower()
    command_text = " ".join(profile.command).replace("\\", "/").lower()
    if model_dir in command_text:
        return True
    relative_parts = dependency.model_dir.parts[-3:]
    if not relative_parts:
        return False
    relative_model_dir = "/".join(relative_parts).lower()
    return relative_model_dir in command_text


def _profile_uses_external_python(profile: LocalCommandProfile) -> bool:
    return any(
        "python_executable" in item and item != "{{ python_executable }}"
        for item in profile.command
    )


def _missing_external_python_messages(
    profile: LocalCommandProfile,
    *,
    base_dir: Path | None,
) -> list[str]:
    missing: list[str] = []
    for item in profile.command:
        if not item.startswith("{{ ") or not item.endswith(" }}"):
            continue
        variable_name = item.removeprefix("{{ ").removesuffix(" }}").strip()
        if "python_executable" not in variable_name or variable_name == "python_executable":
            continue
        configured = profile.extra.get(variable_name)
        if not configured:
            missing.append(f"{profile.stage}/{profile.id}: external python missing: {variable_name}")
            continue
        configured_path = _resolve_runtime_path(Path(str(configured)), base_dir)
        if not configured_path.is_file():
            missing.append(
                f"{profile.stage}/{profile.id}: external python not found: {configured_path}"
            )
    return missing


def _missing_engine_command_file_messages(
    profile: LocalCommandProfile,
    *,
    base_dir: Path | None,
) -> list[str]:
    messages: list[str] = []
    for index, item in enumerate(profile.command):
        if item != "--engine-command-json-file":
            continue
        if index + 1 >= len(profile.command):
            messages.append(f"{profile.stage}/{profile.id}: engine command file path missing")
            continue
        engine_command_path = _resolve_runtime_path(Path(profile.command[index + 1]), base_dir)
        if not engine_command_path.is_file():
            messages.append(
                f"{profile.stage}/{profile.id}: engine command file missing: {engine_command_path}"
            )
    return messages


def _resolve_runtime_path(path: Path, base_dir: Path | None) -> Path:
    if path.is_absolute() or base_dir is None:
        return path
    return base_dir / path


def check_optional_runtime_warning(
    dependencies: list[OptionalDependencyStatus],
) -> list[ReadinessResult]:
    """Check for known runtime warnings in installed optional dependencies.

    Returns a list of ReadinessResult with status='warning' for each
    known runtime issue that does not block the pipeline but should be
    surfaced to the user.
    """
    results: list[ReadinessResult] = []
    for dep in dependencies:
        if not dep.installed:
            continue
        # Check for torchcodec DLL issues in pyannote venv
        if dep.venv_name == ".venv-pyannote" and dep.stage == "diarization":
            torchcodec_ok = _check_torchcodec_in_venv(dep.venv_name)
            if not torchcodec_ok:
                results.append(
                    ReadinessResult(
                        stage="diarization",
                        provider=dep.name,
                        status="warning",
                        message=(
                            "torchcodec/FFmpeg DLL 不完整，内置音频解码可能不可用。"
                            "当前流程已使用 soundfile 预加载音频，通常不影响说话人识别。"
                            "如后续说话人识别失败，请检查 .venv-pyannote 中 torchcodec 与 FFmpeg 的兼容性。"
                        ),
                    )
                )
    return results


def _check_torchcodec_in_venv(venv_name: str) -> bool:
    """Return True if torchcodec imports successfully in the given venv."""
    import subprocess

    for base in (Path.cwd(), Path(__file__).resolve().parents[3]):
        python = base / venv_name / "Scripts" / "python.exe"
        if not python.is_file():
            continue
        try:
            result = subprocess.run(
                [str(python), "-c", "import torchcodec"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False
    return True
