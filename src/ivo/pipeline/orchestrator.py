from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from ivo.core.project import DubbingProject
from ivo.pipeline.synthesize import (
    DEFAULT_CHINESE_TTS_SPEED,
    SynthesisResult,
    TtsAdapter,
    normalize_tts_speed,
    synthesize_segment,
)


class PipelineStageError(RuntimeError):
    def __init__(self, stage: str, message: str) -> None:
        super().__init__(f"{stage}: {message}")
        self.stage = stage


class ProgressEvent(BaseModel):
    stage: str
    current_segment: int | None = None
    total_segments: int | None = None
    message: str


@dataclass(frozen=True)
class PipelineStage:
    name: str
    run: Callable[[DubbingProject], None]


class PipelineOrchestrator:
    def __init__(
        self,
        project: DubbingProject,
        stages: list[PipelineStage],
        *,
        on_progress: Callable[[ProgressEvent], None] | None = None,
    ) -> None:
        self.project = project
        self.stages = stages
        self.on_progress = on_progress

    def run(self) -> None:
        for stage in self.stages:
            record = self.project.jobs.get(stage.name)
            if record is not None and record.status == "completed":
                self._emit(stage.name, "skipped completed stage")
                continue

            self.project.jobs.mark_running(stage.name, "running")
            self._emit(stage.name, "running")
            try:
                stage.run(self.project)
            except Exception as exc:
                message = str(exc)
                self.project.jobs.mark_failed(stage.name, message)
                self._emit(stage.name, message)
                raise PipelineStageError(stage.name, message) from exc

            self.project.jobs.mark_completed(stage.name, "completed")
            self._emit(stage.name, "completed")

    def _emit(self, stage: str, message: str) -> None:
        if self.on_progress is not None:
            self.on_progress(ProgressEvent(stage=stage, message=message))


def regenerate_segment(
    project: DubbingProject,
    segment_id: str,
    adapter: TtsAdapter,
    **changes: object,
) -> SynthesisResult:
    raw_speech_rate = changes.pop("speech_rate", None)
    speech_rate = _parse_speech_rate(raw_speech_rate)
    if changes:
        project.timeline.update_segment(segment_id, **changes)
    segment = project.timeline.get_segment(segment_id)
    return synthesize_segment(project, segment, adapter, speech_rate=speech_rate)


def _parse_speech_rate(value: object) -> float:
    if value is None:
        return DEFAULT_CHINESE_TTS_SPEED
    if isinstance(value, (int, float, str)):
        try:
            return normalize_tts_speed(float(value))
        except ValueError:
            return DEFAULT_CHINESE_TTS_SPEED
    return DEFAULT_CHINESE_TTS_SPEED
