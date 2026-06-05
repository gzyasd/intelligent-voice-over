from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner


def test_package_exposes_version() -> None:
    import ivo

    assert isinstance(ivo.__version__, str)
    assert ivo.__version__


def test_doctor_reports_python_and_ffmpeg_status() -> None:
    from ivo.cli import app

    result = CliRunner().invoke(app, ["doctor"])

    assert result.exit_code == 0
    assert "Python" in result.output
    assert "FFmpeg" in result.output
    assert "NVIDIA" in result.output


def test_environment_diagnostics_reports_missing_tools(monkeypatch) -> None:
    from ivo.environment import collect_environment_diagnostics

    monkeypatch.setattr("shutil.which", lambda name: None)

    diagnostics = collect_environment_diagnostics()

    assert diagnostics.ffmpeg_path is None
    assert diagnostics.nvidia_smi_path is None
    assert "winget install" in diagnostics.ffmpeg_hint


def test_environment_diagnostics_uses_explicit_ffmpeg_path(monkeypatch, tmp_path) -> None:
    from ivo.environment import collect_environment_diagnostics

    ffmpeg = tmp_path / "ffmpeg.exe"
    ffmpeg.write_text("fake", encoding="utf-8")
    monkeypatch.setattr("shutil.which", lambda name: None)
    monkeypatch.setenv("IVO_FFMPEG_PATH", str(ffmpeg))

    diagnostics = collect_environment_diagnostics()

    assert diagnostics.ffmpeg_path == str(ffmpeg)


def test_mock_preview_command_creates_project_and_preview(tmp_path) -> None:
    from ivo.cli import app

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    output_dir = tmp_path / "out"

    result = CliRunner().invoke(
        app,
        [
            "mock-preview",
            str(source),
            str(output_dir),
            "--project-name",
            "Episode 01",
            "--source-language",
            "en",
        ],
    )

    assert result.exit_code == 0
    assert "preview.mp4" in result.output
    assert (output_dir / "Episode 01.ivoproj" / "renders" / "preview.mp4").is_file()


def test_batch_mock_preview_command_creates_projects_for_each_video(tmp_path) -> None:
    from ivo.cli import app

    input_dir = tmp_path / "episodes"
    input_dir.mkdir()
    (input_dir / "episode-01.mp4").write_bytes(b"video-1")
    (input_dir / "episode-02.mkv").write_bytes(b"video-2")
    (input_dir / "notes.txt").write_text("ignored", encoding="utf-8")
    output_dir = tmp_path / "out"

    result = CliRunner().invoke(
        app,
        [
            "batch-mock-preview",
            str(input_dir),
            str(output_dir),
            "--source-language",
            "en",
            "--no-watermark",
        ],
    )

    assert result.exit_code == 0
    assert "Processed 2 videos" in result.output
    assert (output_dir / "episode-01.ivoproj" / "renders" / "preview.mp4").is_file()
    assert (output_dir / "episode-02.ivoproj" / "renders" / "preview.mp4").is_file()


def test_batch_local_preview_command_processes_each_video(monkeypatch, tmp_path) -> None:
    from ivo.cli import app
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult

    input_dir = tmp_path / "episodes"
    input_dir.mkdir()
    (input_dir / "episode-01.mp4").write_bytes(b"video-1")
    (input_dir / "episode-02.mkv").write_bytes(b"video-2")
    (input_dir / "notes.txt").write_text("ignored", encoding="utf-8")
    output_dir = tmp_path / "out"
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
    processed: list[str] = []

    def fake_run_local_command_preview(project, **kwargs):
        processed.append(project.name)
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
            "batch-local-preview",
            str(input_dir),
            str(output_dir),
            "--profiles",
            str(profiles_path),
            "--source-language",
            "en",
            "--no-watermark",
        ],
    )

    assert result.exit_code == 0
    assert processed == ["episode-01", "episode-02"]
    assert "Processed 2 videos" in result.output
    assert (output_dir / "episode-01.ivoproj" / "renders" / "local-preview.mp4").is_file()
    assert (output_dir / "episode-02.ivoproj" / "renders" / "local-preview.mp4").is_file()


