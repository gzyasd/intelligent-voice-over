"""Tests for Deepgram ASR provider adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from ivo.model_services.adapters.deepgram import (
    DeepgramProvider,
    _parse_deepgram_response,
)


class TestParseDeepgramResponse:
    def test_basic_word_grouping(self) -> None:
        response = {
            "results": {
                "channels": [
                    {
                        "alternatives": [
                            {
                                "words": [
                                    {"word": "hello", "start": 0.0, "end": 0.5, "confidence": 0.99, "speaker": 0},
                                    {"word": "world", "start": 0.6, "end": 1.0, "confidence": 0.98, "speaker": 0},
                                ]
                            }
                        ]
                    }
                ]
            }
        }
        asr_segs, diar_segs = _parse_deepgram_response(response, "en")
        assert len(asr_segs) == 1
        assert asr_segs[0].source_text == "hello world"
        assert asr_segs[0].speaker_id == "speaker_0"
        assert asr_segs[0].start_ms == 0
        assert asr_segs[0].end_ms == 1000

    def test_speaker_change_creates_new_segment(self) -> None:
        response = {
            "results": {
                "channels": [
                    {
                        "alternatives": [
                            {
                                "words": [
                                    {"word": "hi", "start": 0.0, "end": 0.3, "confidence": 0.99, "speaker": 0},
                                    {"word": "hello", "start": 1.0, "end": 1.5, "confidence": 0.99, "speaker": 1},
                                ]
                            }
                        ]
                    }
                ]
            }
        }
        asr_segs, diar_segs = _parse_deepgram_response(response, "en")
        assert len(asr_segs) == 2
        assert asr_segs[0].speaker_id == "speaker_0"
        assert asr_segs[1].speaker_id == "speaker_1"

    def test_gap_creates_new_segment(self) -> None:
        response = {
            "results": {
                "channels": [
                    {
                        "alternatives": [
                            {
                                "words": [
                                    {"word": "word1", "start": 0.0, "end": 0.3, "confidence": 0.99, "speaker": 0},
                                    {"word": "word2", "start": 2.0, "end": 2.5, "confidence": 0.99, "speaker": 0},
                                ]
                            }
                        ]
                    }
                ]
            }
        }
        asr_segs, _ = _parse_deepgram_response(response, "en")
        assert len(asr_segs) == 2

    def test_empty_response(self) -> None:
        response = {"results": {"channels": []}}
        asr_segs, diar_segs = _parse_deepgram_response(response, "en")
        assert asr_segs == []
        assert diar_segs == []


class TestDeepgramProvider:
    def test_provider_metadata(self) -> None:
        provider = DeepgramProvider(api_key="test-key")
        assert provider.provider_id == "deepgram"
        assert provider.stage == "asr"
        assert provider.protocol == "deepgram_asr"

    def test_diarize_mode(self) -> None:
        provider = DeepgramProvider(api_key="k", protocol="deepgram_diarize", diarize=True)
        assert provider._diarize is True
        assert provider.protocol == "deepgram_diarize"

    def test_to_pipeline_adapter_returns_asr_adapter(self) -> None:
        provider = DeepgramProvider(api_key="test-key")
        adapter = provider.to_pipeline_adapter()
        assert hasattr(adapter, "transcribe")
        assert callable(adapter.transcribe)

    @patch("ivo.model_services.adapters.deepgram.httpx.post")
    def test_validate_credentials_success(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        provider = DeepgramProvider(api_key="valid-key")
        result = provider.validate_credentials()
        assert result.ok is True
        assert result.provider_id == "deepgram"

    @patch("ivo.model_services.adapters.deepgram.httpx.post")
    def test_validate_credentials_auth_failed(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        provider = DeepgramProvider(api_key="bad-key")
        result = provider.validate_credentials()
        assert result.ok is False
        assert result.error_code == "AUTH_FAILED"
