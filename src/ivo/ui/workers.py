from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, Signal

from ivo.local_readiness import check_profiles_readiness


class PipelineWorker(QThread):
    progress = Signal(object)
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


class ReadinessWorker(PipelineWorker):
    def __init__(self, profiles_path: Path, *, models_dir: Path) -> None:
        super().__init__(
            lambda: check_profiles_readiness(
                profiles_path,
                models_dir=models_dir,
            )
        )
