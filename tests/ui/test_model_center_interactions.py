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
