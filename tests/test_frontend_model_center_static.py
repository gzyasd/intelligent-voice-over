from __future__ import annotations

from pathlib import Path


def test_settings_page_does_not_expose_preferred_preset_id_field() -> None:
    source = Path("src/pages/Settings.vue").read_text(encoding="utf-8")

    assert "preferredPresetId" not in source
    assert "preferred_preset_id" not in source
    assert "首选预设 ID" not in source


def test_model_center_filters_stage_providers_and_autofills_local_model_fields() -> None:
    source = Path("src/pages/ModelCenter.vue").read_text(encoding="utf-8")

    assert "stageProviderOptions" in source
    assert "supportsStage(provider, stageConfigForm.stage)" in source
    assert "provider.mvp_enabled" in source
    assert "selectedLocalModel" in source
    assert "stageConfigForm.local_model_path = localModel.model_path" in source
    assert "stageConfigForm.model_name = basename(localModel.model_path)" in source
    assert ':options="deviceOptions"' in source
    assert ':options="precisionOptions"' in source


def test_model_center_supports_one_click_local_model_downloads() -> None:
    source = Path("src/pages/ModelCenter.vue").read_text(encoding="utf-8")
    api = Path("src/api/modelServices.ts").read_text(encoding="utf-8")
    store = Path("src/stores/modelServices.ts").read_text(encoding="utf-8")

    assert "modelDownloadSource" in source
    assert "https://huggingface.co" in source
    assert "https://hf-mirror.com" in source
    assert "downloadLocalModel(model)" in source
    assert "openModelPathSettings" in source
    assert "router.push('/settings')" in source
    assert "download(" in api
    assert "providerKey: string" in api
    assert "/download" in api
    assert "downloadLocalModel" in store


def test_electron_bridge_exposes_directory_picker_for_model_paths() -> None:
    preload = Path("electron/preload.ts").read_text(encoding="utf-8")
    handlers = Path("electron/ipc-handlers.ts").read_text(encoding="utf-8")
    types = Path("src/types/electron.d.ts").read_text(encoding="utf-8")

    assert "showOpenDirectoryDialog" in preload
    assert "dialog:openDirectory" in preload
    assert "dialog:openDirectory" in handlers
    assert "openDirectory" in handlers
    assert "showOpenDirectoryDialog" in types
