"""Async job adapter base class for multi-step API providers."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from ivo.adapters.base import AdapterError, AdapterResult


class AsyncJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class AsyncJobHandle:
    job_id: str
    provider_id: str
    stage: str
    created_at: float


class AsyncJobAdapter(ABC):
    """Base class for async multi-step API adapters."""

    POLL_INTERVAL_INITIAL: float = 2.0
    POLL_INTERVAL_MAX: float = 30.0
    POLL_BACKOFF_FACTOR: float = 1.5
    POLL_TIMEOUT: float = 600.0  # 10 minutes

    provider_id: str
    stage: str

    @abstractmethod
    def create_job(self, **kwargs: Any) -> AsyncJobHandle: ...

    @abstractmethod
    def check_status(self, handle: AsyncJobHandle) -> AsyncJobStatus: ...

    @abstractmethod
    def download_result(self, handle: AsyncJobHandle, output_path: Path) -> None: ...

    def execute(self, output_path: Path, **kwargs: Any) -> AdapterResult:
        """Full async workflow: create → poll → download."""
        handle = self.create_job(**kwargs)
        status = self._poll_until_done(handle)
        if status == AsyncJobStatus.COMPLETED:
            self.download_result(handle, output_path)
            return AdapterResult(
                stage=self.stage,
                provider=self.provider_id,
                ok=True,
                payload={"output_path": str(output_path)},
            )
        return AdapterResult(
            stage=self.stage,
            provider=self.provider_id,
            ok=False,
            payload={},
            error=AdapterError(
                provider=self.provider_id,
                stage=self.stage,
                message=f"Async job {status.value}",
            ),
        )

    def _poll_until_done(self, handle: AsyncJobHandle) -> AsyncJobStatus:
        interval = self.POLL_INTERVAL_INITIAL
        elapsed = 0.0
        while elapsed < self.POLL_TIMEOUT:
            status = self.check_status(handle)
            if status in (AsyncJobStatus.COMPLETED, AsyncJobStatus.FAILED):
                return status
            time.sleep(interval)
            elapsed += interval
            interval = min(interval * self.POLL_BACKOFF_FACTOR, self.POLL_INTERVAL_MAX)
        return AsyncJobStatus.TIMEOUT