def test_batch_local_preview_command_continues_after_video_failure(monkeypatch, tmp_path) -> None:
    from ivo.cli import app
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult

    input_dir = tmp_path / "episodes"
    input_dir.mkdir()
    (input_dir / "episode-01.mp4").write_bytes(b"video-1")
    (input_dir / "episode-02.mp4").write_bytes(b"video-2")
    output_dir = tmp_path / "out"
    report_path = tmp_path / "batch-report.json"
    profiles_path = _write_smoke_local_profiles(tmp_path)
    processed: list[str] = []

    def fake_run_local_command_preview(project, **kwargs):
        processed.append(project.name)
        if project.name == "episode-01":
            project.jobs.mark_failed("asr", "asr provider failed")
            raise RuntimeError("asr provider failed")
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
            "batch-local-preview",
            str(input_dir),
            str(output_dir),
            "--profiles",
            str(profiles_path),
            "--source-language",
            "en",
            "--report",
            str(report_path),
        ],
    )

    assert result.exit_code == 1
    assert processed == ["episode-01", "episode-02"]
    assert "episode-01.mp4: FAILED: asr provider failed" in result.output
    assert "Failed 1 of 2 videos" in result.output
    assert (output_dir / "episode-02.ivoproj" / "renders" / "local-preview.mp4").is_file()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["processed"] == 2
    assert report["failed"] == 1
    assert report["completed"] == 1
    assert report["videos"][0]["source_video"].endswith("episode-01.mp4")
    assert "duration_seconds" in report["videos"][0]
    assert report["videos"][0]["status"] == "failed"
    assert report["videos"][0]["failed_stage"] == "asr"
    assert report["videos"][0]["error"] == "asr provider failed"
    assert report["videos"][1]["source_video"].endswith("episode-02.mp4")
    assert report["videos"][1]["status"] == "passed"
    assert report["videos"][1]["failed_stage"] is None
    assert report["videos"][1]["final_video"].endswith("local-preview.mp4")
    assert "duration_seconds" in report["videos"][1]


def test_batch_local_preview_command_skips_existing_outputs(monkeypatch, tmp_path) -> None:
    from ivo.cli import app
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult

    input_dir = tmp_path / "episodes"
    input_dir.mkdir()
    (input_dir / "episode-01.mp4").write_bytes(b"video-1")
    (input_dir / "episode-02.mp4").write_bytes(b"video-2")
    output_dir = tmp_path / "out"
    existing_preview = output_dir / "episode-01.ivoproj" / "renders" / "local-preview.mp4"
    existing_preview.parent.mkdir(parents=True)
    existing_preview.write_bytes(b"existing-preview")
    report_path = tmp_path / "batch-report.json"
    profiles_path = _write_smoke_local_profiles(tmp_path)
    processed: list[str] = []

    def fake_run_local_command_preview(project, **kwargs):
        processed.append(project.name)
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
            "batch-local-preview",
            str(input_dir),
            str(output_dir),
            "--profiles",
            str(profiles_path),
            "--skip-existing",
            "--report",
            str(report_path),
        ],
    )

    assert result.exit_code == 0
    assert processed == ["episode-02"]
    assert "episode-01.mp4: SKIPPED existing output" in result.output
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["skipped"] == 1
    assert report["videos"][0]["source_video"].endswith("episode-01.mp4")
    assert report["videos"][0]["status"] == "skipped"
    assert report["videos"][0]["failed_stage"] is None
    assert report["videos"][0]["final_video"].endswith("local-preview.mp4")
    assert "duration_seconds" in report["videos"][0]


def test_batch_local_preview_command_can_resume_existing_projects(monkeypatch, tmp_path) -> None:
    from ivo.cli import app
    from ivo.core.project import DubbingProject
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult

    input_dir = tmp_path / "episodes"
    input_dir.mkdir()
    (input_dir / "episode-01.mp4").write_bytes(b"video-1")
    output_dir = tmp_path / "out"
    project = DubbingProject.create(
        output_dir / "episode-01.ivoproj",
        name="episode-01",
        source_language="en",
        target_language="zh",
    )
    project.jobs.mark_completed("audio_extract", "completed")
    profiles_path = _write_smoke_local_profiles(tmp_path)
    captured: dict[str, object] = {}

    def fake_run_local_command_preview(project, **kwargs):
        captured["project_path"] = project.path
        captured["audio_extract_status"] = project.jobs.get("audio_extract").status
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
            "batch-local-preview",
            str(input_dir),
            str(output_dir),
            "--profiles",
            str(profiles_path),
            "--resume-existing",
        ],
    )

    assert result.exit_code == 0
    assert captured == {
        "project_path": output_dir / "episode-01.ivoproj",
        "audio_extract_status": "completed",
    }
    assert "Processed 1 videos" in result.output


