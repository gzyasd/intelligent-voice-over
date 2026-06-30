"""环境诊断 API"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ivo.environment import collect_environment_diagnostics, collect_optional_model_dependencies
from ivo.model_services.local_models import find_venv_python

from .. import dependencies
from ..venv_setup import setup_venv_stream

router = APIRouter()


class SetupVenvRequest(BaseModel):
    mirror: Literal["official", "tsinghua", "aliyun", "ustc"] = "official"


@router.get("/diagnostics")
def diagnostics() -> dict[str, Any]:
    """环境诊断：FFmpeg、NVIDIA、Python 版本"""
    return collect_environment_diagnostics().model_dump()


@router.get("/optional-dependencies")
def optional_dependencies() -> list[dict[str, Any]]:
    """可选模型依赖状态"""
    deps = collect_optional_model_dependencies()
    return [dep.model_dump() for dep in deps]


@router.get("/venvs")
def list_venvs() -> dict[str, Any]:
    """返回已解析的 venv Python 路径（只读诊断信息）。

    用于设置页面显示 .venv 和 .venv-pyannote 的实际路径，
    让用户知道 venv 存放在哪、是否存在。
    同时返回用户配置的自定义路径（如有）。
    """
    settings = dependencies.get_user_settings_store().load()
    custom_paths: dict[str, Path | None] = {
        ".venv": settings.custom_venv_python,
        ".venv-pyannote": settings.custom_pyannote_python,
    }

    venvs: list[dict[str, Any]] = []
    for name in (".venv", ".venv-pyannote"):
        custom = custom_paths[name]
        python_path = find_venv_python(name, custom_python=custom)
        venvs.append(
            {
                "name": name,
                "python_path": str(python_path) if python_path else None,
                "exists": python_path is not None,
                "custom_path": str(custom) if custom else None,
            }
        )
    return {"venvs": venvs}


@router.post("/setup-venv")
async def setup_venv(req: SetupVenvRequest) -> StreamingResponse:
    """自动创建 .venv 和 .venv-pyannote（SSE 流式推送进度）。

    流程：检查/下载 uv → 创建 .venv → 安装依赖 → 创建 .venv-pyannote → 安装 pyannote.audio
    """
    return await setup_venv_stream(req.mirror)
