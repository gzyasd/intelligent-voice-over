"""Stage definitions for the model services pipeline."""

from __future__ import annotations

from typing import Literal

StageName = Literal["separation", "asr", "diarization", "translation", "tts"]

STAGE_NAMES: tuple[StageName, ...] = (
    "separation",
    "asr",
    "diarization",
    "translation",
    "tts",
)

STAGE_LABELS: dict[StageName, str] = {
    "separation": "人声分离",
    "asr": "语音识别",
    "diarization": "说话人识别",
    "translation": "翻译",
    "tts": "语音合成",
}

# Stages that depend on each other and may be combined
COMBINABLE_STAGES: dict[StageName, list[StageName]] = {
    "asr": ["diarization"],
    "diarization": ["asr"],
}
