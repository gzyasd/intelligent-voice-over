from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QThread, Signal


class PipelineWorker(QThread):
    succeeded = Signal()
    failed = Signal(str)

    def __init__(self, task: Callable[[], Any]) -> None:
        super().__init__()
        self.task = task
        self.result: Any = None

    def run(self) -> None:
        try:
            self.result = self.task()
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.succeeded.emit()
