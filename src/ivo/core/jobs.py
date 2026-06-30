from __future__ import annotations

import sqlite3
import time
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
    started_at: float | None = None
    completed_at: float | None = None
    elapsed_seconds: int | None = None
    updated_at: float = 0.0


class JobStore:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._initialize()

    def get(self, stage: str) -> JobRecord | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT stage, status, message, started_at, completed_at, elapsed_seconds, updated_at
                FROM jobs
                WHERE stage = ?
                """,
                (stage,),
            ).fetchone()
        if row is None:
            return None
        return self._record_from_row(row)

    def list_records(self) -> list[JobRecord]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT stage, status, message, started_at, completed_at, elapsed_seconds, updated_at
                FROM jobs
                ORDER BY stage ASC
                """
            ).fetchall()
        return [self._record_from_row(row) for row in rows]

    def mark_running(
        self,
        stage: str,
        message: str = "running",
        *,
        now: float | None = None,
    ) -> None:
        timestamp = time.time() if now is None else now
        self._upsert_running(stage, message, timestamp)

    def mark_completed(
        self,
        stage: str,
        message: str = "completed",
        *,
        now: float | None = None,
    ) -> None:
        self._finish(stage, "completed", message, now=now)

    def mark_failed(self, stage: str, message: str, *, now: float | None = None) -> None:
        self._finish(stage, "failed", message, now=now)

    def _upsert_running(self, stage: str, message: str, timestamp: float) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs (
                    stage,
                    status,
                    message,
                    started_at,
                    completed_at,
                    elapsed_seconds,
                    updated_at
                )
                VALUES (?, 'running', ?, ?, NULL, NULL, ?)
                ON CONFLICT(stage) DO UPDATE SET
                    status = excluded.status,
                    message = excluded.message,
                    started_at = excluded.started_at,
                    completed_at = NULL,
                    elapsed_seconds = NULL,
                    updated_at = excluded.updated_at
                """,
                (stage, message, timestamp, timestamp),
            )

    def _finish(
        self,
        stage: str,
        status: JobStatusValue,
        message: str,
        *,
        now: float | None,
    ) -> None:
        timestamp = time.time() if now is None else now
        with self._connect() as connection:
            row = connection.execute(
                "SELECT started_at FROM jobs WHERE stage = ?",
                (stage,),
            ).fetchone()
            started_at = row["started_at"] if row is not None else None
            if started_at is None:
                started_at = timestamp
            elapsed_seconds = max(0, round(timestamp - started_at))
            connection.execute(
                """
                INSERT INTO jobs (
                    stage,
                    status,
                    message,
                    started_at,
                    completed_at,
                    elapsed_seconds,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stage) DO UPDATE SET
                    status = excluded.status,
                    message = excluded.message,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    elapsed_seconds = excluded.elapsed_seconds,
                    updated_at = excluded.updated_at
                """,
                (
                    stage,
                    status,
                    message,
                    started_at,
                    timestamp,
                    elapsed_seconds,
                    timestamp,
                ),
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
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(jobs)").fetchall()
            }
            migrations = {
                "started_at": "ALTER TABLE jobs ADD COLUMN started_at REAL",
                "completed_at": "ALTER TABLE jobs ADD COLUMN completed_at REAL",
                "elapsed_seconds": "ALTER TABLE jobs ADD COLUMN elapsed_seconds INTEGER",
                "updated_at": "ALTER TABLE jobs ADD COLUMN updated_at REAL NOT NULL DEFAULT 0",
            }
            for column, statement in migrations.items():
                if column not in columns:
                    connection.execute(statement)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            stage=row["stage"],
            status=row["status"],
            message=row["message"],
            started_at=row["started_at"],
            completed_at=row["completed_at"],
            elapsed_seconds=row["elapsed_seconds"],
            updated_at=row["updated_at"],
        )
