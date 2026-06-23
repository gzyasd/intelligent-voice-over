"""用户设置 API"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Literal

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, ValidationError

from ivo.core.project import ProjectMetadata
from ivo.core.user_settings import PYPI_MIRRORS

from .. import dependencies

router = APIRouter()


class UpdateSettingsRequest(BaseModel):
    models_dir: str | None = None
    projects_dir: str | None = None
    preferred_preset_id: str | None = None
    prefer_gpu: bool | None = None
    lm_studio_base_url: str | None = None
    theme: Literal["light", "dark", "system"] | None = None
    pip_mirror: Literal["official", "tsinghua", "aliyun", "ustc"] | None = None
    custom_venv_python: str | None = None
    custom_pyannote_python: str | None = None


@router.get("")
def get_settings() -> dict[str, Any]:
    """获取用户设置"""
    store = dependencies.get_user_settings_store()
    return store.load().model_dump(mode="json")


@router.put("")
def update_settings(req: UpdateSettingsRequest) -> dict[str, Any]:
    """更新用户设置"""
    store = dependencies.get_user_settings_store()
    settings = store.load()
    changes = req.model_dump(exclude_unset=True)
    if changes:
        if "models_dir" in changes:
            changes["models_dir"] = Path(changes["models_dir"])
        if "projects_dir" in changes:
            changes["projects_dir"] = Path(changes["projects_dir"])
        # 自定义 venv 路径：空字符串转为 None（清空自定义路径）
        if "custom_venv_python" in changes:
            val = changes["custom_venv_python"]
            changes["custom_venv_python"] = Path(val) if val else None
        if "custom_pyannote_python" in changes:
            val = changes["custom_pyannote_python"]
            changes["custom_pyannote_python"] = Path(val) if val else None
        settings = settings.model_copy(update=changes)
        store.save(settings)
    return settings.model_dump(mode="json")


@router.get("/recent-projects")
def get_recent_projects() -> list[dict[str, Any]]:
    """获取最近项目列表（含完整项目元数据）。

    对每个路径尝试读取 project.json；若项目缺失或元数据损坏，
    则标记 missing=True 以便前端提示用户清理。
    """
    store = dependencies.get_user_settings_store()
    settings = store.load()
    results: list[dict[str, Any]] = []
    for project_path in settings.recent_projects:
        entry: dict[str, Any] = {"path": str(project_path)}
        metadata_path = project_path / "project.json"
        if metadata_path.is_file():
            try:
                data = json.loads(metadata_path.read_text(encoding="utf-8"))
                metadata = ProjectMetadata.model_validate(data)
                entry.update(metadata.model_dump(mode="json"))
                entry["missing"] = False
            except (OSError, ValueError, ValidationError):
                entry["missing"] = True
        else:
            entry["missing"] = True
        results.append(entry)
    return results


@router.get("/test-pypi-connection")
async def test_pypi_connection() -> dict[str, Any]:
    """测试当前 PyPI 镜像的连通性。

    用于安装依赖前检查网络，若不可用提示用户切换镜像。
    """
    store = dependencies.get_user_settings_store()
    settings = store.load()
    mirror_url = PYPI_MIRRORS.get(settings.pip_mirror, ("", ""))[1]
    test_url = mirror_url or "https://pypi.org/simple"
    start = time.time()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.head(test_url, follow_redirects=True)
            latency_ms = int((time.time() - start) * 1000)
            return {
                "ok": resp.status_code < 400,
                "latency_ms": latency_ms,
                "status_code": resp.status_code,
                "url": test_url,
                "error": None,
            }
    except Exception as e:
        return {
            "ok": False,
            "latency_ms": int((time.time() - start) * 1000),
            "status_code": None,
            "url": test_url,
            "error": str(e)[:200],
        }


@router.get("/test-mirrors")
async def test_mirrors() -> dict[str, Any]:
    """一键测试所有 PyPI 镜像的连通性和延迟。

    并行测试所有镜像，按延迟升序排序，不可用的排最后。
    """

    async def _test_one(key: str, label: str, url: str) -> dict[str, Any]:
        test_url = url or "https://pypi.org/simple"
        start = time.time()
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.head(test_url, follow_redirects=True)
                latency_ms = int((time.time() - start) * 1000)
                return {
                    "key": key,
                    "label": label,
                    "url": test_url,
                    "ok": resp.status_code < 400,
                    "latency_ms": latency_ms,
                    "status_code": resp.status_code,
                    "error": None,
                }
        except Exception as e:
            return {
                "key": key,
                "label": label,
                "url": test_url,
                "ok": False,
                "latency_ms": int((time.time() - start) * 1000),
                "status_code": None,
                "error": str(e)[:200],
            }

    tasks = [_test_one(k, v[0], v[1]) for k, v in PYPI_MIRRORS.items()]
    results = await asyncio.gather(*tasks)
    # 按延迟升序，不可用的排后面
    results_sorted = sorted(results, key=lambda r: (not r["ok"], r["latency_ms"]))
    return {"results": results_sorted}
