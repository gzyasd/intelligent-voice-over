from __future__ import annotations

import sqlite3
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class SegmentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    FAILED = "failed"
    RENDERED = "rendered"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


JobStatusValue = Literal["pending", "running", "completed", "failed", "skipped"]


class JobRecord(BaseModel):
    stage: str
    status: JobStatusValue
    message: str


class JobStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._initialize()

    def get(self, stage: str) -> JobRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT stage, status, message FROM jobs WHERE stage = ?",
                (stage,),
            ).fetchone()
        if row is None:
            return None
        return JobRecord(stage=row["stage"], status=row["status"], message=row["message"])

    def mark_running(self, stage: str, message: str = "running") -> None:
        self._upsert(stage, "running", message)

    def mark_completed(self, stage: str, message: str = "completed") -> None:
        self._upsert(stage, "completed", message)

    def mark_failed(self, stage: str, message: str) -> None:
        self._upsert(stage, "failed", message)

    def _upsert(self, stage: str, status: JobStatusValue, message: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (stage, status, message)
                VALUES (?, ?, ?)
                ON CONFLICT(stage) DO UPDATE SET status = excluded.status, message = excluded.message
                """,
                (stage, status, message),
            )

    def _initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    stage TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    message TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection
