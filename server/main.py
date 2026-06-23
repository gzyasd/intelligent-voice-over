"""IVO FastAPI 后端入口"""

from __future__ import annotations

import sys
from pathlib import Path

# 确保能 import ivo 包
_src = str(Path(__file__).resolve().parent.parent / "src")
if _src not in sys.path:
    sys.path.insert(0, _src)

import uvicorn  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from . import dependencies  # noqa: E402
from .routers import (  # noqa: E402
    accounts,
    environment,
    export,
    files,
    health,
    local_models,
    pipeline,
    projects,
    providers,
    schemes,
    segments,
    settings,
    stage_configs,
)

app = FastAPI(
    title="IVO API",
    version=dependencies.get_app_version(),
    docs_url="/docs",
    redoc_url="/redoc",
)

# 开发模式 CORS（Vite dev server）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, tags=["health"])
app.include_router(environment.router, prefix="/environment", tags=["environment"])
app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(segments.router, prefix="/projects", tags=["segments"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])
app.include_router(files.router, prefix="/files", tags=["files"])
app.include_router(providers.router, prefix="/providers", tags=["providers"])
app.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
app.include_router(stage_configs.router, prefix="/stage-configs", tags=["stage-configs"])
app.include_router(schemes.router, prefix="/schemes", tags=["schemes"])
app.include_router(local_models.router, prefix="/local-models", tags=["local-models"])
app.include_router(pipeline.router, prefix="/pipeline", tags=["pipeline"])
app.include_router(export.router, prefix="/export", tags=["export"])


def main() -> None:
    port = 17000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            sys.stderr.write(
                "ERROR: ivo-server is a FastAPI server entry, not a Python interpreter.\n"
                f"Received non-numeric argument: {sys.argv[1]}\n"
                "If you intended to run a local model script, the application must "
                "configure IVO_LOCAL_PYTHON to point to a .venv Python executable.\n"
            )
            sys.exit(1)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="info")


if __name__ == "__main__":
    main()
