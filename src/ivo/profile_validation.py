from __future__ import annotations

from pydantic import BaseModel

from ivo.adapters.local import LocalCommandProfile
from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles


class LocalProfileValidationReport(BaseModel):
    ok: bool
    stages: list[str]
    errors: list[str]


def validate_local_command_profiles(profiles: LocalCommandPipelineProfiles) -> LocalProfileValidationReport:
    stage_profiles = [
        profiles.separation,
        profiles.asr,
        *([profiles.diarization] if profiles.diarization is not None else []),
        profiles.tts,
    ]
    errors: list[str] = []
    stages: list[str] = []
    for profile in stage_profiles:
        stages.append(profile.stage)
        errors.extend(_validate_profile(profile))
    return LocalProfileValidationReport(ok=not errors, stages=stages, errors=errors)


def _validate_profile(profile: LocalCommandProfile) -> list[str]:
    errors: list[str] = []
    if not profile.command:
        errors.append(f"{profile.stage} command cannot be empty")
    rendered_command = " ".join(profile.command)
    if "{{ output_json_path }}" not in rendered_command:
        errors.append(f"{profile.stage} command should include {{{{ output_json_path }}}}")
    if not profile.output_json_path:
        errors.append(f"{profile.stage} output_json_path cannot be empty")
    return errors
