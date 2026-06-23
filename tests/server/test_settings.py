"""用户设置 API 测试"""

from __future__ import annotations

from pathlib import Path
import importlib

import pytest


@pytest.fixture
def patch_settings(tmp_path: Path, monkeypatch):
    from server import dependencies
    from ivo.core.user_settings import UserSettingsStore

    store = UserSettingsStore(tmp_path / "settings.json", runtime_root=tmp_path)
    monkeypatch.setattr(dependencies, "get_user_settings_store", lambda: store)
    return store


async def test_get_settings(client, patch_settings):
    response = await client.get("/settings")
    assert response.status_code == 200
    data = response.json()
    assert "models_dir" in data
    assert "projects_dir" in data
    assert "theme" in data


async def test_update_settings(client, patch_settings):
    response = await client.put("/settings", json={"theme": "dark", "prefer_gpu": False})
    assert response.status_code == 200
    data = response.json()
    assert data["theme"] == "dark"
    assert data["prefer_gpu"] is False


async def test_update_settings_persists_preferred_preset_id(client, patch_settings):
    response = await client.put(
        "/settings",
        json={"preferred_preset_id": "local_fast_gpu"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["preferred_preset_id"] == "local_fast_gpu"
    assert patch_settings.load().preferred_preset_id == "local_fast_gpu"


def test_dependencies_use_user_data_dir_for_persistent_settings(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import server.dependencies as dependencies

    user_data_dir = tmp_path / "IVO"
    monkeypatch.setenv("IVO_USER_DATA_DIR", str(user_data_dir))
    reloaded = importlib.reload(dependencies)
    try:
        store = reloaded.get_user_settings_store()

        assert store.path == user_data_dir / ".ivo-work" / "user-settings.json"
        assert store.runtime_root == user_data_dir.resolve()
        assert reloaded.get_config_dir() == user_data_dir / ".ivo-work" / "config"
    finally:
        monkeypatch.delenv("IVO_USER_DATA_DIR", raising=False)
        importlib.reload(reloaded)


async def test_get_recent_projects(client, patch_settings):
    response = await client.get("/settings/recent-projects")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
