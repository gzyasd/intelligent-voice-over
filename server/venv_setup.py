"""Venv 自动创建逻辑：安装 uv → 创建 .venv → 创建 .venv-pyannote。

通过 SSE（Server-Sent Events）向前端推送实时进度。
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import sys
from pathlib import Path
from typing import AsyncIterator

import httpx
from fastapi.responses import StreamingResponse

from ivo.core.user_settings import PYPI_MIRRORS, PipMirrorKey


def _sse(data: dict[str, object]) -> str:
    """Format a single SSE event."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _get_runtime_root() -> Path:
    """获取 venv 应创建的目标目录。

    生产模式：resources/ 目录（ivo-server.exe 的父目录的父目录）
    开发模式：项目根目录
    """
    exe_dir = Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False):
        # resources/python/ivo-server.exe → resources/
        return exe_dir.parent
    # 开发模式：.venv/Scripts/python.exe → 项目根目录
    if (exe_dir.parent / "pyvenv.cfg").is_file():
        return exe_dir.parent.parent
    return Path.cwd().resolve()


def _get_requirements_path() -> Path:
    """获取 requirements-venv.txt 路径。"""
    root = _get_runtime_root()
    candidates = [
        root / "requirements-venv.txt",
        root.parent / "requirements-venv.txt",
    ]
    for p in candidates:
        if p.is_file():
            return p
    # 开发模式回退到项目根
    return Path(__file__).resolve().parent.parent / "requirements-venv.txt"


async def _find_uv() -> str | None:
    """检查系统是否已安装 uv。"""
    # 1. 检查 PATH
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path
    # 2. 检查常见安装位置
    home = Path.home()
    common = [
        home / ".local" / "bin" / "uv.exe",
        home / ".cargo" / "bin" / "uv.exe",
        home / "AppData" / "Roaming" / "uv" / "uv.exe",
    ]
    for p in common:
        if p.is_file():
            return str(p)
    return None


async def _download_uv(target_dir: Path) -> str:
    """下载 uv 独立二进制到指定目录。"""
    target_dir.mkdir(parents=True, exist_ok=True)
    uv_exe = target_dir / "uv.exe"
    # GitHub releases: uv-x86_64-pc-windows-msvc.zip
    url = "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.exe"
    # 直接下载 exe（不需要解压）
    async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        uv_exe.write_bytes(resp.content)
    return str(uv_exe)


async def _run_subprocess_with_stream(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> AsyncIterator[str]:
    """运行子进程，逐行 yield stdout/stderr。"""
    full_env = os.environ.copy()
    if env:
        full_env.update(env)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(cwd) if cwd else None,
        env=full_env,
    )

    assert proc.stdout is not None
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        yield line.decode("utf-8", errors="replace").rstrip("\r\n")

    await proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"命令失败 (exit code {proc.returncode}): {' '.join(cmd)}")


def _mirror_url(mirror: PipMirrorKey) -> str:
    """获取 pip 镜像 URL。"""
    _, url = PYPI_MIRRORS.get(mirror, ("", ""))
    return url or "https://pypi.org/simple"


