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
from ivo.evaluation import (
    build_batch_evaluation_report,
    build_project_evaluation_report,
    render_evaluation_markdown,
)
from ivo.local_readiness import LocalReadinessReport, build_local_readiness_report
from ivo.model_setup import build_model_setup_script
from ivo.models.manager import ModelManager
from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles, run_local_command_preview
from ivo.pipeline.mock_pipeline import run_mock_dubbing_pipeline
from ivo.pipeline.separate_audio import HttpSeparationAdapter
from ivo.pipeline.synthesize import HttpTtsAdapter
from ivo.pipeline.transcribe import HttpAsrAdapter, HttpDiarizationAdapter
from ivo.pipeline.translate import HttpTranslationAdapter
from ivo.profile_validation import validate_http_profile, validate_local_command_profiles

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
    stage: Annotated[
        str | None,
        typer.Option("--stage", help="Only show diagnostics for one stage."),
    ] = None,
) -> None:
    """Report optional local model bridge dependencies."""
    dependencies = [
        dependency
        for dependency in collect_optional_model_dependencies(models_dir)
        if stage is None or dependency.stage == stage
    ]
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
        if dependency.required_env_var is not None:
            env_status = "set" if dependency.env_var_set else "missing"
            typer.echo(f"  env: {dependency.required_env_var} ({env_status})")
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


@app.command("batch-local-preview")
def batch_local_preview(
    input_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False, readable=True)],
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
    source_language: Annotated[SourceLanguage, typer.Option()] = "en",
    target_language: Annotated[TargetLanguage, typer.Option()] = "zh",
    watermark: Annotated[bool, typer.Option("--watermark/--no-watermark")] = True,
    report: Annotated[
        Path | None,
        typer.Option("--report", dir_okay=False, help="Optional JSON batch report output path."),
    ] = None,
    skip_existing: Annotated[
        bool,
        typer.Option("--skip-existing", help="Skip videos with an existing local-preview.mp4."),
    ] = False,
    models_dir: Annotated[
        Path,
        typer.Option("--models-dir", file_okay=False, help="Local model cache root to inspect."),
    ] = Path("models"),
    require_readiness: Annotated[
        bool,
        typer.Option("--require-readiness", help="Fail before creating projects if models are not ready."),
    ] = False,
    resume_existing: Annotated[
        bool,
        typer.Option(
            "--resume-existing",
            help="Load existing .ivoproj folders and resume completed stages.",
        ),
    ] = False,
) -> None:
    """Run local command preview for every video file in a directory."""
    profiles = LocalCommandPipelineProfiles.model_validate(
        json.loads(profiles_path.read_text(encoding="utf-8"))
    )
    if require_readiness:
        readiness = build_local_readiness_report(
            profiles,
            dependencies=collect_optional_model_dependencies(models_dir),
        )
        _echo_local_readiness(readiness)
        if not readiness.ok:
            raise typer.Exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    video_paths = _iter_video_paths(input_dir)
    failures: list[str] = []
    report_items: list[dict[str, object]] = []
    for source_video in video_paths:
        project_path = output_dir / f"{source_video.stem}.ivoproj"
        final_video = project_path / "renders" / "local-preview.mp4"
        if skip_existing and final_video.is_file():
            report_items.append(
                {
                    "video": str(source_video),
                    "project_path": str(project_path),
                    "status": "skipped",
                    "final_video": str(final_video),
                    "error": None,
                }
            )
            typer.echo(f"{source_video.name}: SKIPPED existing output")
            continue
        if project_path.exists() and not resume_existing:
            message = (
                f"Project already exists: {project_path}. "
                "Use --resume-existing to continue it."
            )
            failures.append(source_video.name)
            report_items.append(
                {
                    "video": str(source_video),
                    "project_path": str(project_path),
                    "status": "failed",
                    "error": message,
                }
            )
            typer.echo(f"{source_video.name}: FAILED: {message}")
            continue
        if resume_existing and project_path.is_dir():
            project = DubbingProject.load(project_path)
        else:
            project = DubbingProject.create(
                project_path,
                name=source_video.stem,
                source_language=source_language,
                target_language=target_language,
                source_video=source_video,
            )
        try:
            result = run_local_command_preview(
                project,
                source_video=source_video,
                profiles=profiles,
                watermark_text="AI Dubbed" if watermark else None,
            )
        except Exception as exc:
            failures.append(source_video.name)
            report_items.append(
                {
                    "video": str(source_video),
                    "project_path": str(project.path),
                    "status": "failed",
                    "error": str(exc),
                }
            )
            typer.echo(f"{source_video.name}: FAILED: {exc}")
            continue
        report_items.append(
            {
                "video": str(source_video),
                "project_path": str(project.path),
                "status": "completed",
                "final_video": str(result.final_video),
                "error": None,
            }
        )
        typer.echo(f"{source_video.name}: {result.final_video}")
    typer.echo(f"Processed {len(video_paths)} videos")
    if report is not None:
        _write_batch_report(report, report_items)
    if failures:
        typer.echo(f"Failed {len(failures)} of {len(video_paths)} videos")
        raise typer.Exit(1)


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


