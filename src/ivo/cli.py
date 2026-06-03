from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from ivo import __version__
from ivo.adapters.http import ApiAdapterProfile
from ivo.adapters.profiles import AdapterProfileStore
from ivo.core.project import DubbingProject
from ivo.core.timeline import SourceLanguage, TargetLanguage
from ivo.environment import collect_environment_diagnostics, collect_optional_model_dependencies
from ivo.models.manager import ModelManager
from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles, run_local_command_preview
from ivo.pipeline.mock_pipeline import run_mock_dubbing_pipeline
from ivo.pipeline.synthesize import HttpTtsAdapter
from ivo.pipeline.transcribe import HttpAsrAdapter, HttpDiarizationAdapter
from ivo.pipeline.translate import HttpTranslationAdapter

app = typer.Typer(help="Intelligent Voice Over developer tools.", no_args_is_help=True)
adapter_app = typer.Typer(help="Manage custom HTTP model API adapter profiles.")
model_app = typer.Typer(help="Manage local model profiles.")
app.add_typer(adapter_app, name="adapter")
app.add_typer(model_app, name="model")


@app.callback()
def main() -> None:
    """Command line entrypoint."""


@app.command()
def doctor() -> None:
    """Report local development environment status."""
    diagnostics = collect_environment_diagnostics()
    typer.echo(f"Intelligent Voice Over: {__version__}")
    typer.echo(f"Python: {diagnostics.python_version}")
    typer.echo(
        f"FFmpeg: {'found at ' + diagnostics.ffmpeg_path if diagnostics.ffmpeg_path else 'not found'}"
    )
    typer.echo(f"FFmpeg hint: {diagnostics.ffmpeg_hint}")
    typer.echo(
        "NVIDIA: "
        f"{'found at ' + diagnostics.nvidia_smi_path if diagnostics.nvidia_smi_path else 'not found'}"
    )
    typer.echo(f"NVIDIA hint: {diagnostics.nvidia_hint}")


@app.command("doctor-models")
def doctor_models() -> None:
    """Report optional local model bridge dependencies."""
    for dependency in collect_optional_model_dependencies():
        status = "installed" if dependency.installed else "missing"
        typer.echo(f"{dependency.name}: {status} ({dependency.install_hint})")


@app.command("mock-preview")
def mock_preview(
    source_video: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    output_dir: Annotated[Path, typer.Argument(file_okay=False)],
    project_name: Annotated[str, typer.Option()] = "Mock Preview",
    source_language: Annotated[SourceLanguage, typer.Option()] = "en",
) -> None:
    """Create a project and run the built-in mock dubbing pipeline."""
    output_dir.mkdir(parents=True, exist_ok=True)
    project = DubbingProject.create(
        output_dir / f"{project_name}.ivoproj",
        name=project_name,
        source_language=source_language,
        target_language="zh",
    )
    result = run_mock_dubbing_pipeline(project, source_video=source_video)
    typer.echo(f"Mock preview created: {result.final_video}")


