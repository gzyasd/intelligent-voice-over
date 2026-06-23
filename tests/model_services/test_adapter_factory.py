"""Tests for the adapter factory with all protocol handlers."""

from __future__ import annotations

from typing import Any
import sys
from unittest.mock import MagicMock

import pytest

from ivo.pipeline.transcribe import DiarizationSegment
from ivo.model_services.adapter_factory import ProviderAdapterFactory
from ivo.model_services.provider_config import StageProviderConfig


def _make_config(
    stage: str = "asr",
    protocol: str = "openai_asr",
    kind: str = "api",
    **kwargs: Any,
) -> StageProviderConfig:
    return StageProviderConfig(
        id=f"test-{stage}-{protocol}",
        display_name=f"Test {stage}",
        account_id="acct-test" if kind == "api" else None,
        provider_key=kwargs.pop("provider_key", "test"),
        kind=kind,  # type: ignore[arg-type]
        stage=stage,  # type: ignore[arg-type]
        protocol=protocol,
        **kwargs,
    )


def _make_factory(**kwargs: Any) -> ProviderAdapterFactory:
    registry = MagicMock()
    store = MagicMock()
    secret = MagicMock()
    store.get_account.return_value = MagicMock(api_base_url="https://api.test.com")
    secret.load.return_value = "test-api-key"
    return ProviderAdapterFactory(
        registry=registry,
        provider_store=store,
        secret_store=secret,
        **kwargs,
    )


class TestAdapterFactoryProtocols:
    def test_openai_asr_creates_adapter(self) -> None:
        factory = _make_factory()
        config = _make_config(stage="asr", protocol="openai_asr")
        adapter = factory.create(config)
        assert hasattr(adapter, "transcribe")

    def test_openai_diarize_creates_adapter(self) -> None:
        factory = _make_factory()
        config = _make_config(stage="asr", protocol="openai_diarize")
        adapter = factory.create(config)
        assert hasattr(adapter, "transcribe")

    def test_deepgram_asr_creates_adapter(self) -> None:
        factory = _make_factory()
        config = _make_config(stage="asr", protocol="deepgram_asr", provider_key="deepgram")
        adapter = factory.create(config)
        assert hasattr(adapter, "transcribe")

    def test_deepgram_diarize_creates_adapter(self) -> None:
        factory = _make_factory()
        config = _make_config(stage="asr", protocol="deepgram_diarize", provider_key="deepgram")
        adapter = factory.create(config)
        assert hasattr(adapter, "transcribe")

    def test_audioshake_separation_creates_adapter(self) -> None:
        factory = _make_factory()
        config = _make_config(
            stage="separation", protocol="audioshake_separation", provider_key="audioshake"
        )
        adapter = factory.create(config)
        assert hasattr(adapter, "separate")

    def test_lalalai_separation_creates_adapter(self) -> None:
        factory = _make_factory()
        config = _make_config(
            stage="separation", protocol="lalalai_separation", provider_key="lalalai"
        )
        adapter = factory.create(config)
        assert hasattr(adapter, "separate")

    def test_openai_tts_creates_adapter(self) -> None:
        factory = _make_factory()
        config = _make_config(stage="tts", protocol="openai_tts", provider_key="openai")
        adapter = factory.create(config)
        assert hasattr(adapter, "synthesize")

    def test_elevenlabs_tts_creates_adapter(self) -> None:
        factory = _make_factory()
        config = _make_config(
            stage="tts", protocol="elevenlabs_tts", provider_key="elevenlabs"
        )
        adapter = factory.create(config)
        assert hasattr(adapter, "synthesize")

    def test_alibaba_qwen_tts_creates_adapter(self) -> None:
        factory = _make_factory()
        config = _make_config(
            stage="tts", protocol="alibaba_qwen_tts", provider_key="alibaba"
        )
        adapter = factory.create(config)
        assert hasattr(adapter, "synthesize")

    def test_openai_compatible_translation_uses_request_url_from_extra(self) -> None:
        factory = _make_factory()
        config = _make_config(
            stage="translation",
            protocol="openai_compatible_translation",
            provider_key="openai_compatible_translation",
            model_name="qwen-local",
            extra={
                "request_url": "http://127.0.0.1:1995/v1/chat/completions",
                "temperature": "0.2",
                "max_tokens": "1200",
            },
        )

        adapter = factory.create(config)

        assert adapter.profile.url == "http://127.0.0.1:1995/v1/chat/completions"
        assert adapter.profile.request_template["model"] == "qwen-local"
        assert adapter.profile.request_template["temperature"] == 0.2
        assert adapter.profile.request_template["max_tokens"] == 1200

    def test_openai_compatible_translation_accepts_base_url_with_v1(self) -> None:
        factory = _make_factory()
        factory._provider_store.get_account.return_value = MagicMock(
            api_base_url="http://127.0.0.1:1995/v1"
        )
        config = _make_config(
            stage="translation",
            protocol="openai_compatible_translation",
            provider_key="openai_compatible_translation",
            model_name="qwen-local",
        )

        adapter = factory.create(config)

        assert adapter.profile.url == "http://127.0.0.1:1995/v1/chat/completions"

    def test_openai_compatible_translation_accepts_full_chat_completions_url(
        self,
    ) -> None:
        factory = _make_factory()
        factory._provider_store.get_account.return_value = MagicMock(
            api_base_url="http://127.0.0.1:1995/v1/chat/completions"
        )
        config = _make_config(
            stage="translation",
            protocol="openai_compatible_translation",
            provider_key="openai_compatible_translation",
            model_name="qwen-local",
        )

        adapter = factory.create(config)

        assert adapter.profile.url == "http://127.0.0.1:1995/v1/chat/completions"

    def test_anthropic_compatible_translation_uses_request_url_and_version(self) -> None:
        factory = _make_factory()
        config = _make_config(
            stage="translation",
            protocol="anthropic_compatible_translation",
            provider_key="anthropic_compatible_translation",
            model_name="claude-local",
            extra={
                "request_url": "http://127.0.0.1:8000/v1/messages",
                "anthropic_version": "2023-06-01",
                "max_tokens": "1200",
                "temperature": "0.2",
            },
        )

        adapter = factory.create(config)

        assert adapter.profile.url == "http://127.0.0.1:8000/v1/messages"
        assert adapter.profile.headers["anthropic-version"] == "2023-06-01"
        assert adapter.profile.request_template["model"] == "claude-local"
        assert adapter.profile.request_template["max_tokens"] == 1200
        assert adapter.profile.request_template["temperature"] == 0.2

    def test_unknown_protocol_raises(self) -> None:
        factory = _make_factory()
        config = _make_config(stage="asr", protocol="unknown_protocol")
        with pytest.raises(NotImplementedError, match="No adapter implementation"):
            factory.create(config)


