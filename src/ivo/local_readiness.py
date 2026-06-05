from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from ivo.adapters.local import LocalCommandProfile
from ivo.environment import OptionalDependencyStatus
from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles


class LocalReadinessReport(BaseModel):
    ok: bool
    checked_profiles: list[str]
    skipped_dry_run_profiles: list[str]
    missing: list[str]


def build_local_readiness_report(
    profiles: LocalCommandPipelineProfiles,
    *,
    dependencies: list[OptionalDependencyStatus],
) -> LocalReadinessReport:
    dependency_by_stage = _index_dependencies(dependencies)
    checked_profiles: list[str] = []
    skipped_dry_run_profiles: list[str] = []
    missing: list[str] = []

    for profile in _iter_profiles(profiles):
        label = f"{profile.stage}:{profile.id}"
        if _is_dry_run_profile(profile):
            skipped_dry_run_profiles.append(label)
            continue

        checked_profiles.append(label)
        missing.extend(_missing_engine_command_file_messages(profile))
        for dependency in dependency_by_stage.get(profile.stage, []):
            if _profile_uses_dependency(profile, dependency):
                missing.extend(_missing_dependency_messages(dependency))

    return LocalReadinessReport(
        ok=not missing,
        checked_profiles=checked_profiles,
        skipped_dry_run_profiles=skipped_dry_run_profiles,
        missing=missing,
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


def _missing_dependency_messages(dependency: OptionalDependencyStatus) -> list[str]:
    missing: list[str] = []
    prefix = f"{dependency.stage}/{dependency.name}"
    if not dependency.installed:
        missing.append(f"{prefix}: package missing")
    if dependency.model_dir_required and not dependency.model_dir_exists:
        missing.append(f"{prefix}: model dir missing")
    if dependency.required_env_var is not None and not dependency.env_var_set:
        missing.append(f"{prefix}: env {dependency.required_env_var} missing")
    return missing


def _missing_engine_command_file_messages(profile: LocalCommandProfile) -> list[str]:
    messages: list[str] = []
    for index, item in enumerate(profile.command):
        if item != "--engine-command-json-file":
            continue
        if index + 1 >= len(profile.command):
            messages.append(f"{profile.stage}/{profile.id}: engine command file path missing")
            continue
        engine_command_path = Path(profile.command[index + 1])
        if not engine_command_path.is_file():
            messages.append(
                f"{profile.stage}/{profile.id}: engine command file missing: {engine_command_path}"
            )
    return messages
