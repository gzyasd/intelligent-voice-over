from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from ivo.core.project import DubbingProject


class ProjectLibraryItem(BaseModel):
    name: str
    path: Path
    source_video_path: Path | None = None
    source_language: str = ""
    target_language: str = ""
    updated_at: float
    status: str
    status_detail: str = ""
    final_video_path: Path | None = None


def scan_project_library(
    projects_dir: Path,
    *,
    recent_projects: list[Path],
) -> list[ProjectLibraryItem]:
    candidates = _candidate_project_paths(projects_dir, recent_projects)
    items = [_read_project_item(path) for path in candidates]
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
        if resolved not in seen:
            seen.add(resolved)
            candidates.append(resolved)
    return candidates


def _read_project_item(path: Path) -> ProjectLibraryItem:
    try:
        project = DubbingProject.load(path)
    except (OSError, ValueError, KeyError) as exc:
        return ProjectLibraryItem(
            name=path.stem,
            path=path,
            updated_at=_path_updated_at(path),
            status="无法读取",
            status_detail=str(exc),
        )

    final_video = _final_video_path(project.path)
    status, detail = _project_status(project, final_video)
    return ProjectLibraryItem(
        name=project.name,
        path=project.path,
        source_video_path=project.source_video_path,
        source_language=project.source_language,
        target_language=project.target_language,
        updated_at=_path_updated_at(project.path),
        status=status,
        status_detail=detail,
        final_video_path=final_video,
    )


def _project_status(project: DubbingProject, final_video: Path | None) -> tuple[str, str]:
    records = project.jobs.list_records()
    failed = next((record for record in records if record.status == "failed"), None)
    if failed is not None:
        return "失败", f"{failed.stage}: {failed.message}"
    if any(record.status == "running" for record in records):
        return "生成中", ""
    export_record = next((record for record in records if record.stage == "export"), None)
    if final_video is not None or (
        export_record is not None and export_record.status == "completed"
    ):
        return "已完成", ""
    if records:
        return "未完成", ""
    return "未开始", ""


def _final_video_path(project_path: Path) -> Path | None:
    for candidate in (
        project_path / "renders" / "final.mp4",
        project_path / "renders" / "local-preview.mp4",
    ):
        if candidate.is_file():
            return candidate
    return None


def _path_updated_at(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0
