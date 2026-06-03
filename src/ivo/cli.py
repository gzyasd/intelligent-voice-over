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
from ivo.evaluation import build_project_evaluation_report, render_evaluation_markdown
from ivo.models.manager import ModelManager
from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles, run_local_command_preview
from ivo.pipeline.mock_pipeline import run_mock_dubbing_pipeline
from ivo.pipeline.separate_audio import HttpSeparationAdapter
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
def doctor_models(
    models_dir: Annotated[
        Path,
        typer.Option("--models-dir", file_okay=False, help="Local model cache root to inspect."),
    ] = Path("models"),
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output machine-readable model diagnostics."),
    ] = False,
) -> None:
    """Report optional local model bridge dependencies."""
    dependencies = collect_optional_model_dependencies(models_dir)
    if json_output:
        typer.echo(
            json.dumps(
                [dependency.model_dump(mode="json") for dependency in dependencies],
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    for dependency in dependencies:
        status = "installed" if dependency.installed else "missing"
        model_status = "found" if dependency.model_dir_exists else "missing"
        typer.echo(f"{dependency.stage} / {dependency.name}: {status}")
        typer.echo(f"  import: {dependency.import_name}")
        typer.echo(f"  install: {dependency.install_hint}")
        typer.echo(f"  model dir: {dependency.model_dir} ({model_status})")
        typer.echo(f"  download: {dependency.download_hint}")
        typer.echo(f"  license: {dependency.license_hint}")
        typer.echo(f"  verify: {dependency.verify_hint}")


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


@app.command("batch-mock-preview")
def batch_mock_preview(
    input_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False, readable=True)],
    output_dir: Annotated[Path, typer.Argument(file_okay=False)],
    source_language: Annotated[SourceLanguage, typer.Option()] = "en",
    watermark: Annotated[bool, typer.Option("--watermark/--no-watermark")] = True,
) -> None:
    """Run mock preview for every video file in a directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    video_paths = [
        path
        for path in sorted(input_dir.iterdir())
        if path.is_file() and path.suffix.lower() in {".mp4", ".mkv", ".mov", ".avi"}
    ]
    for source_video in video_paths:
        project = DubbingProject.create(
            output_dir / f"{source_video.stem}.ivoproj",
            name=source_video.stem,
            source_language=source_language,
            target_language="zh",
            source_video=source_video,
        )
        result = run_mock_dubbing_pipeline(
            project,
            source_video=source_video,
            watermark_text="AI Dubbed" if watermark else "",
        )
        typer.echo(f"{source_video.name}: {result.final_video}")
    typer.echo(f"Processed {len(video_paths)} videos")


@app.command("evaluate-project")
def evaluate_project(
    project_path: Annotated[Path, typer.Argument(exists=True, file_okay=False, readable=True)],
    output_format: Annotated[
        str,
        typer.Option("--format", help="Output format: markdown or json."),
    ] = "markdown",
    output: Annotated[
        Path | None,
        typer.Option("--output", dir_okay=False, help="Optional report output path."),
    ] = None,
) -> None:
    """Summarize timeline quality flags, statuses, and job records for a project."""
    project = DubbingProject.load(project_path)
    report = build_project_evaluation_report(project)
    if output_format == "json":
        rendered = report.model_dump_json(indent=2)
    elif output_format == "markdown":
        rendered = render_evaluation_markdown(report)
    else:
        raise typer.BadParameter("Expected --format markdown or json")

    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        typer.echo(f"Evaluation report written: {output}")
        return
    typer.echo(rendered)


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
            help="JSON file containing local command profiles for the dubbing pipeline.",
        ),
    ],
    project_name: Annotated[str, typer.Option()] = "Local Preview",
    source_language: Annotated[SourceLanguage, typer.Option()] = "en",
    target_language: Annotated[TargetLanguage, typer.Option()] = "zh",
    target_text: Annotated[list[str] | None, typer.Option("--target-text")] = None,
    separation_profile: Annotated[
        Path | None,
        typer.Option("--separation-profile", exists=True, dir_okay=False, readable=True),
    ] = None,
    separation_var: Annotated[list[str] | None, typer.Option("--separation-var")] = None,
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
    separation_extra: dict[str, object] = {
        key: value for key, value in _parse_key_value_options(separation_var or []).items()
    }
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
    separation_adapter = (
        HttpSeparationAdapter(
            ApiAdapterProfile.model_validate(
                json.loads(separation_profile.read_text(encoding="utf-8"))
            ),
            project_path=project.path,
            extra=separation_extra,
        )
        if separation_profile is not None
        else None
    )
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
        separation_adapter=separation_adapter,
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
    optional_response: Annotated[list[str] | None, typer.Option("--optional-response")] = None,
    file_upload: Annotated[list[str] | None, typer.Option("--file-upload")] = None,
) -> None:
    """Add a simple HTTP adapter profile to a JSON store."""
    response_mapping = _parse_key_value_options(response or [])
    file_upload_fields = _parse_key_value_options(file_upload or [])
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
        optional_response_keys=optional_response or [],
        file_upload_fields=file_upload_fields,
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


@model_app.command("setup-plan")
def model_setup_plan(
    models_dir: Annotated[
        Path,
        typer.Option("--models-dir", file_okay=False, help="Local model cache root to inspect."),
    ] = Path("models"),
    stage: Annotated[
        str | None,
        typer.Option("--stage", help="Only show setup plan entries for one stage."),
    ] = None,
) -> None:
    """Print install/download/verify steps for recommended local model dependencies."""
    dependencies = collect_optional_model_dependencies(models_dir)
    for dependency in dependencies:
        if stage is not None and dependency.stage != stage:
            continue
        package_status = "installed" if dependency.installed else "missing"
        model_status = "found" if dependency.model_dir_exists else "missing"
        typer.echo(f"{dependency.stage} / {dependency.name}")
        typer.echo(f"  package: {package_status}")
        typer.echo(f"  model dir: {dependency.model_dir} ({model_status})")
        typer.echo(f"  install: {dependency.install_hint}")
        typer.echo(f"  download: {dependency.download_hint}")
        typer.echo(f"  license: {dependency.license_hint}")
        typer.echo(f"  verify: {dependency.verify_hint}")


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