@app.command("evaluate-batch")
def evaluate_batch(
    input_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False, readable=True)],
    output: Annotated[
        Path,
        typer.Option("--output", dir_okay=False, help="JSON batch evaluation report path."),
    ],
) -> None:
    """Summarize evaluation data for every .ivoproj project in a directory."""
    project_paths = [
        path
        for path in sorted(input_dir.iterdir())
        if path.is_dir() and path.suffix == ".ivoproj"
    ]
    report = build_batch_evaluation_report(project_paths)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    typer.echo(f"Batch evaluation written: {output}")


@app.command("validate-local-profiles")
def validate_local_profiles(
    profiles_path: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON validation report.")] = False,
) -> None:
    """Validate a local command profiles JSON before running real models."""
    profiles = LocalCommandPipelineProfiles.model_validate(
        json.loads(profiles_path.read_text(encoding="utf-8"))
    )
    report = validate_local_command_profiles(profiles)
    if json_output:
        typer.echo(report.model_dump_json(indent=2))
    else:
        status = "ok" if report.ok else "failed"
        typer.echo(f"Local profiles validation: {status}")
        for stage in report.stages:
            typer.echo(f"  stage: {stage}")
        for error in report.errors:
            typer.echo(f"  error: {error}")
    if not report.ok:
        raise typer.Exit(1)


@app.command("check-local-readiness")
def check_local_readiness(
    profiles_path: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    models_dir: Annotated[
        Path,
        typer.Option("--models-dir", file_okay=False, help="Local model cache root to inspect."),
    ] = Path("models"),
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Output JSON readiness report."),
    ] = False,
) -> None:
    """Check whether selected local profiles appear ready for real model execution."""
    profiles = LocalCommandPipelineProfiles.model_validate(
        json.loads(profiles_path.read_text(encoding="utf-8"))
    )
    report = build_local_readiness_report(
        profiles,
        dependencies=collect_optional_model_dependencies(models_dir),
    )
    if json_output:
        typer.echo(report.model_dump_json(indent=2))
    else:
        _echo_local_readiness(report)
    if not report.ok:
        raise typer.Exit(1)


def _echo_local_readiness(report: LocalReadinessReport) -> None:
    status = "ok" if report.ok else "failed"
    typer.echo(f"readiness: {status}")
    for profile in report.checked_profiles:
        typer.echo(f"checked: {profile}")
    for profile in report.skipped_dry_run_profiles:
        typer.echo(f"skipped dry-run: {profile}")
    for missing in report.missing:
        typer.echo(f"missing: {missing}")


