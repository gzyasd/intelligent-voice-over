from __future__ import annotations


def test_model_center_uses_unified_config_library_and_detail_panel(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)

    assert center.config_library_title.text() == "配置库"
    assert center.config_detail_title.text() == "本机高质量（LM Studio + F5-TTS）"
    assert "已应用" in center.current_config_status_label.text()
    assert "推荐方案" in center.config_library_summary()
    assert "我的配置" in center.config_library_summary()
    assert center.apply_preset_button.text() == "应用此配置"


def test_model_center_new_config_opens_visual_editor_drawer(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)

    center.new_config_button.click()

    assert center.editor_drawer.isHidden() is False
    assert center.editor_tabs.tabText(0) == "基础信息"
    assert center.editor_tabs.tabText(1) == "阶段设置"
    assert center.editor_tabs.tabText(2) == "高级源文件"
    assert center.current_config_id().startswith("custom-")


def test_model_center_edit_builtin_copies_to_custom_config(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)

    center.select_config("local_fast_gpu")
    center.edit_config_button.click()

    assert center.current_config_id().startswith("custom-")
    assert center.editor_drawer.isHidden() is False
    assert "已复制推荐方案" in center.status_label.text()


def test_model_center_deletes_only_custom_config_from_detail_actions(qtbot, tmp_path) -> None:
    from ivo.ui.model_center import ModelCenter

    center = ModelCenter(config_store_path=tmp_path / "model-configs.json")
    qtbot.addWidget(center)
    center.select_config("local_cpu_preview")
    center.copy_config_button.click()
    custom_id = center.current_config_id()

    center.delete_config_button.click()

    assert custom_id not in center.config_ids()
    assert center.current_config_id() == "local_quality_lmstudio_qwen_f5"
