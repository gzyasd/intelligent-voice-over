from __future__ import annotations

from pathlib import Path


def test_user_settings_defaults_use_runtime_root(tmp_path: Path) -> None:
    from ivo.core.user_settings import UserSettings

    settings = UserSettings.with_defaults(runtime_root=tmp_path)

    assert settings.models_dir == tmp_path / "models"
    assert settings.projects_dir == tmp_path / "runs"
    assert settings.prefer_gpu is True
    assert settings.lm_studio_base_url == "http://127.0.0.1:1995/v1"
    assert settings.preferred_preset_id == "local_quality_lmstudio_qwen_f5"


def test_user_settings_store_round_trips_and_tracks_recent_projects(tmp_path: Path) -> None:
    from ivo.core.user_settings import UserSettingsStore

    store = UserSettingsStore(tmp_path / ".ivo-work" / "user-settings.json", runtime_root=tmp_path)
    first = tmp_path / "runs" / "Episode 01.ivoproj"
    second = tmp_path / "runs" / "Episode 02.ivoproj"

    store.add_recent_project(first)
    store.add_recent_project(second)
    store.add_recent_project(first)
    loaded = store.load()

    assert loaded.recent_projects == [first, second]
    assert loaded.models_dir == tmp_path / "models"
