from __future__ import annotations

from pydantic import BaseModel
from jsonpath_ng import parse  # type: ignore[import-untyped]

from ivo.adapters.http import ApiAdapterProfile
from ivo.adapters.local import LocalCommandProfile
from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles


class LocalProfileValidationReport(BaseModel):
    ok: bool
    stages: list[str]
    errors: list[str]


class HttpProfileValidationReport(BaseModel):
    ok: bool
    stage: str
    provider: str
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


def validate_http_profile(profile: ApiAdapterProfile) -> HttpProfileValidationReport:
    errors: list[str] = []
    if not profile.response_mapping:
        errors.append("response_mapping cannot be empty")
    for output_key, expression in profile.response_mapping.items():
        try:
            parse(expression)
        except Exception:
            errors.append(f"response mapping {output_key} is not valid JSONPath")
    if profile.method == "GET" and profile.file_upload_fields:
        errors.append("GET profile cannot use file_upload_fields")
    for field_name, value_name in profile.file_upload_fields.items():
        if not field_name.strip() or not value_name.strip():
            errors.append("file_upload_fields entries must use non-empty field and variable names")
    return HttpProfileValidationReport(
        ok=not errors,
        stage=profile.stage,
        provider=profile.id,
        errors=errors,
    )


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
