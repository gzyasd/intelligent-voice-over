"""Stage provider configuration API."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ivo.model_services.local_models import get_local_service
from ivo.model_services.provider_config import ProviderKind, StageProviderConfig
from ivo.model_services.provider_registry import ProviderRegistryEntry
from ivo.model_services.stages import StageName

from .. import dependencies

router = APIRouter()


class CreateStageConfigRequest(BaseModel):
    display_name: str
    provider_key: str
    kind: ProviderKind
    stage: StageName
    protocol: str
    account_id: str | None = None
    model_name: str = ""
    local_model_path: str = ""
    device: str = "auto"
    precision: str = "auto"
    quality_preset: str = "balanced"
    upload_media_to_cloud: bool = False
    extra: dict[str, object] = {}


class UpdateStageConfigRequest(BaseModel):
    display_name: str | None = None
    account_id: str | None = None
    model_name: str | None = None
    local_model_path: str | None = None
    device: str | None = None
    precision: str | None = None
    quality_preset: str | None = None
    upload_media_to_cloud: bool | None = None
    extra: dict[str, object] | None = None


def _provider_entry(provider_key: str) -> ProviderRegistryEntry:
    registry = dependencies.get_provider_registry()
    entry = registry.get(provider_key)
    if entry is None:
        raise HTTPException(status_code=400, detail=f"供应商不存在: {provider_key}")
    return entry


def _validate_provider_for_stage(
    *,
    entry: ProviderRegistryEntry,
    provider_key: str,
    kind: ProviderKind,
    stage: StageName,
    protocol: str,
) -> None:
    if stage not in entry.supported_stages:
        raise HTTPException(
            status_code=400,
            detail=f"供应商 {provider_key} 不支持阶段 {stage}",
        )
    expected_kind: ProviderKind = "api" if entry.requires_api_key else "local"
    if kind != expected_kind:
        raise HTTPException(
            status_code=400,
            detail=f"供应商 {provider_key} 类型应为 {expected_kind}",
        )
    if protocol not in entry.protocols:
        raise HTTPException(
            status_code=400,
            detail=f"供应商 {provider_key} 不支持协议 {protocol}",
        )


def _default_local_model_path(provider_key: str) -> Path | None:
    svc = get_local_service(provider_key)
    if svc is None:
        return None
    models_root = dependencies.get_user_settings_store().load().models_dir.resolve()
    return svc.resolve_model_path(models_root)


def _local_model_name(provider_key: str, local_model_path: str) -> str:
    svc = get_local_service(provider_key)
    if svc is None:
        return Path(local_model_path).name if local_model_path else provider_key
    return Path(svc.model_dir_name).name


@router.get("")
def list_stage_configs() -> list[dict[str, Any]]:
    store = dependencies.get_provider_store()
    return [c.model_dump(mode="json") for c in store.load_stage_configs()]


@router.post("")
def create_stage_config(req: CreateStageConfigRequest) -> dict[str, Any]:
    entry = _provider_entry(req.provider_key)
    _validate_provider_for_stage(
        entry=entry,
        provider_key=req.provider_key,
        kind=req.kind,
        stage=req.stage,
        protocol=req.protocol,
    )
    model_name = req.model_name
    local_model_path = req.local_model_path
    if req.kind == "local":
        if not local_model_path:
            default_path = _default_local_model_path(req.provider_key)
            if default_path is not None:
                local_model_path = str(default_path)
        if not model_name:
            model_name = _local_model_name(req.provider_key, local_model_path)

    store = dependencies.get_provider_store()
    config = StageProviderConfig(
        id=str(uuid.uuid4()),
        display_name=req.display_name,
        provider_key=req.provider_key,
        kind=req.kind,
        stage=req.stage,
        protocol=req.protocol,
        account_id=req.account_id,
        model_name=model_name,
        local_model_path=local_model_path,
        device=req.device or "auto",
        precision=req.precision or "auto",
        quality_preset=req.quality_preset,
        upload_media_to_cloud=req.upload_media_to_cloud,
        extra=req.extra,
    )
    store.save_stage_config(config)
    return config.model_dump(mode="json")


@router.get("/{config_id}")
def get_stage_config(config_id: str) -> dict[str, Any]:
    store = dependencies.get_provider_store()
    config = store.get_stage_config(config_id)
    if config is None:
        raise HTTPException(status_code=404, detail="阶段配置不存在")
    return config.model_dump(mode="json")


@router.put("/{config_id}")
def update_stage_config(config_id: str, req: UpdateStageConfigRequest) -> dict[str, Any]:
    store = dependencies.get_provider_store()
    config = store.get_stage_config(config_id)
    if config is None:
        raise HTTPException(status_code=404, detail="阶段配置不存在")

    if req.display_name is not None:
        config.display_name = req.display_name
    if req.account_id is not None:
        config.account_id = req.account_id
    if req.model_name is not None:
        config.model_name = req.model_name
    if req.local_model_path is not None:
        config.local_model_path = req.local_model_path
    if req.device is not None:
        config.device = req.device
    if req.precision is not None:
        config.precision = req.precision
    if req.quality_preset is not None:
        config.quality_preset = req.quality_preset
    if req.upload_media_to_cloud is not None:
        config.upload_media_to_cloud = req.upload_media_to_cloud
    if req.extra is not None:
        config.extra = req.extra
    store.save_stage_config(config)
    return config.model_dump(mode="json")


@router.delete("/{config_id}")
def delete_stage_config(config_id: str) -> dict[str, bool]:
    store = dependencies.get_provider_store()
    store.delete_stage_config(config_id)
    return {"deleted": True}
