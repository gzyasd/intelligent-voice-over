"""Tests for the adapter factory with all protocol handlers."""

from __future__ import annotations

from typing import Any
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


def _make_factory() -> ProviderAdapterFactory:
    registry = MagicMock()
    store = MagicMock()
    secret = MagicMock()
    store.get_account.return_value = MagicMock(api_base_url="https://api.test.com")
    secret.load.return_value = "test-api-key"
    return ProviderAdapterFactory(registry=registry, provider_store=store, secret_store=secret)


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
