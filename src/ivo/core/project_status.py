from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from ivo.core.project import DubbingProject

ProjectLifecycle = Literal[
    "unreadable",
    "not_started",
    "running",
    "paused",
    "interrupted",
    "incomplete",
    "failed",
    "completed",
]

ProjectPrimaryAction = Literal["create", "start", "resume", "progress", "open_output"]


class ProjectStatusSnapshot(BaseModel):
    project_path: Path
    name: str
    content_type: str = "video"
    source_media_path: Path | None = None
    source_language: str = ""
    target_language: str = ""
    lifecycle: ProjectLifecycle
    status_label: str
    status_detail: str = ""
    primary_action: ProjectPrimaryAction
    elapsed_seconds: int | None = None
    final_output_path: Path | None = None
    open_output_enabled: bool = False
    updated_at: float = 0.0


def read_project_status_snapshot(
    project_path: Path,
    *,
    active_project_paths: set[Path],
    paused_project_paths: set[Path] | None = None,
) -> ProjectStatusSnapshot:
    try:
        project = DubbingProject.load(project_path)
    except (OSError, ValueError, KeyError) as exc:
        return ProjectStatusSnapshot(
            project_path=project_path,
            name=project_path.stem,
            lifecycle="unreadable",
            status_label="无法读取",
            status_detail=str(exc),
            primary_action="start",
            updated_at=_path_updated_at(project_path),
        )

    final_output = find_project_output(project.path)
    records = project.jobs.list_records()
    failed = next((record for record in records if record.status == "failed"), None)
    running = next((record for record in records if record.status == "running"), None)
    active = project.path.resolve() in active_project_paths
    paused = (
        paused_project_paths is not None
        and project.path.resolve() in paused_project_paths
    )

    lifecycle: ProjectLifecycle
    label: str
    detail = ""
    action: ProjectPrimaryAction

    if failed is not None or project.metadata.generation_status == "failed":
        lifecycle = "failed"
        label = "生成失败"
        detail = f"{failed.stage}: {failed.message}" if failed is not None else ""
        action = "resume"
    elif running is not None or project.metadata.generation_status == "running":
        if active:
            if paused:
                lifecycle = "paused"
                label = "已暂停"
                action = "progress"
            else:
                lifecycle = "running"
                label = "生成中"
                action = "progress"
        else:
            lifecycle = "interrupted"
            label = "上次中断"
            detail = f"{running.stage}: {running.message}" if running is not None else ""
            action = "resume"
    elif final_output is not None or project.metadata.generation_status == "completed":
        lifecycle = "completed"
        label = "已完成"
        action = "open_output"
    elif records:
        lifecycle = "incomplete"
        label = "未完成"
        action = "resume"
    else:
        lifecycle = "not_started"
        label = "未开始"
        action = "start"

    return ProjectStatusSnapshot(
        project_path=project.path,
        name=project.name,
        content_type=project.content_type,
        source_media_path=project.source_media_path,
        source_language=project.source_language,
        target_language=project.target_language,
        lifecycle=lifecycle,
        status_label=label,
        status_detail=_append_elapsed_detail(detail, project.metadata.generation_elapsed_seconds),
        primary_action=action,
        elapsed_seconds=project.metadata.generation_elapsed_seconds,
        final_output_path=final_output,
        open_output_enabled=final_output is not None,
        updated_at=_path_updated_at(project.path),
    )


def find_project_output(project_path: Path) -> Path | None:
    for candidate in (
        project_path / "renders" / "final.mp4",
        project_path / "renders" / "final.wav",
        project_path / "renders" / "final.mp3",
        project_path / "renders" / "local-preview.mp4",
        project_path / "renders" / "local-preview.wav",
    ):
        if candidate.is_file():
            return candidate
    return None


def _append_elapsed_detail(detail: str, elapsed_seconds: int | None) -> str:
    if elapsed_seconds is None:
        return detail
    elapsed = f"总耗时 {_format_elapsed(elapsed_seconds)}"
    return f"{detail} · {elapsed}" if detail else elapsed


def _format_elapsed(seconds: int) -> str:
    minutes, rest = divmod(max(0, seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{rest:02d}"
    return f"{minutes:02d}:{rest:02d}"


def _path_updated_at(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0
