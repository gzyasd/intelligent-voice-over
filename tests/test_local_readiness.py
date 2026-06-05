from __future__ import annotations

from pathlib import Path


def test_build_local_readiness_report_skips_dry_run_profiles(tmp_path: Path) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.environment import OptionalDependencyStatus
    from ivo.local_readiness import build_local_readiness_report
    from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles

    report = build_local_readiness_report(
        LocalCommandPipelineProfiles(
            separation=LocalCommandProfile(
                id="demucs-dry-run",
                stage="separation",
                command=["python", "demucs_separate.py", "--dry-run"],
                output_json_path="sep.json",
            ),
            asr=LocalCommandProfile(
                id="faster-whisper-dry-run",
                stage="asr",
                command=["python", "faster_whisper_asr.py", "--dry-run"],
                output_json_path="asr.json",
            ),
            tts=LocalCommandProfile(
                id="f5-tts-dry-run",
                stage="tts",
                command=["python", "f5_tts_command.py", "--dry-run"],
                output_json_path="tts.json",
            ),
        ),
        dependencies=[
            OptionalDependencyStatus(
                name="faster-whisper",
                stage="asr",
                import_name="faster_whisper",
                installed=False,
                install_hint="uv pip install faster-whisper",
                download_hint="download",
                license_hint="license",
                model_dir=tmp_path / "models" / "asr",
                model_dir_exists=False,
                verify_hint="verify",
            )
        ],
    )

    assert report.ok is True
    assert report.skipped_dry_run_profiles == [
        "separation:demucs-dry-run",
        "asr:faster-whisper-dry-run",
        "tts:f5-tts-dry-run",
    ]
    assert report.missing == []


def test_build_local_readiness_report_reports_missing_dependency_and_model_dir(
    tmp_path: Path,
) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.environment import OptionalDependencyStatus
    from ivo.local_readiness import build_local_readiness_report
    from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles

    report = build_local_readiness_report(
        LocalCommandPipelineProfiles(
            separation=LocalCommandProfile(
                id="demucs-real",
                stage="separation",
                command=["python", "demucs_separate.py"],
                output_json_path="sep.json",
            ),
            asr=LocalCommandProfile(
                id="faster-whisper-real",
                stage="asr",
                command=["python", "faster_whisper_asr.py"],
                output_json_path="asr.json",
            ),
            tts=LocalCommandProfile(
                id="cosyvoice-real",
                stage="tts",
                command=["python", "cosyvoice_tts.py"],
                output_json_path="tts.json",
            ),
        ),
        dependencies=[
            OptionalDependencyStatus(
                name="demucs",
                stage="separation",
                import_name="demucs",
                installed=True,
                install_hint="uv pip install demucs",
                download_hint="download",
                license_hint="license",
                model_dir=tmp_path / "models" / "demucs",
                model_dir_exists=False,
                verify_hint="verify",
            ),
            OptionalDependencyStatus(
                name="faster-whisper",
                stage="asr",
                import_name="faster_whisper",
                installed=False,
                install_hint="uv pip install faster-whisper",
                download_hint="download",
                license_hint="license",
                model_dir=tmp_path / "models" / "asr",
                model_dir_exists=False,
                verify_hint="verify",
            ),
            OptionalDependencyStatus(
                name="CosyVoice",
                stage="tts",
                import_name="cosyvoice",
                installed=False,
                install_hint="install CosyVoice",
                download_hint="download",
                license_hint="license",
                model_dir=tmp_path / "models" / "tts",
                model_dir_exists=False,
                verify_hint="verify",
            ),
        ],
    )

    assert report.ok is False
    assert "asr/faster-whisper: package missing" in report.missing
    assert "tts/CosyVoice: package missing" in report.missing


def test_local_readiness_report_exposes_structured_ui_results(tmp_path: Path) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.environment import OptionalDependencyStatus
    from ivo.local_readiness import build_local_readiness_report
    from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles

    report = build_local_readiness_report(
        LocalCommandPipelineProfiles(
            separation=LocalCommandProfile(
                id="sep-dry-run",
                stage="separation",
                command=["python", "sep.py", "--dry-run"],
                output_json_path="sep.json",
            ),
            asr=LocalCommandProfile(
                id="asr-real",
                stage="asr",
                command=["python", "faster_whisper_asr.py"],
                output_json_path="asr.json",
            ),
            tts=LocalCommandProfile(
                id="cosyvoice-real",
                stage="tts",
                command=["python", "cosyvoice_tts.py"],
                output_json_path="tts.json",
            ),
        ),
        dependencies=[
            OptionalDependencyStatus(
                name="faster-whisper",
                stage="asr",
                import_name="faster_whisper",
                installed=True,
                install_hint="install",
                download_hint="download",
                license_hint="license",
                model_dir=tmp_path / "models" / "asr",
                model_dir_exists=True,
                verify_hint="verify",
            ),
            OptionalDependencyStatus(
                name="CosyVoice",
                stage="tts",
                import_name="cosyvoice",
                installed=False,
                install_hint="install",
                download_hint="download",
                license_hint="license",
                model_dir=tmp_path / "models" / "tts",
                model_dir_exists=False,
                verify_hint="verify",
            ),
        ],
    )

    results = report.ui_results

    assert any(result.stage == "asr" and result.status == "ok" for result in results)
    assert any(
        result.stage == "tts"
        and result.provider == "CosyVoice"
        and result.status == "missing"
        and "package missing" in result.message
        for result in results
    )


