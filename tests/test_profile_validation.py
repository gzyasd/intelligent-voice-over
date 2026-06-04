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


def _profile_payload() -> dict[str, object]:
    return {
        "separation": {
            "id": "sep",
            "stage": "separation",
            "command": ["python", "sep.py", "--out", "{{ output_json_path }}"],
            "output_json_path": "sep.json",
        },
        "asr": {
            "id": "asr",
            "stage": "asr",
            "command": ["python", "asr.py", "--out", "{{ output_json_path }}"],
            "output_json_path": "asr.json",
        },
        "tts": {
            "id": "tts",
            "stage": "tts",
            "command": ["python", "tts.py", "--out", "{{ output_json_path }}"],
            "output_json_path": "tts.json",
        },
    }
