"""配音方案管理 API"""
from __future__ import annotations
import uuid
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .. import dependencies
from ivo.model_services.provider_config import DubbingScheme, SchemeStageBinding
from ivo.model_services.stages import StageName

router = APIRouter()

class BindingRequest(BaseModel):
    stage: StageName
    stage_config_id: str
    execution_group: str | None = None
    skip_when_execution_group_has_output: bool = False

class CreateSchemeRequest(BaseModel):
    display_name: str
    description: str = ""
    bindings: list[BindingRequest]
    prefer_gpu: bool = True
    content_types: list[str] = ["通用"]

class UpdateSchemeRequest(BaseModel):
    display_name: str | None = None
    description: str | None = None
    bindings: list[BindingRequest] | None = None
    prefer_gpu: bool | None = None
    content_types: list[str] | None = None

class SetDefaultSchemeRequest(BaseModel):
    scheme_id: str

@router.get("")
def list_schemes() -> list[dict[str, Any]]:
    store = dependencies.get_provider_store()
    return [s.model_dump(mode="json") for s in store.load_schemes()]

@router.post("")
def create_scheme(req: CreateSchemeRequest) -> dict[str, Any]:
    store = dependencies.get_provider_store()
    scheme_id = str(uuid.uuid4())
    scheme = DubbingScheme(
        id=scheme_id,
        display_name=req.display_name,
        description=req.description,
        bindings=[
            SchemeStageBinding(
                stage=b.stage,
                stage_config_id=b.stage_config_id,
                execution_group=b.execution_group,
                skip_when_execution_group_has_output=b.skip_when_execution_group_has_output,
            )
            for b in req.bindings
        ],
        prefer_gpu=req.prefer_gpu,
        content_types=req.content_types,
    )
    store.save_scheme(scheme)
    return scheme.model_dump(mode="json")

@router.get("/default-scheme")
def get_default_scheme() -> dict[str, Any]:
    store = dependencies.get_provider_store()
    scheme_id = store.load_default_scheme_id()
    if scheme_id is None:
        return {"scheme_id": None}
    return {"scheme_id": scheme_id}

@router.put("/default-scheme")
def set_default_scheme(req: SetDefaultSchemeRequest) -> dict[str, Any]:
    store = dependencies.get_provider_store()
    scheme = store.get_scheme(req.scheme_id)
    if scheme is None:
        raise HTTPException(status_code=404, detail="方案不存在")
    store.save_default_scheme_id(req.scheme_id)
    return {"scheme_id": req.scheme_id}

@router.get("/{scheme_id}")
def get_scheme(scheme_id: str) -> dict[str, Any]:
    store = dependencies.get_provider_store()
    scheme = store.get_scheme(scheme_id)
    if scheme is None:
        raise HTTPException(status_code=404, detail="方案不存在")
    return scheme.model_dump(mode="json")

@router.put("/{scheme_id}")
def update_scheme(scheme_id: str, req: UpdateSchemeRequest) -> dict[str, Any]:
    store = dependencies.get_provider_store()
    scheme = store.get_scheme(scheme_id)
    if scheme is None:
        raise HTTPException(status_code=404, detail="方案不存在")
    if req.display_name is not None:
        scheme.display_name = req.display_name
    if req.description is not None:
        scheme.description = req.description
    if req.bindings is not None:
        scheme.bindings = [
            SchemeStageBinding(
                stage=b.stage,
                stage_config_id=b.stage_config_id,
                execution_group=b.execution_group,
                skip_when_execution_group_has_output=b.skip_when_execution_group_has_output,
            )
            for b in req.bindings
        ]
    if req.prefer_gpu is not None:
        scheme.prefer_gpu = req.prefer_gpu
    if req.content_types is not None:
        scheme.content_types = req.content_types
    store.save_scheme(scheme)
    return scheme.model_dump(mode="json")

@router.delete("/{scheme_id}")
def delete_scheme(scheme_id: str) -> dict[str, Any]:
    store = dependencies.get_provider_store()
    store.delete_scheme(scheme_id)
    return {"deleted": True}