@app.command("local-preview")
def local_preview(
    source_video: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    output_dir: Annotated[Path, typer.Argument(file_okay=False)],
    profiles_path: Annotated[
        Path,
        typer.Option(
            "--profiles",
            exists=True,
            dir_okay=False,
            readable=True,
            help="JSON file containing separation/asr/tts local command profiles.",
        ),
    ],
    project_name: Annotated[str, typer.Option()] = "Local Preview",
    source_language: Annotated[SourceLanguage, typer.Option()] = "en",
    target_language: Annotated[TargetLanguage, typer.Option()] = "zh",
    target_text: Annotated[list[str] | None, typer.Option("--target-text")] = None,
    asr_profile: Annotated[
        Path | None,
        typer.Option("--asr-profile", exists=True, dir_okay=False, readable=True),
    ] = None,
    asr_var: Annotated[list[str] | None, typer.Option("--asr-var")] = None,
    diarization_profile: Annotated[
        Path | None,
        typer.Option("--diarization-profile", exists=True, dir_okay=False, readable=True),
    ] = None,
    diarization_var: Annotated[list[str] | None, typer.Option("--diarization-var")] = None,
    translation_profile: Annotated[
        Path | None,
        typer.Option("--translation-profile", exists=True, dir_okay=False, readable=True),
    ] = None,
    translation_var: Annotated[list[str] | None, typer.Option("--translation-var")] = None,
    tts_profile: Annotated[
        Path | None,
        typer.Option("--tts-profile", exists=True, dir_okay=False, readable=True),
    ] = None,
    tts_var: Annotated[list[str] | None, typer.Option("--tts-var")] = None,
    ffmpeg_path: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    watermark: Annotated[bool, typer.Option("--watermark/--no-watermark")] = True,
) -> None:
    """Create a project and run local command adapters from a profile JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    project = DubbingProject.create(
        output_dir / f"{project_name}.ivoproj",
        name=project_name,
        source_language=source_language,
        target_language=target_language,
    )
    profiles = LocalCommandPipelineProfiles.model_validate(
        json.loads(profiles_path.read_text(encoding="utf-8"))
    )
    asr_extra: dict[str, object] = {
        key: value for key, value in _parse_key_value_options(asr_var or []).items()
    }
    diarization_extra: dict[str, object] = {
        key: value for key, value in _parse_key_value_options(diarization_var or []).items()
    }
    translation_extra: dict[str, object] = {
        key: value for key, value in _parse_key_value_options(translation_var or []).items()
    }
    tts_extra: dict[str, object] = {
        key: value for key, value in _parse_key_value_options(tts_var or []).items()
    }
    translation_adapter = (
        HttpTranslationAdapter(
            ApiAdapterProfile.model_validate(
                json.loads(translation_profile.read_text(encoding="utf-8"))
            ),
            project_path=project.path,
            target_language=target_language,
            extra=translation_extra,
        )
        if translation_profile is not None
        else None
    )
    asr_adapter = (
        HttpAsrAdapter(
            ApiAdapterProfile.model_validate(json.loads(asr_profile.read_text(encoding="utf-8"))),
            project_path=project.path,
            extra=asr_extra,
        )
        if asr_profile is not None
        else None
    )
    diarization_adapter = (
        HttpDiarizationAdapter(
            ApiAdapterProfile.model_validate(
                json.loads(diarization_profile.read_text(encoding="utf-8"))
            ),
            project_path=project.path,
            extra=diarization_extra,
        )
        if diarization_profile is not None
        else None
    )
    tts_adapter = (
        HttpTtsAdapter(
            ApiAdapterProfile.model_validate(json.loads(tts_profile.read_text(encoding="utf-8"))),
            project_path=project.path,
            extra=tts_extra,
        )
        if tts_profile is not None
        else None
    )
    result = run_local_command_preview(
        project,
        source_video=source_video,
        profiles=profiles,
        translation_overrides=_parse_key_value_options(target_text or []),
        asr_adapter=asr_adapter,
        diarization_adapter=diarization_adapter,
        translation_adapter=translation_adapter,
        tts_adapter=tts_adapter,
        ffmpeg_path=str(ffmpeg_path) if ffmpeg_path is not None else None,
        watermark_text="AI Dubbed" if watermark else None,
    )
    typer.echo(f"Local preview created: {result.final_video}")


@adapter_app.command("add-http")
def adapter_add_http(
    store_path: Annotated[Path, typer.Argument(dir_okay=False)],
    profile_id: Annotated[str, typer.Option("--id")],
    stage: Annotated[str, typer.Option()],
    url: Annotated[str, typer.Option()],
    method: Annotated[str, typer.Option()] = "POST",
    response: Annotated[list[str] | None, typer.Option("--response")] = None,
) -> None:
    """Add a simple HTTP adapter profile to a JSON store."""
    response_mapping = _parse_key_value_options(response or [])
    profile = ApiAdapterProfile(
        id=profile_id,
        stage=stage,
        method=method,  # type: ignore[arg-type]
        url=url,
        headers={},
        request_template={
            "prompt": "{{ prompt }}",
            "text": "{{ segment_text }}",
            "source_language": "{{ source_language }}",
            "target_language": "{{ target_language }}",
            "speaker_id": "{{ speaker_id }}",
        },
        response_mapping=response_mapping,
    )
    store = AdapterProfileStore(store_path)
    profiles = [existing for existing in store.load() if existing.id != profile.id]
    profiles.append(profile)
    store.save(profiles)
    typer.echo(f"Saved adapter profile: {profile.id}")


@adapter_app.command("list")
def adapter_list(store_path: Annotated[Path, typer.Argument(dir_okay=False)]) -> None:
    """List configured HTTP adapter profiles."""
    profiles = AdapterProfileStore(store_path).load()
    if not profiles:
        typer.echo("No adapter profiles configured.")
        return
    for profile in profiles:
        typer.echo(f"{profile.id}\t{profile.stage}\t{profile.method}\t{profile.url}")


@model_app.command("add-local")
def model_add_local(
    store_path: Annotated[Path, typer.Argument(dir_okay=False)],
    model_id: Annotated[str, typer.Option("--id")],
    stage: Annotated[str, typer.Option()],
    name: Annotated[str, typer.Option()],
    path: Annotated[Path, typer.Option(exists=True, file_okay=False)],
    language: Annotated[list[str] | None, typer.Option("--language")] = None,
    confirm_license: Annotated[bool, typer.Option()] = False,
) -> None:
    """Register a local model path without bundling model weights."""
    manager = ModelManager.from_store(store_path)
    manager.register_local_model(
        model_id=model_id,
        stage=stage,
        name=name,
        path=path,
        languages=language or [],
    )
    if confirm_license:
        manager.licenses.confirm(model_id)
    manager.save()
    typer.echo(f"Saved local model profile: {model_id}")


@model_app.command("list")
def model_list(store_path: Annotated[Path, typer.Argument(dir_okay=False)]) -> None:
    """List local and configured model profiles."""
    manager = ModelManager.from_store(store_path)
    profiles = manager.registry.list_all()
    if not profiles:
        typer.echo("No model profiles configured.")
        return
    for profile in profiles:
        license_status = "yes" if manager.can_use(profile.id) else "no"
        typer.echo(f"{profile.id}\t{profile.stage}\t{profile.backend}\tlicense: {license_status}")


def _parse_key_value_options(options: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for option in options:
        key, separator, value = option.partition("=")
        if not separator or not key or not value:
            raise typer.BadParameter(f"Expected KEY=VALUE, got: {option}")
        parsed[key] = value
    return parsed


if __name__ == "__main__":
    app()
