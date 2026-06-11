"""Tests for combined ASR + diarization cache and skip strategy."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ivo.model_services.combined_asr import (
    CombinedAsrPipelineAdapter,
    CombinedAsrResultCache,
    CombinedDiarizationPipelineAdapter,
)
from ivo.pipeline.transcribe import DiarizationSegment, TranscriptionSegment


class TestCombinedAsrResultCache:
    def test_store_and_retrieve(self, tmp_path: Path) -> None:
        cache = CombinedAsrResultCache()
        audio = tmp_path / "test.wav"
        audio.touch()
        segments = [DiarizationSegment(start_ms=0, end_ms=1000, speaker_id="spk_0")]
        cache.store(audio, segments)
        result = cache.retrieve(audio)
        assert result is not None
        assert len(result) == 1
        assert result[0].speaker_id == "spk_0"

    def test_retrieve_wrong_path_returns_none(self, tmp_path: Path) -> None:
        cache = CombinedAsrResultCache()
        audio1 = tmp_path / "a.wav"
        audio2 = tmp_path / "b.wav"
        audio1.touch()
        audio2.touch()
        cache.store(audio1, [DiarizationSegment(start_ms=0, end_ms=1000, speaker_id="s")])
        assert cache.retrieve(audio2) is None

    def test_clear(self, tmp_path: Path) -> None:
        cache = CombinedAsrResultCache()
        audio = tmp_path / "test.wav"
        audio.touch()
        cache.store(audio, [DiarizationSegment(start_ms=0, end_ms=1000, speaker_id="s")])
        assert cache.has_cached is True
        cache.clear()
        assert cache.has_cached is False

    def test_has_cached_initially_false(self) -> None:
        cache = CombinedAsrResultCache()
        assert cache.has_cached is False


class TestCombinedAsrPipelineAdapter:
    def test_transcribe_caches_diarization(self, tmp_path: Path) -> None:
        audio = tmp_path / "audio.wav"
        audio.touch()
        mock_inner = MagicMock()
        mock_inner.transcribe.return_value = [
            TranscriptionSegment(
                id="0", start_ms=0, end_ms=1000, source_language="en",
                source_text="Hello", speaker_id="speaker_0",
            ),
            TranscriptionSegment(
                id="1", start_ms=1000, end_ms=2000, source_language="en",
                source_text="World", speaker_id="speaker_1",
            ),
        ]
        cache = CombinedAsrResultCache()
        adapter = CombinedAsrPipelineAdapter(mock_inner, cache)
        result = adapter.transcribe(audio, source_language="en")

        assert len(result) == 2
        assert cache.has_cached is True
        cached = cache.retrieve(audio)
        assert cached is not None
        assert len(cached) == 2
        assert cached[0].speaker_id == "speaker_0"
        assert cached[1].speaker_id == "speaker_1"

    def test_transcribe_clears_previous_cache(self, tmp_path: Path) -> None:
        audio = tmp_path / "audio.wav"
        audio.touch()
        cache = CombinedAsrResultCache()
        # Pre-populate cache
        cache.store(audio, [DiarizationSegment(start_ms=99, end_ms=199, speaker_id="old")])

        mock_inner = MagicMock()
        mock_inner.transcribe.return_value = [
            TranscriptionSegment(
                id="0", start_ms=0, end_ms=1000, source_language="en",
                source_text="New", speaker_id="new_speaker",
            ),
        ]
        adapter = CombinedAsrPipelineAdapter(mock_inner, cache)
        adapter.transcribe(audio, source_language="en")
        cached = cache.retrieve(audio)
        assert cached is not None
        assert cached[0].speaker_id == "new_speaker"


class TestCombinedDiarizationPipelineAdapter:
    def test_diarize_returns_cached(self, tmp_path: Path) -> None:
        audio = tmp_path / "audio.wav"
        audio.touch()
        cache = CombinedAsrResultCache()
        expected = [DiarizationSegment(start_ms=0, end_ms=1000, speaker_id="spk_0")]
        cache.store(audio, expected)

        adapter = CombinedDiarizationPipelineAdapter(cache)
        result = adapter.diarize(audio)
        assert result == expected

    def test_diarize_without_cache_raises(self, tmp_path: Path) -> None:
        audio = tmp_path / "audio.wav"
        audio.touch()
        cache = CombinedAsrResultCache()
        adapter = CombinedDiarizationPipelineAdapter(cache)
        with pytest.raises(RuntimeError, match="ASR stage must run first"):
            adapter.diarize(audio)
