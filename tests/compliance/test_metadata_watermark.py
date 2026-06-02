from __future__ import annotations


def test_metadata_marks_ai_dubbing() -> None:
    from ivo.compliance.metadata import build_ai_dubbing_metadata

    metadata = build_ai_dubbing_metadata(source_language="en", target_language="zh")

    assert metadata["ai_dubbing"] == "true"
    assert metadata["source_language"] == "en"
    assert metadata["target_language"] == "zh"


def test_watermark_filter_is_optional_and_customizable() -> None:
    from ivo.compliance.watermark import WatermarkOptions, build_watermark_filter

    assert build_watermark_filter(WatermarkOptions(enabled=False, text="AI Dubbed")) is None

    watermark_filter = build_watermark_filter(WatermarkOptions(enabled=True, text="中文 AI 配音"))

    assert watermark_filter is not None
    assert "drawtext" in watermark_filter
    assert "中文 AI 配音" in watermark_filter
