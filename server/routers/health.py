"""健康检查端点"""

from __future__ import annotations

import sys

from fastapi import APIRouter

from .. import dependencies

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": dependencies.get_app_version(),
        "python_version": sys.version,
    }
