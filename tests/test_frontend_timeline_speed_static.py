from __future__ import annotations

from pathlib import Path


def test_timeline_regeneration_exposes_speech_rate_control() -> None:
    source = Path("src/pages/TimelineEditor.vue").read_text(encoding="utf-8")

    assert "NInputNumber" in source
    assert "speech_rate" in source
    assert "regenForm.value.speech_rate" in source
    assert "0.9" in source
    assert "语速" in source


def test_segments_api_sends_speech_rate_for_regeneration() -> None:
    source = Path("src/api/segments.ts").read_text(encoding="utf-8")

    assert "speech_rate?: number" in source
