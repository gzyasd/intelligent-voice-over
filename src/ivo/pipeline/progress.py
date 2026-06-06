from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

PipelineStage = Literal[
    "import",
    "audio_extract",
    "separation",
    "asr",
    "diarization",
    "translation",
    "tts",
    "export",
]

PipelineProgressStatus = Literal["started", "progress", "completed", "failed", "skipped"]

STAGE_LABELS: dict[PipelineStage, str] = {
    "import": "导入视频",
    "audio_extract": "提取音频",
    "separation": "分离人声/背景",
    "asr": "识别字幕",
    "diarization": "识别角色",
    "translation": "翻译改写",
    "tts": "生成配音",
    "export": "合成视频",
}

STAGE_ORDER: tuple[PipelineStage, ...] = (
    "import",
    "audio_extract",
    "separation",
    "asr",
    "diarization",
    "translation",
    "tts",
    "export",
)

STAGE_PROGRESS_RANGES: dict[PipelineStage, tuple[int, int]] = {
    "import": (0, 5),
    "audio_extract": (5, 10),
    "separation": (10, 20),
    "asr": (20, 35),
    "diarization": (35, 42),
    "translation": (42, 55),
    "tts": (55, 90),
    "export": (90, 100),
}


class PipelineProgressEvent(BaseModel):
    stage: PipelineStage
    stage_label: str
    status: PipelineProgressStatus
    message: str = ""
    overall_percent: int = 0
    current_item: int | None = None
    total_items: int | None = None
    output_path: Path | None = None


def stage_percent(
    stage: PipelineStage,
    *,
    status: PipelineProgressStatus,
    current_item: int | None = None,
    total_items: int | None = None,
) -> int:
    start, end = STAGE_PROGRESS_RANGES[stage]
    if status == "completed":
        return end
    if status == "progress" and current_item is not None and total_items:
        fraction = max(0, min(current_item / total_items, 1))
        return min(end, start + int((end - start) * fraction))
    if status == "skipped":
        return end
    return start
