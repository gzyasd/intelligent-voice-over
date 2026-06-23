"""供应商注册表 API（只读）"""
from __future__ import annotations
from typing import Any
from fastapi import APIRouter, HTTPException
from .. import dependencies
from ivo.model_services.provider_registry import ConfigField, ProviderRegistryEntry

router = APIRouter()

@router.get("")
def list_providers() -> list[dict[str, Any]]:
    """列出所有供应商"""
    registry = dependencies.get_provider_registry()
    return [_entry_to_dict(e) for e in registry.list_all()]

@router.get("/stage/{stage}")
def list_providers_by_stage(stage: str) -> list[dict[str, Any]]:
    """按阶段筛选供应商"""
    registry = dependencies.get_provider_registry()
    return [_entry_to_dict(e) for e in registry.list_for_stage(stage)]

@router.get("/{provider_id}")
def get_provider(provider_id: str) -> dict[str, Any]:
    """获取供应商详情"""
    registry = dependencies.get_provider_registry()
    entry = registry.get(provider_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"供应商不存在: {provider_id}")
    return _entry_to_dict(entry)

def _entry_to_dict(entry: ProviderRegistryEntry) -> dict[str, Any]:
    """将 ProviderRegistryEntry dataclass 转为 dict"""
    return {
        "provider_id": entry.provider_id,
        "display_name": entry.display_name,
        "supported_stages": list(entry.supported_stages),
        "protocols": list(entry.protocols),
        "capabilities": sorted(entry.capabilities),
        "requires_api_key": entry.requires_api_key,
        "requires_base_url": entry.requires_base_url,
        "default_base_url": entry.default_base_url,
        "config_fields": [_field_to_dict(f) for f in entry.config_fields],
        "stage_config_fields": {
            stage: [_field_to_dict(f) for f in fields]
            for stage, fields in (entry.stage_config_fields or {}).items()
        },
        "implemented": entry.implemented,
        "mvp_enabled": entry.mvp_enabled,
        "scenario": entry.scenario,
        "external_docs_url": entry.external_docs_url,
    }

def _field_to_dict(field: ConfigField) -> dict[str, Any]:
    return {
        "name": field.name,
        "display_name": field.display_name,
        "field_type": field.field_type,
        "required": field.required,
        "default": field.default,
        "placeholder": field.placeholder,
        "options": list(field.options) if field.options else None,
        "validation_pattern": field.validation_pattern,
    }
