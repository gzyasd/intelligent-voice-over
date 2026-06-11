"""Combined ASR + diarization result caching and skip strategy.

This module provides utilities for managing combined ASR + diarization
adapters where a single API call produces both transcription and speaker
diarization results. The diarization stage can then skip its own API call
and reuse cached results.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

from ivo.core.timeline import SourceLanguage
from ivo.pipeline.transcribe import DiarizationSegment, TranscriptionSegment


class CombinedAsrResultCache:
    """Thread-safe cache for combined ASR + diarization results.

    When a combined adapter runs transcribe(), it stores the diarization
    segments. The diarization adapter can then retrieve them without
    making another API call.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._diarization_segments: list[DiarizationSegment] | None = None
        self._source_audio: Path | None = None

    def store(
        self,
        audio_path: Path,
        diarization_segments: list[DiarizationSegment],
    ) -> None:
        """Store diarization results from a combined ASR call."""
        with self._lock:
            self._diarization_segments = list(diarization_segments)
            self._source_audio = audio_path

    def retrieve(self, audio_path: Path) -> list[DiarizationSegment] | None:
        """Retrieve cached diarization if it matches the audio path."""
        with self._lock:
            if self._diarization_segments is not None and self._source_audio == audio_path:
                return list(self._diarization_segments)
            return None

    def clear(self) -> None:
        """Clear the cached results."""
        with self._lock:
            self._diarization_segments = None
            self._source_audio = None

    @property
    def has_cached(self) -> bool:
        with self._lock:
            return self._diarization_segments is not None


class CombinedAsrPipelineAdapter:
    """ASR adapter that caches diarization results for reuse.

    Wraps an underlying provider's ASR adapter and, after transcription,
    stores the diarization segments in a shared cache.
    """

    def __init__(
        self,
        inner_asr_adapter: Any,
        cache: CombinedAsrResultCache,
        diarization_provider: Any | None = None,
    ) -> None:
        self._inner = inner_asr_adapter
        self._cache = cache
        self._diarization_provider = diarization_provider

    def transcribe(
        self, audio_path: Path, *, source_language: SourceLanguage
    ) -> list[TranscriptionSegment]:
        # Clear previous cache before new transcription
        self._cache.clear()

        segments: list[TranscriptionSegment] = self._inner.transcribe(
            audio_path, source_language=source_language
        )

        # Extract diarization from the transcription results
        diar_segments = [
            DiarizationSegment(
                start_ms=seg.start_ms,
                end_ms=seg.end_ms,
                speaker_id=seg.speaker_id,
            )
            for seg in segments
        ]
        self._cache.store(audio_path, diar_segments)
        return segments


class CombinedDiarizationPipelineAdapter:
    """Diarization adapter that returns cached results from combined ASR call.

    If no cached results are available, raises an error indicating that
    the ASR stage must run first.
    """

    def __init__(self, cache: CombinedAsrResultCache) -> None:
        self._cache = cache

    def diarize(self, audio_path: Path) -> list[DiarizationSegment]:
        cached = self._cache.retrieve(audio_path)
        if cached is not None:
            return cached
        raise RuntimeError(
            "Diarization results not available. "
            "The ASR stage must run first with a combined ASR+diarization adapter. "
            "Ensure both ASR and diarization stages use the same provider config."
        )
