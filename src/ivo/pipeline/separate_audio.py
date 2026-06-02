from __future__ import annotations

import shutil
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel

from ivo.adapters.base import AdapterContext
from ivo.adapters.local import CommandRunner, LocalCommandAdapter, LocalCommandProfile
from ivo.core.project import DubbingProject


class SeparationResult(BaseModel):
    vocals_path: Path
    background_path: Path


class SeparationAdapter(Protocol):
    def separate(
        self,
        input_audio: Path,
        *,
        vocals_path: Path,
        background_path: Path,
    ) -> SeparationResult: ...


class MockSeparationAdapter:
    def separate(
        self,
        input_audio: Path,
        *,
        vocals_path: Path,
        background_path: Path,
    ) -> SeparationResult:
        shutil.copy2(input_audio, vocals_path)
        shutil.copy2(input_audio, background_path)
        return SeparationResult(vocals_path=vocals_path, background_path=background_path)


class LocalCommandSeparationAdapter:
    def __init__(
        self,
        profile: LocalCommandProfile,
        *,
        runner: CommandRunner | None = None,
    ) -> None:
        self.profile = profile
        self.adapter = LocalCommandAdapter(profile, runner=runner)

    def separate(
        self,
        input_audio: Path,
        *,
        vocals_path: Path,
        background_path: Path,
    ) -> SeparationResult:
        result = self.adapter.run(
            AdapterContext(
                project_path=input_audio.parent,
                segment_text="",
                source_language="",
                target_language="zh",
                speaker_id="",
                extra={
                    "audio_path": str(input_audio),
                    "vocals_path": str(vocals_path),
                    "background_path": str(background_path),
                },
            )
        )
        if not result.ok:
            message = result.error.message if result.error is not None else "unknown separation error"
            raise RuntimeError(f"{self.profile.id}: {message}")

        produced_vocals = Path(str(result.payload.get("vocals_path", vocals_path)))
        produced_background = Path(str(result.payload.get("background_path", background_path)))
        if produced_vocals != vocals_path:
            shutil.copy2(produced_vocals, vocals_path)
        if produced_background != background_path:
            shutil.copy2(produced_background, background_path)
        if not vocals_path.is_file():
            raise RuntimeError(f"{self.profile.id}: vocals output not found: {vocals_path}")
        if not background_path.is_file():
            raise RuntimeError(f"{self.profile.id}: background output not found: {background_path}")
        return SeparationResult(vocals_path=vocals_path, background_path=background_path)


def separate_audio(
    project: DubbingProject,
    input_audio: Path,
    adapter: SeparationAdapter,
) -> SeparationResult:
    if not input_audio.is_file():
        raise FileNotFoundError(input_audio)

    vocals_path = project.path / "work" / "vocals.wav"
    background_path = project.path / "work" / "background.wav"
    return adapter.separate(
        input_audio,
        vocals_path=vocals_path,
        background_path=background_path,
    )
