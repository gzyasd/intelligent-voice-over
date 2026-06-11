"""Tests for model_services provider store (JSON-based persistence)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ivo.model_services.provider_config import (
    ProviderAccount,
    StageProviderConfig,
)


@pytest.fixture()
def store_dir(tmp_path: Path) -> Path:
    return tmp_path / "model-services"


def _make_account() -> ProviderAccount:
    return ProviderAccount(
        id="acct-openai",
        display_name="OpenAI",
        provider_key="openai",
        kind="api",
        api_key_ref="secret-openai-1",
    )


def _make_config() -> StageProviderConfig:
    return StageProviderConfig(
        id="stage-openai-asr",
        display_name="OpenAI ASR",
        account_id="acct-openai",
        provider_key="openai",
        kind="api",
        stage="asr",
        protocol="openai_asr",
        model_name="gpt-4o-transcribe",
    )


def test_provider_store_saves_account_without_api_key(store_dir: Path) -> None:
    from ivo.model_services.provider_store import ProviderStore

    store = ProviderStore(store_dir)
    account = _make_account()
    store.save_account(account)

    # Read the JSON file and verify no plaintext key
    accounts_file = store_dir / "provider-accounts.json"
    raw_text = accounts_file.read_text(encoding="utf-8")

    # The file should contain the account data but NOT any actual API key value
    assert "acct-openai" in raw_text
    assert "secret-openai-1" in raw_text  # ref is OK
    assert "sk-" not in raw_text  # no actual key


def test_provider_store_loads_accounts(store_dir: Path) -> None:
    from ivo.model_services.provider_store import ProviderStore

    store = ProviderStore(store_dir)
    account = _make_account()
    store.save_account(account)

    loaded = store.load_accounts()
    assert len(loaded) == 1
    assert loaded[0].id == "acct-openai"


def test_provider_store_saves_stage_configs(store_dir: Path) -> None:
    from ivo.model_services.provider_store import ProviderStore

    store = ProviderStore(store_dir)
    config = _make_config()
    store.save_stage_config(config)

    loaded = store.load_stage_configs()
    assert len(loaded) == 1
    assert loaded[0].id == "stage-openai-asr"
    assert loaded[0].protocol == "openai_asr"


def test_provider_store_export_excludes_secrets(store_dir: Path) -> None:
    from ivo.model_services.provider_store import ProviderStore

    store = ProviderStore(store_dir)
    account = _make_account()
    config = _make_config()
    store.save_account(account)
    store.save_stage_config(config)

    exported = store.export_config()
    exported_text = json.dumps(exported, ensure_ascii=False)

    # Exported config should have accounts and stage_configs
    assert "accounts" in exported
    assert "stage_configs" in exported

    # But should NOT contain api_key_ref values (user must re-enter)
    assert "secret-openai-1" not in exported_text


def test_provider_store_delete_account(store_dir: Path) -> None:
    from ivo.model_services.provider_store import ProviderStore

    store = ProviderStore(store_dir)
    store.save_account(_make_account())
    store.delete_account("acct-openai")

    loaded = store.load_accounts()
    assert len(loaded) == 0


def test_provider_store_get_account(store_dir: Path) -> None:
    from ivo.model_services.provider_store import ProviderStore

    store = ProviderStore(store_dir)
    store.save_account(_make_account())

    found = store.get_account("acct-openai")
    assert found is not None
    assert found.provider_key == "openai"

    not_found = store.get_account("nonexistent")
    assert not_found is None
