from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from ivo.core.project_status import find_project_output, read_project_status_snapshot


class ProjectLibraryItem(BaseModel):
    name: str
    path: Path
    content_type: str = "video"
    source_media_path: Path | None = None
    source_language: str = ""
    target_language: str = ""
    updated_at: float
    status: str
    status_detail: str = ""
    lifecycle: str = ""
    failed_stage: str | None = None
    elapsed_seconds: int | None = None
    final_output_path: Path | None = None


def scan_project_library(
    projects_dir: Path,
    *,
    recent_projects: list[Path],
    active_project_paths: set[Path] | None = None,
    paused_project_paths: set[Path] | None = None,
) -> list[ProjectLibraryItem]:
    active = active_project_paths or set()
    paused = paused_project_paths or set()
    candidates = _candidate_project_paths(projects_dir, recent_projects)
    items = [
        _read_project_item(path, active_project_paths=active, paused_project_paths=paused)
        for path in candidates
    ]
    return sorted(items, key=lambda item: item.updated_at, reverse=True)


def _candidate_project_paths(projects_dir: Path, recent_projects: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    candidates: list[Path] = []
    if projects_dir.is_dir():
        for path in projects_dir.glob("*.ivoproj"):
            resolved = path.resolve()
            seen.add(resolved)
            candidates.append(resolved)
    for path in recent_projects:
        resolved = path.resolve()
        if not resolved.is_dir():
            continue
        if resolved not in seen:
            seen.add(resolved)
            candidates.append(resolved)
    return candidates


def _read_project_item(
    path: Path,
    *,
    active_project_paths: set[Path],
    paused_project_paths: set[Path] | None = None,
) -> ProjectLibraryItem:
    snapshot = read_project_status_snapshot(
        path,
        active_project_paths=active_project_paths,
        paused_project_paths=paused_project_paths,
    )
    # 从 status_detail 中提取失败阶段（格式为 "{stage}: {message} · 总耗时 ..."）
    failed_stage: str | None = None
    if snapshot.lifecycle == "failed" and snapshot.status_detail:
        detail = snapshot.status_detail
        # 去掉可能的 " · 总耗时 ..." 后缀
        if " · " in detail:
            detail = detail.split(" · ", 1)[0]
        if ": " in detail:
            failed_stage = detail.split(": ", 1)[0]
    return ProjectLibraryItem(
        name=snapshot.name,
        path=snapshot.project_path,
        content_type=snapshot.content_type,
        source_media_path=snapshot.source_media_path,
        source_language=snapshot.source_language,
        target_language=snapshot.target_language,
        updated_at=snapshot.updated_at,
        status=snapshot.status_label,
        status_detail=snapshot.status_detail,
        lifecycle=snapshot.lifecycle,
        failed_stage=failed_stage,
        elapsed_seconds=snapshot.elapsed_seconds,
        final_output_path=snapshot.final_output_path,
    )


def _final_output_path(project_path: Path) -> Path | None:
    return find_project_output(project_path)


def _path_updated_at(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0