async def setup_venv_stream(
    mirror: PipMirrorKey,
) -> StreamingResponse:
    """创建 venv 的 SSE 流。"""

    async def event_stream() -> AsyncIterator[str]:
        root = _get_runtime_root()
        mirror_u = _mirror_url(mirror)

        # ── Step 1: 检查/安装 uv ──
        yield _sse({"step": "uv", "status": "running", "message": "正在检查 uv..."})
        uv_path = await _find_uv()
        if uv_path:
            yield _sse({"step": "uv", "status": "done", "message": f"uv 已就绪: {uv_path}"})
        else:
            yield _sse({"step": "uv", "status": "running", "message": "uv 未找到，正在下载..."})
            try:
                uv_dir = root / "uv-bin"
                uv_path = await _download_uv(uv_dir)
                yield _sse({"step": "uv", "status": "done", "message": f"uv 下载完成: {uv_path}"})
            except Exception as e:
                yield _sse({"step": "uv", "status": "error", "message": f"uv 下载失败: {e}"})
                return

        # ── Step 2: 创建主 .venv ──
        venv_dir = root / ".venv"
        venv_python = venv_dir / "Scripts" / "python.exe"

        if venv_python.is_file():
            yield _sse({
                "step": "main-venv",
                "status": "done",
                "message": ".venv 已存在，跳过创建",
            })
        else:
            yield _sse({
                "step": "main-venv",
                "status": "running",
                "message": "正在创建主虚拟环境 .venv（下载 Python 3.10）...",
            })
            try:
                async for line in _run_subprocess_with_stream(
                    [uv_path, "venv", "--python", "3.10", str(venv_dir)],
                    cwd=root,
                ):
                    yield _sse({"step": "main-venv", "status": "log", "message": line})
                yield _sse({"step": "main-venv", "status": "done", "message": ".venv 创建完成"})
            except Exception as e:
                yield _sse({"step": "main-venv", "status": "error", "message": f".venv 创建失败: {e}"})
                return

        # ── Step 3: 安装主 venv 依赖 ──
        yield _sse({
            "step": "main-deps",
            "status": "running",
            "message": "正在安装主环境依赖（torch、demucs、f5-tts 等，体积较大）...",
        })
        req_path = _get_requirements_path()
        try:
            uv_env: dict[str, str] = {}
            if mirror_u:
                uv_env["UV_INDEX_URL"] = mirror_u

            async for line in _run_subprocess_with_stream(
                [uv_path, "pip", "install", "--python", str(venv_python), "-r", str(req_path)],
                cwd=root,
                env=uv_env,
            ):
                yield _sse({"step": "main-deps", "status": "log", "message": line})
            yield _sse({"step": "main-deps", "status": "done", "message": "主环境依赖安装完成"})
        except Exception as e:
            yield _sse({"step": "main-deps", "status": "error", "message": f"主环境依赖安装失败: {e}"})
            return

        # ── Step 4: 创建 .venv-pyannote ──
        pyannote_dir = root / ".venv-pyannote"
        pyannote_python = pyannote_dir / "Scripts" / "python.exe"

        if pyannote_python.is_file():
            yield _sse({
                "step": "pyannote-venv",
                "status": "done",
                "message": ".venv-pyannote 已存在，跳过创建",
            })
        else:
            yield _sse({
                "step": "pyannote-venv",
                "status": "running",
                "message": "正在创建 pyannote 虚拟环境...",
            })
            try:
                async for line in _run_subprocess_with_stream(
                    [uv_path, "venv", "--python", "3.10", str(pyannote_dir)],
                    cwd=root,
                ):
                    yield _sse({"step": "pyannote-venv", "status": "log", "message": line})
                yield _sse({"step": "pyannote-venv", "status": "done", "message": ".venv-pyannote 创建完成"})
            except Exception as e:
                yield _sse({"step": "pyannote-venv", "status": "error", "message": f".venv-pyannote 创建失败: {e}"})
                return

        # ── Step 5: 安装 pyannote.audio ──
        yield _sse({
            "step": "pyannote-deps",
            "status": "running",
            "message": "正在安装 pyannote.audio...",
        })
        try:
            pyannote_env: dict[str, str] = {}
            if mirror_u:
                pyannote_env["UV_INDEX_URL"] = mirror_u

            async for line in _run_subprocess_with_stream(
                [uv_path, "pip", "install", "--python", str(pyannote_python), "pyannote.audio"],
                cwd=root,
                env=pyannote_env,
            ):
                yield _sse({"step": "pyannote-deps", "status": "log", "message": line})
            yield _sse({"step": "pyannote-deps", "status": "done", "message": "pyannote.audio 安装完成"})
        except Exception as e:
            yield _sse({"step": "pyannote-deps", "status": "error", "message": f"pyannote.audio 安装失败: {e}"})
            return

        # ── Complete ──
        yield _sse({"step": "complete", "status": "done", "message": "环境配置完成！所有依赖已安装。"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
