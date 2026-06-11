"""Tests for OpenAI ASR provider adapter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from ivo.model_services.adapters.openai_audio import (
    OpenAIAudioProvider,
    _parse_diarized,
    _parse_segments,
)


# -- Response parsing tests --


class TestParseSegments:
    def test_verbose_json_with_segments(self) -> None:
        response = {
            "task": "transcribe",
            "language": "english",
            "duration": 6.0,
            "text": "Hello world",
            "segments": [
                {"id": 0, "start": 0.0, "end": 3.0, "text": "Hello"},
                {"id": 1, "start": 3.0, "end": 6.0, "text": "world"},
            ],
        }
        segments = _parse_segments(response, "en")
        assert len(segments) == 2
        assert segments[0].start_ms == 0
        assert segments[0].end_ms == 3000
        assert segments[0].source_text == "Hello"
        assert segments[1].start_ms == 3000
        assert segments[1].end_ms == 6000
        assert segments[1].source_text == "world"

    def test_json_without_segments_fallback(self) -> None:
        response = {
            "task": "transcribe",
            "language": "english",
            "duration": 5.0,
            "text": "full transcript text",
        }
        segments = _parse_segments(response, "en")
        assert len(segments) == 1
        assert segments[0].start_ms == 0
        assert segments[0].end_ms == 5000
        assert segments[0].source_text == "full transcript text"

    def test_json_without_segments_zero_duration(self) -> None:
        response = {"text": "hello", "duration": 0}
        segments = _parse_segments(response, "en")
        assert len(segments) == 1
        assert segments[0].end_ms == 1  # max(0, 1) fallback


class TestParseDiarized:
    def test_diarized_json_with_speakers(self) -> None:
        response = {
            "task": "transcribe",
            "duration": 6.0,
            "segments": [
                {"start": 0.0, "end": 3.0, "text": "Hello", "speaker": "speaker_0"},
                {"start": 3.5, "end": 6.0, "text": "Hi there", "speaker": "speaker_1"},
            ],
        }
        asr_segs, diar_segs = _parse_diarized(response, "en")
        assert len(asr_segs) == 2
        assert len(diar_segs) == 2
        assert asr_segs[0].speaker_id == "speaker_0"
        assert asr_segs[1].speaker_id == "speaker_1"
        assert diar_segs[0].speaker_id == "speaker_0"
        assert diar_segs[1].speaker_id == "speaker_1"
        assert asr_segs[0].source_text == "Hello"
        assert asr_segs[1].source_text == "Hi there"

    def test_diarized_empty_segments(self) -> None:
        response = {"segments": []}
        asr_segs, diar_segs = _parse_diarized(response, "en")
        assert asr_segs == []
        assert diar_segs == []


# -- Provider tests --


class TestOpenAIAudioProvider:
    def test_provider_metadata(self) -> None:
        provider = OpenAIAudioProvider(api_key="test-key")
        assert provider.provider_id == "openai"
        assert provider.stage == "asr"
        assert provider.protocol == "openai_asr"

    def test_diarize_model_detection(self) -> None:
        p1 = OpenAIAudioProvider(api_key="k", model_name="gpt-4o-transcribe")
        assert not p1._is_diarize_model()
        p2 = OpenAIAudioProvider(
            api_key="k", model_name="gpt-4o-transcribe-diarize", protocol="openai_diarize"
        )
        assert p2._is_diarize_model()

    def test_to_pipeline_adapter_returns_asr_adapter(self) -> None:
        provider = OpenAIAudioProvider(api_key="test-key")
        adapter = provider.to_pipeline_adapter()
        assert hasattr(adapter, "transcribe")
        assert callable(adapter.transcribe)

    @patch("ivo.model_services.adapters.openai_audio.httpx.post")
    def test_validate_credentials_success(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        provider = OpenAIAudioProvider(api_key="valid-key")
        result = provider.validate_credentials()
        assert result.ok is True
        assert result.provider_id == "openai"

    @patch("ivo.model_services.adapters.openai_audio.httpx.post")
    def test_validate_credentials_auth_failed(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_post.return_value = mock_response
        provider = OpenAIAudioProvider(api_key="bad-key")
        result = provider.validate_credentials()
        assert result.ok is False
        assert result.error_code == "AUTH_FAILED"