def test_batch_local_preview_command_reports_existing_project_without_resume(
    monkeypatch, tmp_path
) -> None:
    from ivo.cli import app
    from ivo.core.project import DubbingProject
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult

    input_dir = tmp_path / "episodes"
    input_dir.mkdir()
    (input_dir / "episode-01.mp4").write_bytes(b"video-1")
    (input_dir / "episode-02.mp4").write_bytes(b"video-2")
    output_dir = tmp_path / "out"
    DubbingProject.create(
        output_dir / "episode-01.ivoproj",
        name="episode-01",
        source_language="en",
        target_language="zh",
    )
    profiles_path = _write_smoke_local_profiles(tmp_path)
    processed: list[str] = []

    def fake_run_local_command_preview(project, **kwargs):
        processed.append(project.name)
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
            "batch-local-preview",
            str(input_dir),
            str(output_dir),
            "--profiles",
            str(profiles_path),
        ],
    )

    assert result.exit_code == 1
    assert processed == ["episode-02"]
    assert "episode-01.mp4: FAILED:" in result.output
    assert "--resume-existing" in result.output
    assert "Failed 1 of 2 videos" in result.output


def test_batch_local_preview_command_can_require_readiness_before_creating_projects(
    tmp_path,
) -> None:
    from ivo.cli import app

    input_dir = tmp_path / "episodes"
    input_dir.mkdir()
    (input_dir / "episode-01.mp4").write_bytes(b"video-1")
    output_dir = tmp_path / "out"

    result = CliRunner().invoke(
        app,
        [
            "batch-local-preview",
            str(input_dir),
            str(output_dir),
            "--profiles",
            "examples/local_command_profiles.real_tts_cosyvoice.json",
            "--models-dir",
            str(tmp_path / "models"),
            "--require-readiness",
        ],
    )

    assert result.exit_code == 1
    assert "readiness: failed" in result.output
    assert "tts/CosyVoice" in result.output
    assert not (output_dir / "episode-01.ivoproj").exists()


def test_local_preview_command_loads_profiles_and_reports_output(monkeypatch, tmp_path) -> None:
    from ivo.cli import app
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    output_dir = tmp_path / "out"
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
    calls: list[str] = []

    def fake_run_local_command_preview(*args, **kwargs) -> LocalCommandPreviewResult:
        project = args[0]
        calls.append(kwargs["profiles"].tts.id)
        final_video = project.path / "renders" / "local-preview.mp4"
        final_video.write_bytes(b"preview")
        return LocalCommandPreviewResult(
            final_video=final_video,
            metadata={"ai_dubbing": "true"},
            generated_segments=[],
        )

    monkeypatch.setattr(
        "ivo.cli.run_local_command_preview",
        fake_run_local_command_preview,
        raising=False,
    )

    result = CliRunner().invoke(
        app,
        [
            "local-preview",
            str(source),
            str(output_dir),
            "--profiles",
            str(profiles_path),
            "--project-name",
            "Episode 01",
            "--source-language",
            "en",
            "--target-text",
            "seg-001=Hello",
            "--no-watermark",
        ],
    )

    assert result.exit_code == 0
    assert calls == ["tts"]
    assert "local-preview.mp4" in result.output


def test_local_preview_command_can_resume_existing_project(monkeypatch, tmp_path) -> None:
    from ivo.cli import app
    from ivo.core.project import DubbingProject
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    output_dir = tmp_path / "out"
    project = DubbingProject.create(
        output_dir / "Episode 01.ivoproj",
        name="Episode 01",
        source_language="en",
        target_language="zh",
    )
    project.jobs.mark_completed("import", "completed")
    profiles_path = _write_smoke_local_profiles(tmp_path)
    captured: dict[str, object] = {}

    def fake_run_local_command_preview(*args, **kwargs) -> LocalCommandPreviewResult:
        current_project = args[0]
        captured["project_path"] = current_project.path
        captured["import_status"] = current_project.jobs.get("import").status
        final_video = current_project.path / "renders" / "local-preview.mp4"
        final_video.write_bytes(b"preview")
        return LocalCommandPreviewResult(
            final_video=final_video,
            metadata={"ai_dubbing": "true"},
            generated_segments=[],
        )

    monkeypatch.setattr(
        "ivo.cli.run_local_command_preview",
        fake_run_local_command_preview,
        raising=False,
    )

    result = CliRunner().invoke(
        app,
        [
            "local-preview",
            str(source),
            str(output_dir),
            "--profiles",
            str(profiles_path),
            "--project-name",
            "Episode 01",
            "--resume-existing",
        ],
    )

    assert result.exit_code == 0
    assert captured == {
        "project_path": output_dir / "Episode 01.ivoproj",
        "import_status": "completed",
    }
    assert "local-preview.mp4" in result.output


