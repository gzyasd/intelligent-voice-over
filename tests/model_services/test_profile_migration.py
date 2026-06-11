"""Tests for profile migration utility."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ivo.model_services.profile_migration import (
    create_default_mock_scheme,
    list_importable_profiles,
    migrate_json_profile,
)
from ivo.model_services.provider_store import ProviderStore


@pytest.fixture
def tmp_store(tmp_path: Path) -> ProviderStore:
    return ProviderStore(tmp_path / ".ivo-config")


class TestMigrateJsonProfile:
    def test_migrate_translation_profile(self, tmp_path: Path, tmp_store: ProviderStore) -> None:
        profile = tmp_path / "http_translation_openai_compatible.example.json"
        profile.write_text(json.dumps({
            "base_url": "https://api.openai.com",
            "model": "gpt-4",
            "headers": {"Authorization": "Bearer {{ api_key }}"},
        }), encoding="utf-8")

        config = migrate_json_profile(profile, tmp_store)
        assert config.stage == "translation"
        assert config.model_name == "gpt-4"
        assert config.kind == "api"

        # Verify account was created
        account = tmp_store.get_account(config.id)
        assert account is not None
        assert account.api_base_url == "https://api.openai.com"

    def test_migrate_preserves_source_file(self, tmp_path: Path, tmp_store: ProviderStore) -> None:
        profile = tmp_path / "http_asr_profile.example.json"
        profile.write_text(json.dumps({"model": "whisper-1"}), encoding="utf-8")

        migrate_json_profile(profile, tmp_store, stage="asr")
        assert profile.is_file()  # Original not deleted

    def test_migrate_missing_file_raises(self, tmp_path: Path, tmp_store: ProviderStore) -> None:
        with pytest.raises(FileNotFoundError):
            migrate_json_profile(tmp_path / "nonexistent.json", tmp_store)

    def test_migrate_with_custom_display_name(
        self, tmp_path: Path, tmp_store: ProviderStore
    ) -> None:
        profile = tmp_path / "http_profile.json"
        profile.write_text(json.dumps({"model": "test"}), encoding="utf-8")

        config = migrate_json_profile(
            profile, tmp_store, display_name="Custom Name"
        )
        assert config.display_name == "Custom Name"

    def test_migrate_stores_source_profile_ref(
        self, tmp_path: Path, tmp_store: ProviderStore
    ) -> None:
        profile = tmp_path / "http_tts_profile.json"
        profile.write_text(json.dumps({"model": "tts-1"}), encoding="utf-8")

        config = migrate_json_profile(profile, tmp_store, stage="tts")
        assert "source_profile" in config.extra


class TestCreateDefaultMockScheme:
    def test_creates_when_no_schemes(self, tmp_store: ProviderStore) -> None:
        scheme = create_default_mock_scheme(tmp_store)
        assert scheme.id == "default-mock"
        assert scheme.display_name == "全自动 Mock 预览"

    def test_returns_existing_when_schemes_exist(self, tmp_store: ProviderStore) -> None:
        from ivo.model_services.provider_config import DubbingScheme

        existing = DubbingScheme(id="custom", display_name="Custom", bindings=[])
        tmp_store.save_scheme(existing)

        scheme = create_default_mock_scheme(tmp_store)
        assert scheme.id == "custom"


class TestListImportableProfiles:
    def test_finds_http_profiles(self, tmp_path: Path) -> None:
        (tmp_path / "http_translation_openai_compatible.example.json").write_text("{}", encoding="utf-8")
        (tmp_path / "http_asr_profile.example.json").write_text("{}", encoding="utf-8")
        (tmp_path / "other.json").write_text("{}", encoding="utf-8")

        results = list_importable_profiles(tmp_path)
        assert len(results) == 2

    def test_returns_empty_for_missing_dir(self, tmp_path: Path) -> None:
        results = list_importable_profiles(tmp_path / "nonexistent")
        assert results == []
