"""供应商账户管理 API"""
from __future__ import annotations
import uuid
from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .. import dependencies
from ivo.model_services.provider_config import ProviderAccount, ProviderKind

router = APIRouter()

class CreateAccountRequest(BaseModel):
    display_name: str
    provider_key: str
    kind: ProviderKind
    api_base_url: str = ""
    api_key: str | None = None
    auth_fields: dict[str, str] = {}
    extra: dict[str, object] = {}

class UpdateAccountRequest(BaseModel):
    display_name: str | None = None
    api_base_url: str | None = None
    api_key: str | None = None
    auth_fields: dict[str, str] | None = None
    extra: dict[str, object] | None = None
    enabled: bool | None = None

@router.get("")
def list_accounts() -> list[dict[str, Any]]:
    store = dependencies.get_provider_store()
    return [a.model_dump(mode="json") for a in store.load_accounts()]

@router.post("")
def create_account(req: CreateAccountRequest) -> dict[str, Any]:
    store = dependencies.get_provider_store()
    secret_store = dependencies.get_secret_store()
    account_id = str(uuid.uuid4())
    api_key_ref = None
    if req.api_key:
        api_key_ref = account_id
        secret_store.save(api_key_ref, req.api_key)
    account = ProviderAccount(
        id=account_id,
        display_name=req.display_name,
        provider_key=req.provider_key,
        kind=req.kind,
        api_base_url=req.api_base_url,
        api_key_ref=api_key_ref,
        auth_fields=req.auth_fields,
        extra=req.extra,
    )
    store.save_account(account)
    return account.model_dump(mode="json")

@router.get("/{account_id}")
def get_account(account_id: str) -> dict[str, Any]:
    store = dependencies.get_provider_store()
    account = store.get_account(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="账户不存在")
    return account.model_dump(mode="json")

@router.put("/{account_id}")
def update_account(account_id: str, req: UpdateAccountRequest) -> dict[str, Any]:
    store = dependencies.get_provider_store()
    secret_store = dependencies.get_secret_store()
    account = store.get_account(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="账户不存在")
    if req.display_name is not None:
        account.display_name = req.display_name
    if req.api_base_url is not None:
        account.api_base_url = req.api_base_url
    if req.auth_fields is not None:
        account.auth_fields = req.auth_fields
    if req.extra is not None:
        account.extra = req.extra
    if req.enabled is not None:
        account.enabled = req.enabled
    if req.api_key is not None:
        ref = account.api_key_ref or account_id
        secret_store.save(ref, req.api_key)
        account.api_key_ref = ref
    store.save_account(account)
    return account.model_dump(mode="json")

@router.delete("/{account_id}")
def delete_account(account_id: str) -> dict[str, Any]:
    store = dependencies.get_provider_store()
    account = store.get_account(account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="账户不存在")
    if account.api_key_ref:
        secret_store = dependencies.get_secret_store()
        secret_store.delete(account.api_key_ref)
    store.delete_account(account_id)
    return {"deleted": True}
