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


async def test_download_local_model_uses_saved_models_dir_and_mirror(
    client,
    patch_user_models_dir: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from server.routers import local_models as local_models_router

    calls: list[dict[str, str]] = []

    def fake_snapshot_download(repo_id: str, target_dir: Path, endpoint: str) -> str:
        calls.append(
            {
                "repo_id": repo_id,
                "target_dir": str(target_dir),
                "endpoint": endpoint,
            }
        )
        target_dir.mkdir(parents=True, exist_ok=True)
        return str(target_dir)

    monkeypatch.setattr(
        local_models_router,
        "_snapshot_download_model",
        fake_snapshot_download,
        raising=False,
    )

    response = await client.post(
        "/local-models/faster-whisper-tiny/download",
        json={"source": "hf_mirror"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["repo_id"] == "Systran/faster-whisper-tiny"
    assert data["endpoint"] == "https://hf-mirror.com"
    assert data["local_dir"] == str(patch_user_models_dir / "asr" / "faster-whisper-tiny")
    assert calls == [
        {
            "repo_id": "Systran/faster-whisper-tiny",
            "target_dir": str(patch_user_models_dir / "asr" / "faster-whisper-tiny"),
            "endpoint": "https://hf-mirror.com",
        }
    ]


async def test_download_local_model_rejects_services_without_repo(
    client,
    patch_user_models_dir: Path,
) -> None:
    response = await client.post("/local-models/demucs/download", json={"source": "huggingface"})

    assert response.status_code == 400
    assert "Hugging Face" in response.json()["detail"]
