from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def patch_stage_config_dependencies(tmp_path: Path, monkeypatch):
    from ivo.core.user_settings import UserSettings
    from ivo.core.user_settings import UserSettingsStore
    from ivo.model_services.provider_store import ProviderStore
    from server import dependencies

    models_dir = tmp_path / "models"
    settings_store = UserSettingsStore(tmp_path / "settings.json", runtime_root=tmp_path)
    settings_store.save(
        UserSettings.with_defaults(runtime_root=tmp_path).model_copy(
            update={"models_dir": models_dir}
        )
    )
    provider_store = ProviderStore(tmp_path / "config")
    monkeypatch.setattr(dependencies, "get_user_settings_store", lambda: settings_store)
    monkeypatch.setattr(dependencies, "get_provider_store", lambda: provider_store)
    return models_dir


async def test_create_stage_config_rejects_provider_that_does_not_support_stage(
    client,
    patch_stage_config_dependencies: Path,
) -> None:
    response = await client.post(
        "/stage-configs",
        json={
            "display_name": "OpenAI Translation",
            "provider_key": "openai",
            "kind": "api",
            "stage": "translation",
            "protocol": "openai_asr",
        },
    )

    assert response.status_code == 400
    assert "不支持阶段" in response.json()["detail"]


async def test_create_local_stage_config_defaults_to_saved_model_dir(
    client,
    patch_stage_config_dependencies: Path,
) -> None:
    response = await client.post(
        "/stage-configs",
        json={
            "display_name": "Demucs Local",
            "provider_key": "demucs",
            "kind": "local",
            "stage": "separation",
            "protocol": "local_demucs",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["model_name"] == "demucs"
    assert data["local_model_path"] == str(patch_stage_config_dependencies / "separation" / "demucs")
    assert data["device"] == "auto"
    assert data["precision"] == "auto"


async def test_create_stage_config_rejects_protocol_not_supported_by_provider(
    client,
    patch_stage_config_dependencies: Path,
) -> None:
    response = await client.post(
        "/stage-configs",
        json={
            "display_name": "Bad Protocol",
            "provider_key": "demucs",
            "kind": "local",
            "stage": "separation",
            "protocol": "openai_tts",
        },
    )

    assert response.status_code == 400
    assert "协议" in response.json()["detail"]
