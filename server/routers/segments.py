"""片段管理 API"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ivo.core.project import DubbingProject
from ivo.core.timeline import SegmentStatusValue
from ivo.model_services.adapter_factory import ProviderAdapterFactory
from ivo.model_services.provider_config import StageProviderConfig
from ivo.model_services.provider_store import ProviderStore
from ivo.model_services.scheme_compiler import SchemeRuntimeCompiler
from ivo.pipeline.orchestrator import regenerate_segment
from .. import dependencies

router = APIRouter()


class _StageConfigStoreAdapter:
    """适配 ProviderStore 到 StageProviderConfigStore Protocol。"""

    def __init__(self, store: ProviderStore) -> None:
        self._store = store

    def get(self, config_id: str) -> StageProviderConfig:
        config = self._store.get_stage_config(config_id)
        if config is None:
            raise KeyError(f"Stage config not found: {config_id}")
        return config


class UpdateSegmentRequest(BaseModel):
    target_text: str | None = None
    speaker_id: str | None = None
    emotion: str | None = None
    style_prompt: str | None = None
    status: SegmentStatusValue | None = None


class BatchUpdateSegmentRequest(BaseModel):
    segment_ids: list[str]
    status: SegmentStatusValue


class RegenerateSegmentRequest(BaseModel):
    target_text: str | None = None
    speaker_id: str | None = None
    emotion: str | None = None
    style_prompt: str | None = None
    speech_rate: float | None = None


@router.get("/segments")
def list_segments(path: str = Query(..., description="项目路径")) -> list[dict[str, Any]]:
    """列出所有片段"""
    project_path = Path(path)
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail="项目不存在")
    project = DubbingProject.load(project_path.resolve())
    segments = project.timeline.list_segments()
    return [seg.model_dump(mode="json") for seg in segments]


@router.get("/segments/{segment_id}")
def get_segment(
    segment_id: str,
    path: str = Query(..., description="项目路径"),
) -> dict[str, Any]:
    """获取单个片段"""
    project_path = Path(path)
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail="项目不存在")
    project = DubbingProject.load(project_path.resolve())
    try:
        segment = project.timeline.get_segment(segment_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="片段不存在") from None
    return segment.model_dump(mode="json")


@router.put("/segments/{segment_id}")
def update_segment(
    segment_id: str,
    req: UpdateSegmentRequest,
    path: str = Query(..., description="项目路径"),
) -> dict[str, Any]:
    """更新片段（译文/说话人/情绪/风格/状态）"""
    project_path = Path(path)
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail="项目不存在")
    project = DubbingProject.load(project_path.resolve())
    try:
        project.timeline.get_segment(segment_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="片段不存在") from None

    changes = req.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="没有需要更新的字段")

    project.timeline.update_segment(segment_id, **changes)
    try:
        updated = project.timeline.get_segment(segment_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="片段不存在") from None
    return updated.model_dump(mode="json")


@router.put("/segments/batch/status")
def batch_update_status(
    req: BatchUpdateSegmentRequest,
    path: str = Query(..., description="项目路径"),
) -> dict[str, Any]:
    """批量更新片段状态"""
    project_path = Path(path)
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail="项目不存在")
    project = DubbingProject.load(project_path.resolve())
    for seg_id in req.segment_ids:
        project.timeline.update_segment(seg_id, status=req.status)
    return {"updated": len(req.segment_ids)}


@router.post("/segments/{segment_id}/regenerate")
def regenerate_segment_audio(
    segment_id: str,
    req: RegenerateSegmentRequest,
    path: str = Query(..., description="项目路径"),
) -> dict[str, Any]:
    """重新合成单个片段的音频"""
    project_path = Path(path)
    if not project_path.is_dir():
        raise HTTPException(status_code=404, detail="项目不存在")
    project = DubbingProject.load(project_path.resolve())

    try:
        project.timeline.get_segment(segment_id)  # 校验片段存在
    except KeyError:
        raise HTTPException(status_code=404, detail="片段不存在") from None

    # 编译方案获取 TTS 适配器
    store = dependencies.get_provider_store()
    scheme_id = project.metadata.scheme_id or store.load_default_scheme_id()
    if scheme_id is None:
        raise HTTPException(status_code=400, detail="未设置默认配音方案")
    scheme = store.get_scheme(scheme_id)
    if scheme is None:
        raise HTTPException(status_code=400, detail="默认方案不存在")

    registry = dependencies.get_provider_registry()
    secret_store = dependencies.get_secret_store()
    user_settings = dependencies.get_user_settings_store().load()
    factory = ProviderAdapterFactory(
        registry=registry,
        provider_store=store,
        secret_store=secret_store,
        local_python=user_settings.custom_venv_python,
        pyannote_python=user_settings.custom_pyannote_python,
    )
    compiler = SchemeRuntimeCompiler(
        registry=registry,
        config_store=_StageConfigStoreAdapter(store),
        adapter_factory=factory,
    )
    compiled = compiler.compile(scheme)
    if compiled.tts is None:
        raise HTTPException(status_code=400, detail="方案未配置 TTS 阶段")

    changes = req.model_dump(exclude_unset=True)
    try:
        result = regenerate_segment(project, segment_id, compiled.tts, **changes)
    except KeyError:
        raise HTTPException(status_code=404, detail="片段不存在") from None
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"重合成失败: {exc}") from exc

    try:
        updated = project.timeline.get_segment(segment_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="片段不存在") from None
    return {
        "segment": updated.model_dump(mode="json"),
        "audio_path": str(result.audio_path) if result.audio_path else None,
        "duration_ms": result.generated_duration_ms,
    }
