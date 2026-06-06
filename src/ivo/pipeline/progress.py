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


class PipelineProgressEvent(BaseModel):
    stage: PipelineStage
    stage_label: str
    status: PipelineProgressStatus
    message: str = ""
    overall_percent: int = 0
    current_item: int | None = None
    total_items: int | None = None
    output_path: Path | None = None


def stage_percent(stage: PipelineStage, *, status: PipelineProgressStatus) -> int:
    index = STAGE_ORDER.index(stage)
    if status == "completed":
        index += 1
    return round(index / len(STAGE_ORDER) * 100)
