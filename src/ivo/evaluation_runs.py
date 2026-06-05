from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class EvaluationRunRecord(BaseModel):
    date: str
    title: str
    source_language: str
    duration_seconds: int
    profile_path: str
    command: str
    output_video: str | None = None
    status: Literal["passed", "failed", "partial"]
    notes: list[str] = Field(default_factory=list)


def render_run_markdown(record: EvaluationRunRecord) -> str:
    lines = [
        f"# {record.date} {record.title}",
        "",
        "## Summary",
        "",
        f"- date: {record.date}",
        f"- title: {record.title}",
        f"- source_language: {record.source_language}",
        f"- duration_seconds: {record.duration_seconds}",
        f"- profile_path: {record.profile_path}",
        f"- status: {record.status}",
        f"- output_video: {record.output_video or 'not recorded'}",
        "",
        "## Command",
        "",
        "```powershell",
        record.command,
        "```",
        "",
        "## Notes",
        "",
    ]
    if record.notes:
        lines.extend(f"- {note}" for note in record.notes)
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def default_run_output_path(title: str, *, today: date | None = None) -> Path:
    run_date = today or date.today()
    return Path("docs") / "evaluation" / "runs" / f"{run_date:%Y-%m-%d}-{_slugify(title)}.md"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "evaluation-run"
