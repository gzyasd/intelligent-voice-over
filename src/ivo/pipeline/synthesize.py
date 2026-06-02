from __future__ import annotations

import wave
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

from ivo.adapters.base import AdapterContext
from ivo.adapters.local import CommandRunner, LocalCommandAdapter, LocalCommandProfile
from ivo.core.project import DubbingProject
from ivo.core.timeline import DubbingSegment, TimelineStore


class SynthesisResult(BaseModel):
    segment_id: str
    audio_path: Path
    generated_duration_ms: int
    quality_flags: list[str]


class TtsAdapter(Protocol):
    def synthesize(
        self,
        *,
        text: str,
        speaker_id: str,
        output_path: Path,
        style_prompt: str | None,
        target_duration_ms: int,
    ) -> int: ...


class MockTtsAdapter:
    def __init__(self, generated_duration_ms: int | None = None) -> None:
        self.generated_duration_ms = generated_duration_ms

    def synthesize(
        self,
        *,
        text: str,
        speaker_id: str,
        output_path: Path,
        style_prompt: str | None,
        target_duration_ms: int,
    ) -> int:
        duration_ms = self.generated_duration_ms or target_duration_ms
        _write_silent_wav(output_path, duration_ms=duration_ms)
        return duration_ms


class LocalCommandTtsAdapter:
    def __init__(
        self,
        profile: LocalCommandProfile,
        *,
        runner: CommandRunner | None = None,
    ) -> None:
        self.profile = profile
        self.adapter = LocalCommandAdapter(profile, runner=runner)

    def synthesize(
        self,
        *,
        text: str,
        speaker_id: str,
        output_path: Path,
        style_prompt: str | None,
        target_duration_ms: int,
    ) -> int:
        result = self.adapter.run(
            AdapterContext(
                project_path=output_path.parent,
                segment_text=text,
                source_language="",
                target_language="zh",
                speaker_id=speaker_id,
                extra={
                    "output_audio_path": str(output_path),
                    "style_prompt": style_prompt or "",
                    "target_duration_ms": target_duration_ms,
                },
            )
        )
        if not result.ok:
            message = result.error.message if result.error is not None else "unknown TTS error"
            raise RuntimeError(f"{self.profile.id}: {message}")

        audio_path = Path(str(result.payload.get("audio_path", output_path)))
        if audio_path != output_path:
            output_path.write_bytes(audio_path.read_bytes())
        if not output_path.is_file():
            raise RuntimeError(f"{self.profile.id}: TTS output audio not found: {output_path}")
        duration = result.payload.get("duration_ms", target_duration_ms)
        return int(duration)


def select_reference_segments(
    timeline: TimelineStore,
    *,
    speaker_id: str,
    limit: int = 3,
) -> list[DubbingSegment]:
    references = [
        segment
        for segment in timeline.list_segments()
        if segment.speaker_id == speaker_id and segment.status == "approved"
    ]
    return references[:limit]


def synthesize_segment(
    project: DubbingProject,
    segment: DubbingSegment,
    adapter: TtsAdapter,
    *,
    tolerance_ms: int = 300,
) -> SynthesisResult:
    output_dir = project.path / "work" / "generated_segments"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{segment.id}.wav"
    target_duration_ms = segment.end_ms - segment.start_ms
    generated_duration_ms = adapter.synthesize(
        text=segment.target_text,
        speaker_id=segment.speaker_id,
        output_path=output_path,
        style_prompt=segment.style_prompt,
        target_duration_ms=target_duration_ms,
    )
    quality_flags = (
        ["duration_ok"]
        if abs(generated_duration_ms - target_duration_ms) <= tolerance_ms
        else ["duration_mismatch"]
    )
    project.timeline.update_segment(
        segment.id,
        quality_flags=quality_flags,
        status="rendered",
    )
    return SynthesisResult(
        segment_id=segment.id,
        audio_path=output_path,
        generated_duration_ms=generated_duration_ms,
        quality_flags=quality_flags,
    )


def _write_silent_wav(output_path: Path, *, duration_ms: int) -> None:
    sample_rate = 16_000
    sample_count = int(sample_rate * (duration_ms / 1000))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * sample_count)