class TestAdapterFactoryLocal:
    def test_builtin_local_templates_use_configured_python_paths(
        self,
        tmp_path,
        monkeypatch,
    ) -> None:
        app_root = tmp_path / "resources"
        (app_root / "examples" / "local_commands").mkdir(parents=True)
        main_python = tmp_path / "custom-main" / "python.exe"
        pyannote_python = tmp_path / "custom-pyannote" / "python.exe"
        main_python.parent.mkdir(parents=True)
        pyannote_python.parent.mkdir(parents=True)
        main_python.write_bytes(b"python")
        pyannote_python.write_bytes(b"python")
        monkeypatch.chdir(app_root)

        factory = _make_factory(
            local_python=main_python,
            pyannote_python=pyannote_python,
        )
        separation = factory.create(
            _make_config(
                stage="separation",
                protocol="local_demucs",
                kind="local",
                provider_key="demucs",
                local_model_path="models/separation/demucs",
            )
        )
        diarization = factory.create(
            _make_config(
                stage="diarization",
                protocol="local_pyannote",
                kind="local",
                provider_key="pyannote-community-1",
                local_model_path="models/diarization/pyannote-community-1",
            )
        )

        assert separation.profile.extra["python_executable"] == str(main_python)
        assert diarization.profile.extra["pyannote_python_executable"] == str(
            pyannote_python
        )

    def test_local_separation_creates_adapter(self) -> None:
        factory = _make_factory()
        config = _make_config(
            stage="separation",
            protocol="local_demucs",
            kind="local",
            provider_key="demucs",
            extra={"command": ["python", "-m", "demucs"], "output_json_path": ""},
        )
        adapter = factory.create(config)
        assert hasattr(adapter, "separate")

    def test_local_asr_creates_adapter(self) -> None:
        factory = _make_factory()
        config = _make_config(
            stage="asr",
            protocol="local_faster_whisper",
            kind="local",
            provider_key="faster-whisper-large-v3",
            extra={"command": ["python", "asr.py"], "output_json_path": ""},
        )
        adapter = factory.create(config)
        assert hasattr(adapter, "transcribe")

    def test_local_pyannote_uses_default_hf_token_env_when_unset(
        self, tmp_path
    ) -> None:
        factory = _make_factory()
        config = _make_config(
            stage="diarization",
            protocol="local_pyannote",
            kind="local",
            provider_key="pyannote-community-1",
            local_model_path="models/diarization/pyannote-community-1",
        )
        adapter = factory.create(config)
        audio = tmp_path / "audio.wav"
        audio.write_bytes(b"fake")
        captured_command: list[str] = []

        def runner(command: list[str], *, cwd: str | None = None) -> None:
            captured_command[:] = command
            output_path = tmp_path / "pyannote-output.json"
            output_path.write_text(
                '{"segments":[{"start_ms":0,"end_ms":1000,"speaker_id":"speaker-1"}]}',
                encoding="utf-8",
            )

        adapter.adapter.runner = runner

        segments = adapter.diarize(audio)

        assert segments == [
            DiarizationSegment(start_ms=0, end_ms=1000, speaker_id="speaker-1")
        ]
        assert "--hf-token-env" in captured_command
        assert "HF_TOKEN" in captured_command

    def test_builtin_local_template_sets_runtime_context(self, tmp_path, monkeypatch) -> None:
        app_root = tmp_path / "app"
        examples_dir = app_root / "examples" / "local_commands"
        examples_dir.mkdir(parents=True)
        local_python = app_root / ".venv" / "Scripts" / "python.exe"
        local_python.parent.mkdir(parents=True)
        local_python.write_text("", encoding="utf-8")
        monkeypatch.chdir(app_root)

        factory = _make_factory()
        config = _make_config(
            stage="separation",
            protocol="local_demucs",
            kind="local",
            provider_key="demucs",
            local_model_path=str(app_root / "models" / "separation" / "demucs"),
        )

        adapter = factory.create(config)

        profile = adapter.profile
        assert profile.extra["working_dir"] == str(app_root)
        assert profile.extra["python_executable"] in {str(local_python), sys.executable}
        assert profile.extra["model_path"] == str(app_root / "models" / "separation" / "demucs")