def test_local_preview_command_reports_existing_project_without_resume(tmp_path) -> None:
    from ivo.cli import app
    from ivo.core.project import DubbingProject

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    output_dir = tmp_path / "out"
    DubbingProject.create(
        output_dir / "Episode 01.ivoproj",
        name="Episode 01",
        source_language="en",
        target_language="zh",
    )
    profiles_path = _write_smoke_local_profiles(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "local-preview",
            str(source),
            str(output_dir),
            "--profiles",
            str(profiles_path),
            "--project-name",
            "Episode 01",
        ],
    )

    assert result.exit_code == 1
    assert "already exists" in result.output
    assert "--resume-existing" in result.output


def test_local_preview_command_can_require_readiness_before_creating_project(tmp_path) -> None:
    from ivo.cli import app

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    output_dir = tmp_path / "out"

    result = CliRunner().invoke(
        app,
        [
            "local-preview",
            str(source),
            str(output_dir),
            "--profiles",
            "examples/local_command_profiles.real_tts_cosyvoice.json",
            "--project-name",
            "Episode 01",
            "--models-dir",
            str(tmp_path / "models"),
            "--require-readiness",
        ],
    )

    assert result.exit_code == 1
    assert "readiness: failed" in result.output
    assert "tts/CosyVoice" in result.output
    assert not (output_dir / "Episode 01.ivoproj").exists()


