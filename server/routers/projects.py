"""项目管理 API"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ivo.core.project import DubbingProject
from ivo.core.project_library import scan_project_library
from ivo.core.project_status import read_project_status_snapshot
from .. import dependencies, pipeline_runner

router = APIRouter()


class CreateProjectRequest(BaseModel):
    source_media_path: str
    name: str
    source_language: Literal["en", "ja", "ko"]
    target_language: Literal["zh"] = "zh"
    content_type: Literal["video", "audio"] = "video"
    scheme_id: str | None = None


@router.get("")
def list_projects() -> list[dict[str, Any]]:
    """列出项目库"""
    store = dependencies.get_user_settings_store()
    settings = store.load()
    items = scan_project_library(
        projects_dir=settings.projects_dir,
        recent_projects=settings.recent_projects,
        active_project_paths=pipeline_runner.get_active_project_paths(),
        paused_project_paths=pipeline_runner.get_paused_project_paths(),
    )
    return [item.model_dump(mode="json") for item in items]


@router.post("")
def create_project(req: CreateProjectRequest) -> dict[str, Any]:
    """创建项目"""
    source_media = Path(req.source_media_path)
    if not source_media.is_file():
        raise HTTPException(status_code=400, detail=f"源素材不存在: {source_media}")

    store = dependencies.get_user_settings_store()
    settings = store.load()
    project_dir = settings.projects_dir / f"{req.name}.ivoproj"

    if project_dir.exists():
        raise HTTPException(status_code=409, detail=f"项目已存在: {project_dir}")

    if req.scheme_id:
        provider_store = dependencies.get_provider_store()
        if provider_store.get_scheme(req.scheme_id) is None:
            raise HTTPException(status_code=404, detail="Scheme not found")

    project = DubbingProject.create(
        path=project_dir,
        name=req.name,
        source_language=req.source_language,
        target_language=req.target_language,
        content_type=req.content_type,
        source_media=source_media,
        scheme_id=req.scheme_id,
    )

    # 添加到最近项目
    store.add_recent_project(project_dir)

    return project.metadata.model_dump(mode="json")


@router.get("/status")
def get_project_status(path: str = Query(..., description="项目路径")) -> dict[str, Any]:
    """获取项目状态快照"""
    project_path = Path(path)
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail="项目不存在")
    snapshot = read_project_status_snapshot(
        project_path.resolve(),
        active_project_paths=pipeline_runner.get_active_project_paths(),
        paused_project_paths=pipeline_runner.get_paused_project_paths(),
    )
    return snapshot.model_dump(mode="json")


@router.get("/detail")
def get_project(path: str = Query(..., description="项目路径")) -> dict[str, Any]:
    """获取项目元数据"""
    project_path = Path(path)
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail="项目不存在")
    project = DubbingProject.load(project_path.resolve())
    return project.metadata.model_dump(mode="json")


class UpdateProjectProfilesRequest(BaseModel):
    """更新项目 profile 路径设置"""
    local_command_profiles_path: str | None = None
    separation_profile_path: str | None = None
    asr_profile_path: str | None = None
    diarization_profile_path: str | None = None
    translation_profile_path: str | None = None
    tts_profile_path: str | None = None


@router.get("/settings")
def get_project_settings(path: str = Query(..., description="项目路径")) -> dict[str, Any]:
    """获取项目设置（profile 路径 + 翻译设置）"""
    project_path = Path(path)
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail="项目不存在")
    project = DubbingProject.load(project_path.resolve())
    return project.settings.load().model_dump(mode="json")


@router.put("/settings")
def update_project_settings(
    req: UpdateProjectProfilesRequest,
    path: str = Query(..., description="项目路径"),
) -> dict[str, Any]:
    """更新项目 profile 路径设置

    支持显式传 null 清除字段（exclude_unset 语义）。
    """
    project_path = Path(path)
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail="项目不存在")
    project = DubbingProject.load(project_path.resolve())
    settings = project.settings.load()
    changes = req.model_dump(exclude_unset=True)
    if changes:
        updated_profiles = settings.profiles.model_copy(update=changes)
        project.settings.update_profiles(updated_profiles)
    return project.settings.load().model_dump(mode="json")


@router.delete("")
def delete_project(path: str = Query(..., description="Project path")) -> dict[str, Any]:
    """Delete a project directory and clear its library record."""
    project_path = Path(path)
    store = dependencies.get_user_settings_store()

    if ".." in project_path.parts:
        raise HTTPException(status_code=400, detail="Path cannot contain parent traversal")

    if not project_path.name.endswith(".ivoproj"):
        raise HTTPException(status_code=400, detail="Only .ivoproj project directories can be deleted")

    if not project_path.is_dir():
        store.remove_recent_project(project_path)
        return {"deleted": True}

    if not (project_path / "project.json").is_file():
        raise HTTPException(status_code=400, detail="Target directory is not a valid IVO project")

    try:
        shutil.rmtree(project_path)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Delete failed: {exc}") from exc

    store.remove_recent_project(project_path)
    return {"deleted": True}