@app.command("validate-http-profile")
def validate_http_profile_command(
    profile_path: Annotated[Path, typer.Argument(exists=True, dir_okay=False, readable=True)],
    json_output: Annotated[bool, typer.Option("--json", help="Output JSON validation report.")] = False,
) -> None:
    """Validate one HTTP adapter profile before using an online API."""
    profile = ApiAdapterProfile.model_validate(json.loads(profile_path.read_text(encoding="utf-8")))
    report = validate_http_profile(profile)
    if json_output:
        typer.echo(report.model_dump_json(indent=2))
    else:
        status = "ok" if report.ok else "failed"
        typer.echo(f"HTTP profile validation: {status}")
        typer.echo(f"  stage: {report.stage}")
        typer.echo(f"  provider: {report.provider}")
        for error in report.errors:
            typer.echo(f"  error: {error}")
    if not report.ok:
        raise typer.Exit(1)


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
    models_dir: Annotated[
        Path,
        typer.Option("--models-dir", file_okay=False, help="Local model cache root to inspect."),
    ] = Path("models"),
    require_readiness: Annotated[
        bool,
        typer.Option("--require-readiness", help="Fail before creating a project if models are not ready."),
    ] = False,
    resume_existing: Annotated[
        bool,
        typer.Option(
            "--resume-existing",
            help="Load an existing project with the same name and resume completed stages.",
        ),
    ] = False,
) -> None:
    """Create a project and run local command adapters from a profile JSON file."""
    profiles = LocalCommandPipelineProfiles.model_validate(
        json.loads(profiles_path.read_text(encoding="utf-8"))
    )
    if require_readiness:
        readiness = build_local_readiness_report(
            profiles,
            dependencies=collect_optional_model_dependencies(models_dir),
        )
        _echo_local_readiness(readiness)
        if not readiness.ok:
            raise typer.Exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)
    project_path = output_dir / f"{project_name}.ivoproj"
    if resume_existing and project_path.is_dir():
        project = DubbingProject.load(project_path)
    else:
        if project_path.exists():
            typer.echo(
                f"Project already exists: {project_path}. "
                "Use --resume-existing to continue it."
            )
            raise typer.Exit(1)
        project = DubbingProject.create(
            project_path,
            name=project_name,
            source_language=source_language,
            target_language=target_language,
            source_video=source_video,
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
            target_language=project.target_language,
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
        if dependency.required_env_var is not None:
            env_status = "set" if dependency.env_var_set else "missing"
            typer.echo(f"  env: {dependency.required_env_var} ({env_status})")
        typer.echo(f"  install: {dependency.install_hint}")
        typer.echo(f"  download: {dependency.download_hint}")
        typer.echo(f"  license: {dependency.license_hint}")
        typer.echo(f"  verify: {dependency.verify_hint}")


@model_app.command("write-setup-script")
def model_write_setup_script(
    output: Annotated[
        Path,
        typer.Option("--output", dir_okay=False, help="PowerShell script path to write."),
    ],
    models_dir: Annotated[
        Path,
        typer.Option("--models-dir", file_okay=False, help="Local model cache root to prepare."),
    ] = Path("models"),
    stage: Annotated[
        str | None,
        typer.Option("--stage", help="Only include setup entries for one stage."),
    ] = None,
) -> None:
    """Write a PowerShell script for recommended local model setup steps."""
    script = build_model_setup_script(models_dir, stage=stage)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(script, encoding="utf-8")
    typer.echo(f"Model setup script written: {output}")


def _parse_key_value_options(options: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for option in options:
        key, separator, value = option.partition("=")
        if not separator or not key or not value:
            raise typer.BadParameter(f"Expected KEY=VALUE, got: {option}")
        parsed[key] = value
    return parsed


def _iter_video_paths(input_dir: Path) -> list[Path]:
    return [
        path
        for path in sorted(input_dir.iterdir())
        if path.is_file() and path.suffix.lower() in {".mp4", ".mkv", ".mov", ".avi"}
    ]


def _write_batch_report(report_path: Path, videos: list[dict[str, object]]) -> None:
    failed = sum(1 for item in videos if item["status"] == "failed")
    skipped = sum(1 for item in videos if item["status"] == "skipped")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "processed": len(videos),
                "completed": len(videos) - failed - skipped,
                "skipped": skipped,
                "failed": failed,
                "videos": videos,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    app()
