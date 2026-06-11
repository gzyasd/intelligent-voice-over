"""Tests for Alibaba Cloud ASR provider adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from ivo.model_services.adapters.alibaba_asr import (
    AlibabaAsrProvider,
    _parse_fun_asr_transcript,
    _parse_qwen_asr_transcript,
)


class TestAlibabaAsrProvider:
    def test_provider_metadata(self) -> None:
        provider = AlibabaAsrProvider(api_key="test-key")
        assert provider.provider_id == "alibaba"
        assert provider.stage == "asr"
        assert provider.protocol == "alibaba_asr"

    def test_default_model_is_fun_asr(self) -> None:
        provider = AlibabaAsrProvider(api_key="test-key")
        assert provider._model_name == "fun-asr"

    def test_to_pipeline_adapter_returns_asr_adapter(self) -> None:
        provider = AlibabaAsrProvider(api_key="test-key")
        adapter = provider.to_pipeline_adapter()
        assert hasattr(adapter, "transcribe")
        assert callable(adapter.transcribe)

    @patch("ivo.model_services.adapters.alibaba_asr.httpx.get")
    def test_validate_credentials_success(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        provider = AlibabaAsrProvider(api_key="valid-key")
        result = provider.validate_credentials()
        assert result.ok is True

    @patch("ivo.model_services.adapters.alibaba_asr.httpx.get")
    def test_validate_credentials_auth_failed(self, mock_get: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response
        provider = AlibabaAsrProvider(api_key="bad-key")
        result = provider.validate_credentials()
        assert result.ok is False
        assert result.error_code == "AUTH_FAILED"


class TestParseFunAsrTranscript:
    def test_parse_sentences(self) -> None:
        data = {
            "transcripts": [
                {
                    "sentences": [
                        {"begin_time": 0, "end_time": 3000, "text": "Hello", "speaker_id": "0"},
                        {"begin_time": 3000, "end_time": 6000, "text": "World", "speaker_id": "1"},
                    ]
                }
            ]
        }
        segments = _parse_fun_asr_transcript(data, "en")
        assert len(segments) == 2
        assert segments[0].source_text == "Hello"
        assert segments[0].speaker_id == "0"
        assert segments[1].source_text == "World"

    def test_parse_empty_transcripts(self) -> None:
        data = {"transcripts": []}
        segments = _parse_fun_asr_transcript(data, "en")
        assert segments == []


class TestParseQwenAsrTranscript:
    def test_parse_sentences(self) -> None:
        data = {
            "transcripts": [
                {
                    "sentences": [
                        {"begin_time": 0, "end_time": 5000, "text": "Test text"},
                    ]
                }
            ]
        }
        segments = _parse_qwen_asr_transcript(data, "en")
        assert len(segments) == 1
        assert segments[0].source_text == "Test text"
        assert segments[0].speaker_id == "unknown"  # Qwen-ASR doesn't support diarization
