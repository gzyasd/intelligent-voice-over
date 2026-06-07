from __future__ import annotations

from pathlib import Path


def test_model_center_scan_models_populates_stage_model_choices(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    models_dir = tmp_path / "models"
    (models_dir / "tts" / "F5-TTS").mkdir(parents=True)
    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)
    center.model_dir_edit.setText(str(models_dir))
    center.select_config("local_fast_gpu")
    center.copy_config_button.click()

    center.refresh_model_candidates()
    center.open_stage_editor("tts")

    assert "F5-TTS" in center.stage_model_choice_summary()
    assert center.stage_model_combo.count() >= 1


def test_model_center_loads_lm_studio_models_into_api_selector(monkeypatch, qtbot, tmp_path) -> None:
    from ivo.ui import model_center as model_center_module
    from ivo.ui.model_center import ModelCenter

    monkeypatch.setattr(
        model_center_module,
        "fetch_lm_studio_models",
        lambda _base_url: ["Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_P"],
    )
    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)
    center.select_config("local_quality_lmstudio_qwen_f5")
    center.open_stage_editor("translation")

    center.load_lm_studio_models()

    assert center.stage_api_model_combo.count() == 1
    assert center.stage_api_model_combo.currentText() == (
        "Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_P"
    )
    assert "已读取 LM Studio 模型" in center.status_label.text()


def test_model_center_single_stage_validation_uses_current_stage_fields(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    models_dir = tmp_path / "models"
    (models_dir / "tts" / "F5-TTS").mkdir(parents=True)
    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)
    center.model_dir_edit.setText(str(models_dir))
    center.select_config("local_fast_gpu")
    center.copy_config_button.click()
    center.open_stage_editor("tts")
    center.stage_model_path_edit.setText("tts/F5-TTS")

    center.test_current_stage()

    assert "语音合成：可用" in center.validation_summary_text()
    assert "F5-TTS" in center.validation_summary_text()


def test_model_center_marks_unsaved_changes_when_stage_form_changes(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)
    center.select_config("local_fast_gpu")
    center.copy_config_button.click()
    center.open_stage_editor("translation")

    center.stage_api_model_edit.setText("Qwen3.6-35B-A3B-Uncensored")

    assert center.has_unsaved_changes() is True
    assert "未保存" in center.status_label.text()
    assert "未保存" in center.save_apply_button.text()


def test_model_center_exports_and_imports_visual_config(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)
    center.select_config("local_fast_gpu")
    center.copy_config_button.click()
    center.config_name_edit.setText("可迁移配置")
    saved = center.save_current_config()
    assert saved is not None

    export_path = tmp_path / "exported-config.json"
    center.export_current_config(export_path)

    imported_center = ModelCenter(config_store_path=tmp_path / "imported-model-configs.json")
    qtbot.addWidget(imported_center)
    imported = imported_center.import_config(export_path)

    assert imported.display_name == "可迁移配置"
    assert imported.id.startswith("custom-")
    assert imported.id in imported_center.config_ids()


def test_model_center_import_rejects_missing_file(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)

    missing_path = Path(tmp_path / "missing.json")
    imported = center.import_config(missing_path)

    assert imported is None
    assert "没有找到配置文件" in center.status_label.text()
