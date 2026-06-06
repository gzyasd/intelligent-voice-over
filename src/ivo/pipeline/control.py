from __future__ import annotations

from threading import Event


class PipelineControl:
    def __init__(self) -> None:
        self._resume_event = Event()
        self._resume_event.set()

    def pause(self) -> None:
        self._resume_event.clear()

    def resume(self) -> None:
        self._resume_event.set()

    def is_paused(self) -> bool:
        return not self._resume_event.is_set()

    def wait_if_paused(self) -> None:
        self._resume_event.wait()
