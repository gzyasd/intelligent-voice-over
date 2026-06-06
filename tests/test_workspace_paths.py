from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner


def test_default_runtime_dirs_are_inside_workspace(tmp_path: Path) -> None:
    from ivo.workspace_paths import default_runs_dir, default_user_settings_path, default_work_dir

    assert default_runs_dir(root=tmp_path) == tmp_path / "runs"
    assert default_work_dir(root=tmp_path) == tmp_path / ".ivo-work"
    assert default_user_settings_path(root=tmp_path) == tmp_path / ".ivo-work" / "user-settings.json"


def test_model_smoke_defaults_use_workspace_work_dir(monkeypatch, tmp_path: Path) -> None:
    from ivo import model_smoke

    monkeypatch.chdir(tmp_path)

    assert model_smoke.default_asr_smoke_output_path() == (
        tmp_path / ".ivo-work" / "smoke" / "asr" / "asr-smoke.json"
    )
    assert model_smoke.default_adapter_smoke_output_path() == (
        tmp_path / ".ivo-work" / "smoke" / "adapters" / "adapter-smoke.json"
    )


def test_local_preview_uses_runs_dir_when_output_dir_is_omitted(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from ivo.cli import app
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult

    monkeypatch.chdir(tmp_path)
    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    profiles_path = tmp_path / "profiles.json"
    profiles_path.write_text(
        json.dumps(
            {
                "separation": {
                    "id": "sep",
                    "stage": "separation",
                    "command": ["sep"],
                    "output_json_path": "sep.json",
                },
                "asr": {
                    "id": "asr",
                    "stage": "asr",
                    "command": ["asr"],
                    "output_json_path": "asr.json",
                },
                "tts": {
                    "id": "tts",
                    "stage": "tts",
                    "command": ["tts"],
                    "output_json_path": "tts.json",
                },
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, Path] = {}

    def fake_run_local_command_preview(project, **kwargs):
        captured["project_path"] = project.path
        final_video = project.path / "renders" / "local-preview.mp4"
        final_video.parent.mkdir(parents=True, exist_ok=True)
        final_video.write_bytes(b"preview")
        return LocalCommandPreviewResult(
            final_video=final_video,
            metadata={"ai_dubbing": "true"},
            generated_segments=[],
        )

    monkeypatch.setattr("ivo.cli.run_local_command_preview", fake_run_local_command_preview)

    result = CliRunner().invoke(
        app,
        [
            "local-preview",
            str(source),
            "--profiles",
            str(profiles_path),
            "--project-name",
            "Episode 01",
            "--source-language",
            "en",
        ],
    )

    assert result.exit_code == 0
    assert captured["project_path"] == tmp_path / "runs" / "Episode 01.ivoproj"
