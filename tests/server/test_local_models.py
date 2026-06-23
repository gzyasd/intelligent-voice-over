from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def patch_user_models_dir(tmp_path: Path, monkeypatch):
    from ivo.core.user_settings import UserSettings
    from ivo.core.user_settings import UserSettingsStore
    from server import dependencies

    models_dir = tmp_path / "custom-models"
    store = UserSettingsStore(tmp_path / "settings.json", runtime_root=tmp_path / "runtime")
    store.save(
        UserSettings.with_defaults(runtime_root=tmp_path / "runtime").model_copy(
            update={"models_dir": models_dir}
        )
    )
    monkeypatch.setattr(dependencies, "get_user_settings_store", lambda: store)
    return models_dir


async def test_local_models_use_saved_models_dir(client, patch_user_models_dir: Path) -> None:
    (patch_user_models_dir / "asr" / "faster-whisper-large-v3").mkdir(parents=True)

    response = await client.get("/local-models")

    assert response.status_code == 200
    large = next(
        item for item in response.json() if item["provider_key"] == "faster-whisper-large-v3"
    )
    assert large["model_dir_exists"] is True
    assert large["model_path"] == str(
        patch_user_models_dir / "asr" / "faster-whisper-large-v3"
    )


async def test_local_models_match_resource_bundle_directory_names(
    client,
    patch_user_models_dir: Path,
) -> None:
    (patch_user_models_dir / "tts" / "F5-TTS").mkdir(parents=True)
    (patch_user_models_dir / "tts" / "Fun-CosyVoice3-0.5B").mkdir(parents=True)

    response = await client.get("/local-models")

    assert response.status_code == 200
    items = {item["provider_key"]: item for item in response.json()}
    assert items["f5-tts"]["model_dir_exists"] is True
    assert items["cosyvoice3"]["model_dir_exists"] is True


async def test_single_local_model_status_returns_only_requested_card(
    client,
    patch_user_models_dir: Path,
) -> None:
    (patch_user_models_dir / "separation" / "demucs").mkdir(parents=True)

    response = await client.get("/local-models/demucs/status")

    assert response.status_code == 200
    data = response.json()
    assert data["provider_key"] == "demucs"
    assert data["stage"] == "separation"
    assert isinstance(data["dependencies"], list)
