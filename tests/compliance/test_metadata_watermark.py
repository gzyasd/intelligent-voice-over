from __future__ import annotations


def test_metadata_marks_ai_dubbing() -> None:
    from ivo.compliance.metadata import build_ai_dubbing_metadata

    metadata = build_ai_dubbing_metadata(source_language="en", target_language="zh")

    # Uses standard MP4 container tags (FFmpeg does not persist custom keys in MP4)
    assert "AI generated dubbing" in metadata["comment"]
    assert "source_language=en" in metadata["comment"]
    assert "target_language=zh" in metadata["comment"]
    assert metadata["genre"] == "AI Dubbed"
    assert metadata["artist"] == "Intelligent Voice Over"
    assert "en" in metadata["title"] and "zh" in metadata["title"]


def test_watermark_filter_is_optional_and_customizable() -> None:
    from ivo.compliance.watermark import WatermarkOptions, build_watermark_filter

    assert build_watermark_filter(WatermarkOptions(enabled=False, text="AI Dubbed")) is None

    watermark_filter = build_watermark_filter(WatermarkOptions(enabled=True, text="中文 AI 配音"))

    assert watermark_filter is not None
    assert "drawtext" in watermark_filter
    assert "中文 AI 配音" in watermark_filter
