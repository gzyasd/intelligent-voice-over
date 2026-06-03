from __future__ import annotations

import json
import subprocess
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
