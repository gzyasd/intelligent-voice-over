from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner


def test_validate_local_profiles_cli_accepts_complete_profile(tmp_path: Path) -> None:
    from ivo.cli import app

    profiles_path = tmp_path / "profiles.json"
    profiles_path.write_text(
        json.dumps(_profile_payload()),
        encoding="utf-8",
    )

    result = CliRunner().invoke(app, ["validate-local-profiles", str(profiles_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["errors"] == []
    assert payload["stages"] == ["separation", "asr", "tts"]


def test_validate_local_profiles_cli_reports_missing_output_placeholder(tmp_path: Path) -> None:
    from ivo.cli import app

    payload = _profile_payload()
    payload["tts"]["command"] = ["python", "tts.py", "--text", "{{ segment_text }}"]
    profiles_path = tmp_path / "profiles.json"
    profiles_path.write_text(json.dumps(payload), encoding="utf-8")

    result = CliRunner().invoke(app, ["validate-local-profiles", str(profiles_path), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert "tts command should include {{ output_json_path }}" in payload["errors"]


def test_validate_local_profiles_cli_reports_stage_mismatch(tmp_path: Path) -> None:
    from ivo.cli import app

    payload = _profile_payload()
    payload["tts"]["stage"] = "asr"
    profiles_path = tmp_path / "profiles.json"
    profiles_path.write_text(json.dumps(payload), encoding="utf-8")

    result = CliRunner().invoke(app, ["validate-local-profiles", str(profiles_path), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert "tts profile stage should be tts, got asr" in payload["errors"]


def test_validate_local_profiles_cli_reports_missing_required_stage_placeholders(
    tmp_path: Path,
) -> None:
    from ivo.cli import app

    payload = _profile_payload()
    payload["asr"]["command"] = ["python", "asr.py", "--out", "{{ output_json_path }}"]
    payload["tts"]["command"] = [
        "python",
        "tts.py",
        "--text",
        "{{ segment_text }}",
        "--out",
        "{{ output_json_path }}",
    ]
    profiles_path = tmp_path / "profiles.json"
    profiles_path.write_text(json.dumps(payload), encoding="utf-8")

    result = CliRunner().invoke(app, ["validate-local-profiles", str(profiles_path), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert "asr command should include {{ audio_path }}" in payload["errors"]
    assert "tts command should include {{ output_audio_path }}" in payload["errors"]


def test_all_example_local_profiles_pass_static_validation() -> None:
    from ivo.pipeline.local_command_preview import LocalCommandPipelineProfiles
    from ivo.profile_validation import validate_local_command_profiles

    for profiles_path in Path("examples").glob("local_command_profiles*.json"):
        profiles = LocalCommandPipelineProfiles.model_validate(
            json.loads(profiles_path.read_text(encoding="utf-8"))
        )
        report = validate_local_command_profiles(profiles)

        assert report.ok, f"{profiles_path}: {report.errors}"


def test_validate_http_profile_cli_accepts_complete_profile(tmp_path: Path) -> None:
    from ivo.cli import app

    profile_path = tmp_path / "translation.json"
    profile_path.write_text(json.dumps(_http_profile_payload()), encoding="utf-8")

    result = CliRunner().invoke(app, ["validate-http-profile", str(profile_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["stage"] == "translation"
    assert payload["errors"] == []


def test_validate_http_profile_cli_reports_bad_response_mapping(tmp_path: Path) -> None:
    from ivo.cli import app

    payload = _http_profile_payload()
    payload["response_mapping"] = {"target_text": "$["}
    profile_path = tmp_path / "translation.json"
    profile_path.write_text(json.dumps(payload), encoding="utf-8")

    result = CliRunner().invoke(app, ["validate-http-profile", str(profile_path), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert "response mapping target_text is not valid JSONPath" in payload["errors"]


def _profile_payload() -> dict[str, object]:
    return {
        "separation": {
            "id": "sep",
            "stage": "separation",
            "command": [
                "python",
                "sep.py",
                "--audio",
                "{{ audio_path }}",
                "--vocals-out",
                "{{ vocals_path }}",
                "--background-out",
                "{{ background_path }}",
                "--out",
                "{{ output_json_path }}",
            ],
            "output_json_path": "sep.json",
        },
        "asr": {
            "id": "asr",
            "stage": "asr",
            "command": [
                "python",
                "asr.py",
                "--audio",
                "{{ audio_path }}",
                "--language",
                "{{ source_language }}",
                "--out",
                "{{ output_json_path }}",
            ],
            "output_json_path": "asr.json",
        },
        "tts": {
            "id": "tts",
            "stage": "tts",
            "command": [
                "python",
                "tts.py",
                "--text",
                "{{ segment_text }}",
                "--speaker",
                "{{ speaker_id }}",
                "--audio-out",
                "{{ output_audio_path }}",
                "--out",
                "{{ output_json_path }}",
            ],
            "output_json_path": "tts.json",
        },
    }


def _http_profile_payload() -> dict[str, object]:
    return {
        "id": "translator",
        "stage": "translation",
        "method": "POST",
        "url": "https://api.example.test/translate",
        "headers": {"Authorization": "Bearer {{ api_key }}"},
        "request_template": {"text": "{{ segment_text }}"},
        "response_mapping": {"target_text": "$.text"},
    }
