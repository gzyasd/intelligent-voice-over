"""流水线运行 API：WebSocket 进度推送 + REST 控制"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query

from ivo.core.project import DubbingProject
from ivo.core.project_status import read_project_status_snapshot

from .. import pipeline_runner

router = APIRouter()

# 流水线阶段顺序（与前端 STAGE_ORDER 保持一致）
_PIPELINE_STAGE_ORDER = [
    "import",
    "audio_extract",
    "separation",
    "asr",
    "diarization",
    "translation",
    "tts",
    "export",
]


@router.websocket("/ws")
async def pipeline_ws(websocket: WebSocket) -> None:
    """WebSocket 端点：实时推送流水线进度事件

    客户端连接时通过 query 参数指定 project_path。
    WebSocket 只订阅已由 REST 启动的流水线，不会因页面连接而隐式启动任务。
    服务端推送的事件类型：
    - 进度事件：{stage, stage_label, status, message, overall_percent, ...}
    - 完成事件：{type: "finished", error: str | null}
    - 错误事件：{type: "error", message: str}
    """
    await websocket.accept()
    project_path = websocket.query_params.get("project_path")
    if not project_path:
        await websocket.send_json({"type": "error", "message": "缺少 project_path 参数"})
        await websocket.close()
        return

    runner = pipeline_runner.get_runner(project_path)
    if runner is None:
        await websocket.send_json({"type": "error", "message": "流水线尚未启动"})
        await websocket.close()
        return
    try:
        after_event_id = int(websocket.query_params.get("after_event_id", "0"))
    except ValueError:
        after_event_id = 0
    queue = runner.subscribe(
        asyncio.get_running_loop(),
        after_event_id=max(after_event_id, 0),
    )

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # 超时期间检查 runner 是否已结束
                if runner.is_finished:
                    # 推送一次 finished 兜底（防止事件丢失）
                    snapshot = read_project_status_snapshot(
                        Path(project_path),
                        active_project_paths=pipeline_runner.get_active_project_paths(),
                        paused_project_paths=pipeline_runner.get_paused_project_paths(),
                    )
                    await websocket.send_json({
                        "type": "finished",
                        "error": runner.error,
                        "elapsed_seconds": snapshot.elapsed_seconds,
                    })
                    break
                continue
            await websocket.send_json(event)
            if event.get("type") == "finished":
                break
    except WebSocketDisconnect:
        pass
    finally:
        # 仅取消订阅，不移除 runner（允许其他客户端继续订阅或 REST 控制继续工作）
        runner.unsubscribe(queue)


@router.post("/start")
async def start_pipeline(project_path: str = Query(..., description="项目路径")) -> dict[str, Any]:
    """启动流水线

    返回 started 状态。客户端随后应通过 WebSocket 订阅进度。
    """
    runner = pipeline_runner.get_runner(project_path)
    if runner is not None and runner.is_finished:
        pipeline_runner.remove_runner(project_path)
        runner = None
    runner = runner or pipeline_runner.create_runner(project_path)
    if runner.is_running:
        raise HTTPException(status_code=409, detail="流水线已在运行中")
    runner.start(asyncio.get_running_loop())
    return {"status": "started", "project_path": project_path}


@router.post("/pause")
async def pause_pipeline(project_path: str = Query(..., description="项目路径")) -> dict[str, Any]:
    """暂停流水线"""
    runner = pipeline_runner.get_runner(project_path)
    if runner is None:
        raise HTTPException(status_code=404, detail="流水线未找到")
    runner.pause()
    return {"status": "paused"}


@router.post("/resume")
async def resume_pipeline(project_path: str = Query(..., description="项目路径")) -> dict[str, Any]:
    """恢复流水线"""
    runner = pipeline_runner.get_runner(project_path)
    if runner is None:
        raise HTTPException(status_code=404, detail="流水线未找到")
    runner.resume()
    return {"status": "resumed"}


@router.get("/status")
async def get_pipeline_status(project_path: str = Query(..., description="项目路径")) -> dict[str, Any]:
    """获取流水线状态"""
    runner = pipeline_runner.get_runner(project_path)
    snapshot = read_project_status_snapshot(
        Path(project_path),
        active_project_paths=pipeline_runner.get_active_project_paths(),
        paused_project_paths=pipeline_runner.get_paused_project_paths(),
    )
    if runner is None:
        return {
            "running": False,
            "paused": False,
            "finished": False,
            "error": None,
            "started_at": snapshot.generation_started_at,
            "completed_at": snapshot.generation_completed_at,
            "elapsed_seconds": snapshot.elapsed_seconds,
        }
    return {
        "running": runner.is_running,
        "paused": runner.is_paused(),
        "finished": runner.is_finished,
        "error": runner.error,
        "started_at": snapshot.generation_started_at,
        "completed_at": snapshot.generation_completed_at,
        "elapsed_seconds": snapshot.elapsed_seconds,
    }


@router.get("/history")
def get_pipeline_history(project_path: str = Query(..., description="项目路径")) -> dict[str, Any]:
    """获取项目流水线历史阶段记录（从 JobStore 恢复）。

    用于从项目库打开失败/已完成项目时，恢复显示生成进度。
    """
    try:
        project = DubbingProject.load(Path(project_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法加载项目：{e}")

    records = project.jobs.list_records()
    records_map = {r.stage: r for r in records}

    stages: list[dict[str, Any]] = []
    current_stage: str | None = None
    failed_stage: str | None = None
    error_message: str | None = None

    for stage_name in _PIPELINE_STAGE_ORDER:
        record = records_map.get(stage_name)
        if record:
            stages.append({
                "stage": record.stage,
                "status": record.status,
                "message": record.message,
                "started_at": record.started_at,
                "completed_at": record.completed_at,
                "elapsed_seconds": record.elapsed_seconds,
            })
            if record.status == "running":
                current_stage = record.stage
            elif record.status == "failed":
                failed_stage = record.stage
                error_message = record.message
        else:
            stages.append({
                "stage": stage_name,
                "status": "pending",
                "message": "",
                "started_at": None,
                "completed_at": None,
                "elapsed_seconds": None,
            })

    has_history = any(s["status"] != "pending" for s in stages)
    # 判断是否已完成（所有阶段都 completed）
    all_completed = all(s["status"] == "completed" for s in stages)

    return {
        "stages": stages,
        "current_stage": current_stage,
        "has_history": has_history,
        "all_completed": all_completed,
        "failed_stage": failed_stage,
        "error_message": error_message,
        "started_at": project.metadata.generation_started_at,
        "completed_at": project.metadata.generation_completed_at,
        "elapsed_seconds": project.metadata.generation_elapsed_seconds,
    }