def test_build_local_readiness_report_allows_optional_model_directories(
    tmp_path: Path,
) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.environment import OptionalDependencyStatus
    from ivo.local_readiness import build_local_readiness_report
    from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles

    report = build_local_readiness_report(
        LocalCommandPipelineProfiles(
            separation=LocalCommandProfile(
                id="demucs-real",
                stage="separation",
                command=["{{ python_executable }}", "demucs_separate.py"],
                output_json_path="sep.json",
            ),
            asr=LocalCommandProfile(
                id="faster-whisper-small",
                stage="asr",
                command=["{{ python_executable }}", "faster_whisper_asr.py", "--model", "small"],
                output_json_path="asr.json",
            ),
            tts=LocalCommandProfile(
                id="f5-tts-dry-run",
                stage="tts",
                command=["{{ python_executable }}", "f5_tts_command.py", "--dry-run"],
                output_json_path="tts.json",
            ),
        ),
        dependencies=[
            OptionalDependencyStatus(
                name="demucs",
                stage="separation",
                import_name="demucs",
                installed=True,
                install_hint="uv sync --extra local-separation",
                download_hint="download on first use",
                license_hint="license",
                model_dir=tmp_path / "models" / "demucs",
                model_dir_exists=False,
                model_dir_required=False,
                verify_hint="verify",
            ),
            OptionalDependencyStatus(
                name="faster-whisper",
                stage="asr",
                import_name="faster_whisper",
                installed=True,
                install_hint="uv sync --extra local-asr",
                download_hint="download on first use",
                license_hint="license",
                model_dir=tmp_path / "models" / "asr",
                model_dir_exists=False,
                model_dir_required=False,
                verify_hint="verify",
            ),
        ],
    )

    assert report.ok is True
    assert report.missing == []


def test_build_local_readiness_report_reports_missing_engine_command_file(
    tmp_path: Path,
) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.local_readiness import build_local_readiness_report
    from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles

    missing_command_file = tmp_path / "missing-engine-command.json"
    report = build_local_readiness_report(
        LocalCommandPipelineProfiles(
            separation=LocalCommandProfile(
                id="sep-dry-run",
                stage="separation",
                command=["python", "demucs_separate.py", "--dry-run"],
                output_json_path="sep.json",
            ),
            asr=LocalCommandProfile(
                id="asr-dry-run",
                stage="asr",
                command=["python", "faster_whisper_asr.py", "--dry-run"],
                output_json_path="asr.json",
            ),
            tts=LocalCommandProfile(
                id="f5-real",
                stage="tts",
                command=[
                    "python",
                    "f5_tts_command.py",
                    "--engine-command-json-file",
                    str(missing_command_file),
                ],
                output_json_path="tts.json",
            ),
        ),
        dependencies=[],
    )

    assert report.ok is False
    assert f"tts/f5-real: engine command file missing: {missing_command_file}" in report.missing


def test_build_local_readiness_report_warns_when_cuda_profile_lacks_nvidia_tool(
    tmp_path: Path,
) -> None:
    from ivo.adapters.local import LocalCommandProfile
    from ivo.environment import OptionalDependencyStatus
    from ivo.local_readiness import build_local_readiness_report
    from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles

    report = build_local_readiness_report(
        LocalCommandPipelineProfiles(
            separation=LocalCommandProfile(
                id="demucs-gpu",
                stage="separation",
                command=["python", "demucs_separate.py", "--device", "cuda"],
                output_json_path="sep.json",
            ),
            asr=LocalCommandProfile(
                id="faster-whisper-gpu",
                stage="asr",
                command=["python", "faster_whisper_asr.py", "--device", "cuda"],
                output_json_path="asr.json",
            ),
            tts=LocalCommandProfile(
                id="f5-tts-dry-run",
                stage="tts",
                command=["python", "f5_tts_command.py", "--dry-run"],
                output_json_path="tts.json",
            ),
        ),
        dependencies=[
            OptionalDependencyStatus(
                name="demucs",
                stage="separation",
                import_name="demucs",
                installed=True,
                install_hint="install",
                download_hint="download",
                license_hint="license",
                model_dir=tmp_path / "models" / "separation" / "demucs",
                model_dir_exists=True,
                verify_hint="verify",
            ),
            OptionalDependencyStatus(
                name="faster-whisper",
                stage="asr",
                import_name="faster_whisper",
                installed=True,
                install_hint="install",
                download_hint="download",
                license_hint="license",
                model_dir=tmp_path / "models" / "asr",
                model_dir_exists=True,
                verify_hint="verify",
            ),
        ],
        nvidia_tool_available=False,
    )

    assert any("NVIDIA" in message and "CPU small" in message for message in report.missing)
    assert any(
        result.status == "missing"
        and "NVIDIA" in result.message
        and "CPU small" in result.message
        for result in report.ui_results
    )


def test_check_local_readiness_cli_accepts_dry_run_profiles(tmp_path: Path) -> None:
    import json

    from ivo.cli import app
    from typer.testing import CliRunner

    profiles_path = Path("examples/local_command_profiles.real_dry_run.json")

    result = CliRunner().invoke(
        app,
        [
            "check-local-readiness",
            str(profiles_path),
            "--models-dir",
            str(tmp_path / "models"),
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["missing"] == []
    assert payload["skipped_dry_run_profiles"]


def test_check_local_readiness_cli_reports_real_profile_gaps(tmp_path: Path) -> None:
    import json

    from ivo.cli import app
    from typer.testing import CliRunner

    profiles_path = Path("examples/local_command_profiles.real_tts_cosyvoice.json")

    result = CliRunner().invoke(
        app,
        [
            "check-local-readiness",
            str(profiles_path),
            "--models-dir",
            str(tmp_path / "models"),
            "--json",
        ],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert any(item.startswith("tts/CosyVoice:") for item in payload["missing"])
