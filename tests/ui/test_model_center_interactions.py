from __future__ import annotations


def test_model_center_browse_model_dir_syncs_advanced_settings(
    monkeypatch,
    qtbot,
    tmp_path,
) -> None:
    from ivo.ui.model_center import ModelCenter

    models_dir = tmp_path / "models"
    models_dir.mkdir()
    monkeypatch.setattr(
        "ivo.ui.model_center.QFileDialog.getExistingDirectory",
        lambda *args, **kwargs: str(models_dir),
    )
    center = ModelCenter()
    qtbot.addWidget(center)

    center.model_dir_button.click()

    assert center.model_dir_edit.text() == str(models_dir)
    assert center.advanced_settings.local_model_path_edit.text() == str(models_dir)


def test_model_center_preset_selection_updates_advanced_profile_paths(qtbot) -> None:
    from ivo.core.model_presets import get_model_preset
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter()
    qtbot.addWidget(center)
    preset = get_model_preset("local_fast_gpu")

    center.select_preset("local_fast_gpu")

    assert center.advanced_settings.local_command_profiles_path_edit.text() == preset.local_profiles_path
    assert center.advanced_settings.translation_profile_path_edit.text() == preset.translation_profile_path


def test_model_center_preset_card_click_selects_preset(qtbot) -> None:
    from ivo.core.model_presets import get_model_preset
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter()
    qtbot.addWidget(center)
    preset = get_model_preset("local_cpu_preview")

    center.preset_buttons["local_cpu_preview"].click()

    assert center.selected_preset_id() == "local_cpu_preview"
    assert center.selected_preset_label.text() == f"当前方案：{preset.display_name}"
    assert center.advanced_settings.local_command_profiles_path_edit.text() == preset.local_profiles_path
    assert "需要模型" in center.selected_preset_detail_label.text()


def test_model_center_apply_current_preset_emits_signal_and_status(qtbot) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter()
    qtbot.addWidget(center)
    emitted: list[str] = []
    center.preset_applied.connect(emitted.append)

    center.select_preset("local_quality_lmstudio_qwen_f5")
    center.apply_preset_button.click()

    assert emitted == ["local_quality_lmstudio_qwen_f5"]
    assert center.status_label.text() == "已应用方案：本机高质量（LM Studio + F5-TTS）"


def test_model_center_copies_edits_and_applies_visual_config(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)
    emitted: list[str] = []
    center.preset_applied.connect(emitted.append)

    center.select_config("local_fast_gpu")
    center.copy_config_button.click()
    custom_id = center.current_config_id()
    center.config_name_edit.setText("我的 GPU 预览配置")
    center.config_description_edit.setText("先快速看效果")
    center.config_local_profiles_path_edit.setText(
        "examples/local_command_profiles.real_gpu_fast_preview.json"
    )
    center.save_config_button.click()
    center.apply_preset_button.click()

    assert custom_id.startswith("custom-")
    assert emitted == [custom_id]
    assert center.current_config_display_name() == "我的 GPU 预览配置"
    assert center.advanced_settings.local_command_profiles_path_edit.text().endswith(
        "real_gpu_fast_preview.json"
    )


def test_model_center_saves_stage_visual_settings(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)

    center.select_config("local_quality_lmstudio_qwen_f5")
    center.copy_config_button.click()
    custom_id = center.current_config_id()
    center.stage_enabled_checks["diarization"].setChecked(False)
    center.stage_service_combos["translation"].setCurrentText("在线 API")
    center.stage_provider_edits["translation"].setText("LM Studio / Qwen3.6 35B")
    center.save_config_button.click()

    saved = center.config_store.get(custom_id)
    stages = {stage.stage: stage for stage in saved.stages}
    assert stages["diarization"].enabled is False
    assert stages["translation"].service_type == "http"
    assert stages["translation"].provider_name == "LM Studio / Qwen3.6 35B"
    assert "翻译：在线 API" in center.selected_preset_detail_label.text()


def test_model_center_deletes_custom_visual_config(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)

    center.select_config("local_cpu_preview")
    center.copy_config_button.click()
    custom_id = center.current_config_id()
    center.delete_config_button.click()

    assert custom_id not in center.config_ids()
    assert center.current_config_id() == "local_quality_lmstudio_qwen_f5"


def test_model_center_check_models_runs_diagnostics_and_readiness(monkeypatch, qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    calls: list[str] = []
    center = ModelCenter()
    qtbot.addWidget(center)
    center.model_dir_edit.setText(str(tmp_path / "models"))
    monkeypatch.setattr(center.advanced_settings, "refresh_model_diagnostics", lambda: calls.append("diagnostics"))
    monkeypatch.setattr(center.advanced_settings, "check_local_readiness", lambda: calls.append("readiness"))

    center.check_models_button.click()

    assert center.advanced_settings.local_model_path_edit.text() == str(tmp_path / "models")
    assert calls == ["diagnostics", "readiness"]


def test_model_center_developer_toggle_shows_feedback(qtbot) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter()
    qtbot.addWidget(center)

    center.toggle_advanced_button.click()

    assert center.advanced_settings_visible() is True
    assert center.toggle_advanced_button.text() == "隐藏开发者设置"
    assert center.developer_settings_hint_label.text() == "开发者设置已展开，可在下方配置本地命令和在线 API。"


def test_main_window_does_not_reparent_model_center_advanced_settings(qtbot) -> None:
    from ivo.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    window.model_center.toggle_advanced_button.click()

    assert window.model_center.advanced_settings_visible() is True
    assert window.model_settings.parent() is window.model_center.advanced_container
    assert window.model_center.advanced_container.layout().itemAt(0).widget() is window.model_settings
    assert window.model_settings.local_model_path_edit.text()


def test_main_window_saves_applied_model_preset(qtbot, tmp_path) -> None:
    from ivo.core.user_settings import UserSettingsStore
    from ivo.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.settings_page.store = UserSettingsStore(
        tmp_path / ".ivo-work" / "user-settings.json",
        runtime_root=tmp_path,
    )

    window.model_center.select_preset("local_fast_gpu")
    window.model_center.apply_preset_button.click()

    assert window.settings_page.store.load().preferred_preset_id == "local_fast_gpu"
    assert window.progress_label.text() == "模型方案已保存：本机快速预览（GPU）"


def test_main_window_saves_applied_custom_model_config(qtbot, tmp_path) -> None:
    from ivo.core.user_settings import UserSettingsStore
    from ivo.core.visual_model_config import VisualModelConfigStore
    from ivo.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    window.settings_page.store = UserSettingsStore(
        tmp_path / ".ivo-work" / "user-settings.json",
        runtime_root=tmp_path,
    )
    window.model_center.config_store = VisualModelConfigStore(tmp_path / "model-configs.json")
    window.model_center.refresh_config_list()

    window.model_center.select_config("local_fast_gpu")
    window.model_center.copy_config_button.click()
    custom_id = window.model_center.current_config_id()
    window.model_center.config_name_edit.setText("我的正式生成配置")
    window.model_center.save_config_button.click()
    window.model_center.apply_preset_button.click()

    assert window.settings_page.store.load().preferred_preset_id == custom_id
    assert window.progress_label.text() == "模型方案已保存：我的正式生成配置"
