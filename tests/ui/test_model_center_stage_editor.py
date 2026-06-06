from __future__ import annotations


def test_model_center_shows_stage_flow_cards_with_validation_status(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)

    summary = center.stage_flow_summary()

    assert "人声分离：本地模型" in summary
    assert "语音识别：本地模型" in summary
    assert "翻译：在线 API" in summary
    assert "尚未检查" in summary


def test_model_center_stage_editor_switches_between_local_and_api_fields(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)
    center.select_config("local_fast_gpu")
    center.copy_config_button.click()
    center.open_stage_editor("translation")

    assert center.stage_local_fields.isHidden() is False
    assert center.stage_api_fields.isHidden() is True

    center.stage_service_type_combo.setCurrentText("在线 API")

    assert center.stage_local_fields.isHidden() is True
    assert center.stage_api_fields.isHidden() is False


def test_model_center_saves_stage_drawer_fields(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)
    center.select_config("local_fast_gpu")
    center.copy_config_button.click()
    custom_id = center.current_config_id()
    center.open_stage_editor("translation")
    center.stage_service_type_combo.setCurrentText("在线 API")
    center.stage_provider_edit.setText("LM Studio / Qwen3.6 35B")
    center.stage_api_base_url_edit.setText("http://127.0.0.1:1995/v1")
    center.stage_api_model_edit.setText("Qwen3.6-35B-A3B-Uncensored")
    center.save_config_button.click()

    saved = center.config_store.get(custom_id)
    translation = next(stage for stage in saved.stages if stage.stage == "translation")

    assert translation.service_type == "http"
    assert translation.provider_name == "LM Studio / Qwen3.6 35B"
    assert translation.api_base_url == "http://127.0.0.1:1995/v1"
    assert translation.api_model == "Qwen3.6-35B-A3B-Uncensored"