def test_local_preview_command_loads_translation_profile(monkeypatch, tmp_path) -> None:
    from ivo.cli import app
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    output_dir = tmp_path / "out"
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
    translation_profile = tmp_path / "translation.json"
    translation_profile.write_text(
        json.dumps(
            {
                "id": "online-translator",
                "stage": "translation",
                "method": "POST",
                "url": "https://api.example.test/translate",
                "headers": {},
                "request_template": {"prompt": "{{ prompt }}", "text": "{{ segment_text }}"},
                "response_mapping": {"target_text": "$.text", "emotion": "$.emotion"},
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    def fake_run_local_command_preview(*args, **kwargs) -> LocalCommandPreviewResult:
        project = args[0]
        captured["translation_adapter"] = kwargs["translation_adapter"]
        final_video = project.path / "renders" / "local-preview.mp4"
        final_video.write_bytes(b"preview")
        return LocalCommandPreviewResult(
            final_video=final_video,
            metadata={"ai_dubbing": "true"},
            generated_segments=[],
        )

    monkeypatch.setattr(
        "ivo.cli.run_local_command_preview",
        fake_run_local_command_preview,
        raising=False,
    )

    result = CliRunner().invoke(
        app,
        [
            "local-preview",
            str(source),
            str(output_dir),
            "--profiles",
            str(profiles_path),
            "--translation-profile",
            str(translation_profile),
            "--translation-var",
            "api_key=test-token",
            "--project-name",
            "Episode 01",
        ],
    )

    adapter = captured["translation_adapter"]
    assert result.exit_code == 0
    assert adapter.__class__.__name__ == "HttpTranslationAdapter"
    assert adapter.profile.id == "online-translator"
    assert adapter.extra == {"api_key": "test-token"}


def test_local_preview_command_loads_http_tts_profile(monkeypatch, tmp_path) -> None:
    from ivo.cli import app
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    output_dir = tmp_path / "out"
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
    tts_profile = tmp_path / "tts-http.json"
    tts_profile.write_text(
        json.dumps(
            {
                "id": "online-tts",
                "stage": "tts",
                "method": "POST",
                "url": "https://api.example.test/tts",
                "headers": {"Authorization": "Bearer {{ api_key }}"},
                "request_template": {"text": "{{ segment_text }}"},
                "response_mapping": {
                    "audio_base64": "$.audio_base64",
                    "duration_ms": "$.duration_ms",
                },
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    def fake_run_local_command_preview(*args, **kwargs) -> LocalCommandPreviewResult:
        project = args[0]
        captured["tts_adapter"] = kwargs["tts_adapter"]
        final_video = project.path / "renders" / "local-preview.mp4"
        final_video.write_bytes(b"preview")
        return LocalCommandPreviewResult(
            final_video=final_video,
            metadata={"ai_dubbing": "true"},
            generated_segments=[],
        )

    monkeypatch.setattr(
        "ivo.cli.run_local_command_preview",
        fake_run_local_command_preview,
        raising=False,
    )

    result = CliRunner().invoke(
        app,
        [
            "local-preview",
            str(source),
            str(output_dir),
            "--profiles",
            str(profiles_path),
            "--tts-profile",
            str(tts_profile),
            "--tts-var",
            "api_key=test-token",
            "--project-name",
            "Episode 01",
        ],
    )

    adapter = captured["tts_adapter"]
    assert result.exit_code == 0
    assert adapter.__class__.__name__ == "HttpTtsAdapter"
    assert adapter.profile.id == "online-tts"
    assert adapter.extra == {"api_key": "test-token"}


def test_local_preview_command_loads_http_asr_profile(monkeypatch, tmp_path) -> None:
    from ivo.cli import app
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    output_dir = tmp_path / "out"
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
    asr_profile = tmp_path / "asr-http.json"
    asr_profile.write_text(
        json.dumps(
            {
                "id": "online-asr",
                "stage": "asr",
                "method": "POST",
                "url": "https://api.example.test/asr",
                "headers": {"Authorization": "Bearer {{ api_key }}"},
                "request_template": {"audio_path": "{{ audio_path }}"},
                "response_mapping": {"segments": "$.segments"},
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    def fake_run_local_command_preview(*args, **kwargs) -> LocalCommandPreviewResult:
        project = args[0]
        captured["asr_adapter"] = kwargs["asr_adapter"]
        final_video = project.path / "renders" / "local-preview.mp4"
        final_video.write_bytes(b"preview")
        return LocalCommandPreviewResult(
            final_video=final_video,
            metadata={"ai_dubbing": "true"},
            generated_segments=[],
        )

    monkeypatch.setattr(
        "ivo.cli.run_local_command_preview",
        fake_run_local_command_preview,
        raising=False,
    )

    result = CliRunner().invoke(
        app,
        [
            "local-preview",
            str(source),
            str(output_dir),
            "--profiles",
            str(profiles_path),
            "--asr-profile",
            str(asr_profile),
            "--asr-var",
            "api_key=test-token",
            "--project-name",
            "Episode 01",
        ],
    )

    adapter = captured["asr_adapter"]
    assert result.exit_code == 0
    assert adapter.__class__.__name__ == "HttpAsrAdapter"
    assert adapter.profile.id == "online-asr"
    assert adapter.extra == {"api_key": "test-token"}


def test_local_preview_command_loads_http_separation_profile(monkeypatch, tmp_path) -> None:
    from ivo.cli import app
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    output_dir = tmp_path / "out"
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
    separation_profile = tmp_path / "separation-http.json"
    separation_profile.write_text(
        json.dumps(
            {
                "id": "online-separation",
                "stage": "separation",
                "method": "POST",
                "url": "https://api.example.test/separate",
                "headers": {"Authorization": "Bearer {{ api_key }}"},
                "request_template": {"audio_path": "{{ audio_path }}"},
                "response_mapping": {
                    "vocals_base64": "$.vocals_base64",
                    "background_base64": "$.background_base64",
                },
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    def fake_run_local_command_preview(*args, **kwargs) -> LocalCommandPreviewResult:
        project = args[0]
        captured["separation_adapter"] = kwargs["separation_adapter"]
        final_video = project.path / "renders" / "local-preview.mp4"
        final_video.write_bytes(b"preview")
        return LocalCommandPreviewResult(
            final_video=final_video,
            metadata={"ai_dubbing": "true"},
            generated_segments=[],
        )

    monkeypatch.setattr(
        "ivo.cli.run_local_command_preview",
        fake_run_local_command_preview,
        raising=False,
    )

    result = CliRunner().invoke(
        app,
        [
            "local-preview",
            str(source),
            str(output_dir),
            "--profiles",
            str(profiles_path),
            "--separation-profile",
            str(separation_profile),
            "--separation-var",
            "api_key=test-token",
            "--project-name",
            "Episode 01",
        ],
    )

    adapter = captured["separation_adapter"]
    assert result.exit_code == 0
    assert adapter.__class__.__name__ == "HttpSeparationAdapter"
    assert adapter.profile.id == "online-separation"
    assert adapter.extra == {"api_key": "test-token"}


def test_local_preview_command_loads_http_diarization_profile(monkeypatch, tmp_path) -> None:
    from ivo.cli import app
    from ivo.pipeline.local_command_preview import LocalCommandPreviewResult

    source = tmp_path / "episode.mp4"
    source.write_bytes(b"video")
    output_dir = tmp_path / "out"
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
    diarization_profile = tmp_path / "diarization-http.json"
    diarization_profile.write_text(
        json.dumps(
            {
                "id": "online-diarization",
                "stage": "diarization",
                "method": "POST",
                "url": "https://api.example.test/diarize",
                "headers": {"Authorization": "Bearer {{ api_key }}"},
                "request_template": {"audio_path": "{{ audio_path }}"},
                "response_mapping": {"segments": "$.segments"},
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    def fake_run_local_command_preview(*args, **kwargs) -> LocalCommandPreviewResult:
        project = args[0]
        captured["diarization_adapter"] = kwargs["diarization_adapter"]
        final_video = project.path / "renders" / "local-preview.mp4"
        final_video.write_bytes(b"preview")
        return LocalCommandPreviewResult(
            final_video=final_video,
            metadata={"ai_dubbing": "true"},
            generated_segments=[],
        )

    monkeypatch.setattr(
        "ivo.cli.run_local_command_preview",
        fake_run_local_command_preview,
        raising=False,
    )

    result = CliRunner().invoke(
        app,
        [
            "local-preview",
            str(source),
            str(output_dir),
            "--profiles",
            str(profiles_path),
            "--diarization-profile",
            str(diarization_profile),
            "--diarization-var",
            "api_key=test-token",
            "--project-name",
            "Episode 01",
        ],
    )

    adapter = captured["diarization_adapter"]
    assert result.exit_code == 0
    assert adapter.__class__.__name__ == "HttpDiarizationAdapter"
    assert adapter.profile.id == "online-diarization"
    assert adapter.extra == {"api_key": "test-token"}


def test_local_preview_command_runs_real_dry_run_profile(tmp_path) -> None:
    from ivo.cli import app
    from ivo.pipeline.import_video import FFmpegNotFoundError, require_ffmpeg

    try:
        ffmpeg = require_ffmpeg()
    except FFmpegNotFoundError:
        pytest.skip("FFmpeg is not visible in this shell; set IVO_FFMPEG_PATH or restart terminal.")

    source = tmp_path / "episode.mp4"
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=64x64:duration=1:rate=10",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=660:duration=1",
            "-shortest",
            str(source),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    output_dir = tmp_path / "out"
    profiles_path = Path("examples/local_command_profiles.real_dry_run.json")

    result = CliRunner().invoke(
        app,
        [
            "local-preview",
            str(source),
            str(output_dir),
            "--profiles",
            str(profiles_path),
            "--project-name",
            "Episode 01",
            "--source-language",
            "en",
            "--target-text",
            "seg-001=嗯，你好。",
            "--no-watermark",
        ],
    )

    preview = output_dir / "Episode 01.ivoproj" / "renders" / "local-preview.mp4"
    assert result.exit_code == 0
    assert preview.is_file()
    assert preview.stat().st_size > 0


def test_adapter_profile_cli_adds_and_lists_http_profile(tmp_path) -> None:
    from ivo.cli import app
    from ivo.adapters.profiles import AdapterProfileStore

    store_path = tmp_path / "adapters.json"
    add_result = CliRunner().invoke(
        app,
        [
            "adapter",
            "add-http",
            str(store_path),
            "--id",
            "translator",
            "--stage",
            "translation",
            "--url",
            "https://api.example.test/translate",
            "--response",
            "target_text=$.text",
            "--optional-response",
            "style_prompt",
            "--file-upload",
            "audio=audio_path",
        ],
    )
    list_result = CliRunner().invoke(app, ["adapter", "list", str(store_path)])

    assert add_result.exit_code == 0
    assert list_result.exit_code == 0
    assert "translator" in list_result.output
    assert "translation" in list_result.output
    profile = AdapterProfileStore(store_path).load()[0]
    assert profile.optional_response_keys == ["style_prompt"]
    assert profile.file_upload_fields == {"audio": "audio_path"}


def test_model_cli_registers_and_lists_local_model(tmp_path) -> None:
    from ivo.cli import app

    store_path = tmp_path / "models.json"
    model_path = tmp_path / "models" / "cosyvoice"
    model_path.mkdir(parents=True)

    add_result = CliRunner().invoke(
        app,
        [
            "model",
            "add-local",
            str(store_path),
            "--id",
            "cosyvoice-local",
            "--stage",
            "tts",
            "--name",
            "CosyVoice Local",
            "--path",
            str(model_path),
            "--language",
            "zh",
            "--confirm-license",
        ],
    )
    list_result = CliRunner().invoke(app, ["model", "list", str(store_path)])

    assert add_result.exit_code == 0
    assert list_result.exit_code == 0
    assert "cosyvoice-local" in list_result.output
    assert "license: yes" in list_result.output


def test_doctor_models_reports_optional_dependency_status() -> None:
    from ivo.cli import app

    result = CliRunner().invoke(app, ["doctor-models"])

    assert result.exit_code == 0
    assert "faster-whisper" in result.output
    assert "demucs" in result.output
    assert "f5_tts" in result.output
    assert "pyannote.audio" in result.output
    assert "CosyVoice" in result.output
    assert "Qwen" in result.output
    assert "download:" in result.output
    assert "license:" in result.output
    assert "model dir:" in result.output
    assert "uv run ivo model smoke-asr --dry-run" in result.output
    assert "uv run ivo model write-setup-script --models-dir .\\models" in result.output


def test_doctor_models_can_filter_by_stage() -> None:
    from ivo.cli import app

    result = CliRunner().invoke(app, ["doctor-models", "--stage", "tts"])

    assert result.exit_code == 0
    assert "tts / CosyVoice" in result.output
    assert "tts / f5_tts" in result.output
    assert "faster-whisper" not in result.output


def test_doctor_models_can_output_json(monkeypatch, tmp_path) -> None:
    from ivo.cli import app

    monkeypatch.delenv("HF_TOKEN", raising=False)
    models_dir = tmp_path / "models"
    (models_dir / "asr" / "faster-whisper-large-v3").mkdir(parents=True)

    result = CliRunner().invoke(app, ["doctor-models", "--models-dir", str(models_dir), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    faster_whisper = next(item for item in payload if item["name"] == "faster-whisper")
    assert faster_whisper["stage"] == "asr"
    assert faster_whisper["model_dir_exists"] is True
    assert "huggingface-cli download" in faster_whisper["download_hint"]
    pyannote = next(item for item in payload if item["name"] == "pyannote.audio")
    assert pyannote["required_env_var"] == "HF_TOKEN"
    assert pyannote["env_var_set"] is False


def test_optional_model_dependency_status_includes_model_directory(tmp_path) -> None:
    from ivo.environment import collect_optional_model_dependencies

    model_dir = tmp_path / "models" / "asr" / "faster-whisper-large-v3"
    model_dir.mkdir(parents=True)

    statuses = collect_optional_model_dependencies(tmp_path / "models")

    faster_whisper = next(status for status in statuses if status.name == "faster-whisper")
    assert faster_whisper.stage == "asr"
    assert faster_whisper.model_dir == model_dir
    assert faster_whisper.model_dir_exists is True
    assert "huggingface-cli download" in faster_whisper.download_hint


def test_model_setup_plan_lists_install_download_and_verify_commands(tmp_path) -> None:
    from ivo.cli import app

    result = CliRunner().invoke(
        app,
        [
            "model",
            "setup-plan",
            "--models-dir",
            str(tmp_path / "models"),
            "--stage",
            "tts",
        ],
    )

    assert result.exit_code == 0
    assert "tts / CosyVoice" in result.output
    assert "install:" in result.output
    assert "download:" in result.output
    assert "verify:" in result.output
    assert "faster-whisper" not in result.output


def test_model_write_setup_script_command_writes_filtered_script(tmp_path) -> None:
    from ivo.cli import app

    output = tmp_path / "setup-local-models.ps1"

    result = CliRunner().invoke(
        app,
        [
            "model",
            "write-setup-script",
            "--models-dir",
            str(tmp_path / "models"),
            "--stage",
            "asr",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    assert output.is_file()
    script = output.read_text(encoding="utf-8")
    assert "asr / faster-whisper" in script
    assert "CosyVoice" not in script
    assert "Model setup script written" in result.output


def test_model_smoke_asr_command_runs_adapter_dry_run(tmp_path) -> None:
    from ivo.cli import app

    output = tmp_path / "asr-smoke.json"

    result = CliRunner().invoke(
        app,
        [
            "model",
            "smoke-asr",
            "--output",
            str(output),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "ASR smoke probe completed" in result.output
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["segments"][0]["text"] == "Well, hi."


def test_model_smoke_asr_command_uses_temp_output_by_default() -> None:
    from ivo.cli import app

    result = CliRunner().invoke(
        app,
        [
            "model",
            "smoke-asr",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "ASR smoke probe completed:" in result.output
    completed_line = next(
        line for line in result.output.splitlines() if line.startswith("ASR smoke probe completed:")
    )
    assert str(Path(tempfile.gettempdir())) in completed_line


def test_model_smoke_adapters_command_validates_local_command_contracts(tmp_path) -> None:
    from ivo.cli import app

    output = tmp_path / "adapter-smoke.json"

    result = CliRunner().invoke(
        app,
        [
            "model",
            "smoke-adapters",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0
    assert "Local adapter smoke probe completed" in result.output
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert [item["stage"] for item in payload["probes"]] == [
        "separation",
        "asr",
        "tts",
        "tts",
    ]
    assert {item["provider"] for item in payload["probes"]} == {
        "demucs",
        "faster-whisper",
        "f5-tts",
        "cosyvoice",
    }


def test_pyproject_declares_local_asr_extra() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "[project.optional-dependencies]" in pyproject
    assert "local-asr" in pyproject
    assert "faster-whisper" in pyproject


def test_pyproject_declares_local_separation_extra() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "local-separation" in pyproject
    assert "demucs" in pyproject
    assert "torch==2.5.1" in pyproject
    assert "torchaudio==2.5.1" in pyproject
    assert "soundfile" in pyproject


def test_pyproject_declares_local_tts_f5_extra() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "local-tts-f5" in pyproject
    assert "f5-tts" in pyproject
    assert "transformers<5" in pyproject


def test_pyproject_declares_local_tts_cosyvoice_extra() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")

    assert "local-tts-cosyvoice" in pyproject
    assert "modelscope" in pyproject


def test_local_model_setup_doc_mentions_json_and_setup_plan_commands() -> None:
    document = Path("docs/local-model-setup.md").read_text(encoding="utf-8")

    assert "uv run ivo doctor-models --json" in document
    assert "uv run ivo model setup-plan" in document
    assert "uv run ivo model write-setup-script" in document
    assert "uv run ivo model smoke-asr" in document
    assert "uv run ivo model smoke-adapters" in document


def test_gitignore_excludes_real_media_models_and_secrets() -> None:
    text = Path(".gitignore").read_text(encoding="utf-8")

    for pattern in ("models/", "测试视频/", "*.mp4", "*.wav", ".env", "scratch/"):
        assert pattern in text


def test_compliance_document_covers_model_and_user_license_responsibilities() -> None:
    text = Path("docs/compliance-and-licenses.md").read_text(encoding="utf-8")

    for required in (
        "项目代码许可证：MIT",
        "第三方模型许可证彼此独立",
        "F5-TTS",
        "CC-BY-NC",
        "CosyVoice",
        "pyannote",
        "Hugging Face",
        "用户必须确认拥有视频处理权利",
        "AI 配音元数据",
        "可见水印",
    ):
        assert required in text


def test_readme_points_to_compliance_and_contribution_guidance() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    assert "docs/compliance-and-licenses.md" in text
    assert "如何提交 issue" in text
    assert "如何贡献 profile" in text
    assert "不接受模型权重、真实影视片段或 API key" in text


def _write_smoke_local_profiles(tmp_path: Path) -> Path:
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
    return profiles_path
