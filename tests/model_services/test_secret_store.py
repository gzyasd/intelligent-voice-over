"""Tests for model_services secret store (encrypted key storage)."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture()
def store_dir(tmp_path: Path) -> Path:
    return tmp_path / "model-services"


def test_secret_store_encrypts_and_decrypts(store_dir: Path) -> None:
    from ivo.model_services.secret_store import SecretStore

    store = SecretStore(store_dir)
    secret_id = "secret-openai-1"
    api_key = "sk-test-key-12345"

    store.save(secret_id, api_key)
    retrieved = store.load(secret_id)

    assert retrieved == api_key


def test_secret_store_does_not_save_plaintext(store_dir: Path) -> None:
    from ivo.model_services.secret_store import SecretStore

    store = SecretStore(store_dir)
    secret_id = "secret-openai-1"
    api_key = "sk-test-key-12345"

    store.save(secret_id, api_key)

    # Read the raw file - should not contain the plaintext key
    secrets_file = store_dir / "provider-secrets.json"
    raw_text = secrets_file.read_text(encoding="utf-8")
    assert api_key not in raw_text


def test_secret_store_delete(store_dir: Path) -> None:
    from ivo.model_services.secret_store import SecretStore

    store = SecretStore(store_dir)
    store.save("s1", "key1")
    store.delete("s1")

    assert store.load("s1") is None


def test_secret_store_load_missing_returns_none(store_dir: Path) -> None:
    from ivo.model_services.secret_store import SecretStore

    store = SecretStore(store_dir)
    assert store.load("nonexistent") is None


def test_secret_store_list_ids(store_dir: Path) -> None:
    from ivo.model_services.secret_store import SecretStore

    store = SecretStore(store_dir)
    store.save("s1", "key1")
    store.save("s2", "key2")

    ids = store.list_ids()
    assert set(ids) == {"s1", "s2"}


def test_secret_store_reports_protection_level(store_dir: Path) -> None:
    from ivo.model_services.secret_store import SecretStore

    store = SecretStore(store_dir)
    level = store.protection_level
    # Should be one of: "dpapi", "keyring", "portable_fallback"
    assert level in ("dpapi", "keyring", "portable_fallback")
