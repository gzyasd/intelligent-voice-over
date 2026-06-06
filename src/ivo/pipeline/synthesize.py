from __future__ import annotations

import audioop
import base64
import wave
from pathlib import Path
from typing import Protocol

import httpx
from pydantic import BaseModel

from ivo.adapters.base import AdapterContext
from ivo.adapters.http import ApiAdapterProfile, HttpStageAdapter
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
        reference_audio_path: Path | None,
        reference_text: str,
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
        reference_audio_path: Path | None,
        reference_text: str,
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
        reference_audio_path: Path | None,
        reference_text: str,
        target_duration_ms: int,
    ) -> int:
        result = self.adapter.run(
            AdapterContext(
                project_path=output_path.parent,
                segment_text=text,
                source_language="",
                target_language="zh",
                speaker_id=speaker_id,
                reference_audio_path=reference_audio_path,
                reference_text=reference_text,
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


class TtsProviderError(RuntimeError):
    """Raised when a TTS provider cannot produce normalized audio."""


class HttpTtsAdapter:
    def __init__(
        self,
        profile: ApiAdapterProfile,
        *,
        project_path: Path,
        client: httpx.Client | None = None,
        extra: dict[str, object] | None = None,
    ) -> None:
        self.profile = profile
        self.project_path = project_path
        self.extra = extra or {}
        self.adapter = HttpStageAdapter(profile, client=client)

    def synthesize(
        self,
        *,
        text: str,
        speaker_id: str,
        output_path: Path,
        style_prompt: str | None,
        reference_audio_path: Path | None,
        reference_text: str,
        target_duration_ms: int,
    ) -> int:
        result = self.adapter.run(
            AdapterContext(
                project_path=self.project_path,
                segment_text=text,
                source_language="",
                target_language="zh",
                speaker_id=speaker_id,
                reference_audio_path=reference_audio_path,
                reference_text=reference_text,
                extra={
                    "output_audio_path": str(output_path),
                    "style_prompt": style_prompt or "",
                    "target_duration_ms": target_duration_ms,
                    **self.extra,
                },
            )
        )
        if not result.ok:
            message = result.error.message if result.error is not None else "unknown TTS error"
            raise TtsProviderError(f"{self.profile.id}: {message}")

        self._write_audio_payload(result.payload, output_path)
        duration = result.payload.get("duration_ms", target_duration_ms)
        return int(duration)

    def _write_audio_payload(self, payload: dict[str, object], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio_base64 = payload.get("audio_base64")
        if isinstance(audio_base64, str) and audio_base64:
            output_path.write_bytes(base64.b64decode(audio_base64))
            return

        audio_path = payload.get("audio_path")
        if isinstance(audio_path, str) and audio_path:
            source_path = Path(audio_path)
            output_path.write_bytes(source_path.read_bytes())
            return

        raise TtsProviderError(
            f"{self.profile.id}: missing audio_base64 or audio_path in response"
        )


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
    max_duration_retries: int = 1,
) -> SynthesisResult:
    if max_duration_retries < 0:
        raise ValueError("max_duration_retries cannot be negative")

    output_dir = project.path / "work" / "generated_segments"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{segment.id}.wav"
    target_duration_ms = segment.end_ms - segment.start_ms
    reference_audio_path = extract_reference_audio(project, segment)
    style_prompt = segment.style_prompt
    retried = False
    for attempt in range(max_duration_retries + 1):
        generated_duration_ms = adapter.synthesize(
            text=segment.target_text,
            speaker_id=segment.speaker_id,
            output_path=output_path,
            style_prompt=style_prompt,
            reference_audio_path=reference_audio_path,
            reference_text=segment.source_text,
            target_duration_ms=target_duration_ms,
        )
        duration_flag = _duration_quality_flag(
            generated_duration_ms,
            target_duration_ms=target_duration_ms,
            tolerance_ms=tolerance_ms,
        )
        if duration_flag == "duration_ok" or attempt >= max_duration_retries:
            break
        retried = True
        style_prompt = _retry_style_prompt(style_prompt, duration_flag)
    quality_flags = _merge_synthesis_quality_flags(
        segment.quality_flags,
        duration_flag=duration_flag,
        reference_missing=reference_audio_path is None,
        silent_audio=_is_silent_wav(output_path),
        tts_retried=retried,
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


def extract_reference_audio(project: DubbingProject, segment: DubbingSegment) -> Path | None:
    source_audio = project.path / "assets" / "extracted_audio.wav"
    if not source_audio.is_file():
        return None

    references = _select_profile_reference_segments(project, segment)
    if not references:
        references = select_reference_segments(project.timeline, speaker_id=segment.speaker_id, limit=1)
    if not references:
        references = [segment]

    reference = references[0]
    output_dir = project.path / "work" / "reference_segments"
    output_path = output_dir / (
        f"{_safe_filename(reference.speaker_id)}-{_safe_filename(reference.id)}.wav"
    )
    if output_path.is_file():
        return output_path

    try:
        _copy_wav_slice(
            source_audio,
            output_path,
            start_ms=reference.start_ms,
            end_ms=reference.end_ms,
        )
    except (EOFError, OSError, wave.Error):
        return None
    return output_path


def _select_profile_reference_segments(
    project: DubbingProject,
    segment: DubbingSegment,
) -> list[DubbingSegment]:
    profile = project.speakers.get(segment.speaker_id)
    if profile is None:
        return []

    references: list[DubbingSegment] = []
    for segment_id in profile.reference_segment_ids:
        try:
            reference = project.timeline.get_segment(segment_id)
        except KeyError:
            continue
        if reference.speaker_id == segment.speaker_id:
            references.append(reference)
    return references


def _copy_wav_slice(source_path: Path, output_path: Path, *, start_ms: int, end_ms: int) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(source_path), "rb") as source_wav:
        frame_rate = source_wav.getframerate()
        total_frames = source_wav.getnframes()
        start_frame = min(int(frame_rate * start_ms / 1000), total_frames)
        end_frame = min(int(frame_rate * end_ms / 1000), total_frames)
        frame_count = max(end_frame - start_frame, 0)
        source_wav.setpos(start_frame)
        frames = source_wav.readframes(frame_count)
        params = source_wav.getparams()

    with wave.open(str(output_path), "wb") as output_wav:
        output_wav.setparams(params)
        output_wav.writeframes(frames)


def _safe_filename(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in "-_." else "_" for char in value)
    return safe or "reference"


def _duration_quality_flag(
    generated_duration_ms: int,
    *,
    target_duration_ms: int,
    tolerance_ms: int,
) -> str:
    if abs(generated_duration_ms - target_duration_ms) <= tolerance_ms:
        return "duration_ok"
    if generated_duration_ms < target_duration_ms:
        return "duration_too_short"
    return "duration_too_long"


def _retry_style_prompt(style_prompt: str | None, duration_flag: str) -> str:
    advice = {
        "duration_too_long": "语速稍快，表达更简短",
        "duration_too_short": "语速稍慢，停顿自然",
    }.get(duration_flag, "")
    parts = [part for part in [style_prompt, advice] if part]
    return "\n".join(parts)


def _merge_synthesis_quality_flags(
    existing_flags: list[str],
    *,
    duration_flag: str,
    reference_missing: bool,
    silent_audio: bool,
    tts_retried: bool = False,
) -> list[str]:
    refreshed_flags = {
        "duration_ok",
        "duration_mismatch",
        "duration_too_short",
        "duration_too_long",
        "missing_reference_audio",
        "silent_audio",
        "tts_retried",
    }
    refreshed = [
        flag
        for flag in existing_flags
        if flag not in refreshed_flags
    ]
    refreshed.append(duration_flag)
    if tts_retried:
        refreshed.append("tts_retried")
    if reference_missing:
        refreshed.append("missing_reference_audio")
    if silent_audio:
        refreshed.append("silent_audio")
    return refreshed


def _is_silent_wav(path: Path) -> bool:
    try:
        with wave.open(str(path), "rb") as wav_file:
            frames = wav_file.readframes(wav_file.getnframes())
            return not frames or audioop.max(frames, wav_file.getsampwidth()) == 0
    except (EOFError, OSError, wave.Error):
        return False


def _write_silent_wav(output_path: Path, *, duration_ms: int) -> None:
    sample_rate = 16_000
    sample_count = int(sample_rate * (duration_ms / 1000))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * sample_count)
