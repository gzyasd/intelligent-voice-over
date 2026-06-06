from __future__ import annotations


def test_visual_model_config_store_lists_builtins_and_persists_custom_copy(tmp_path) -> None:
    from ivo.core.visual_model_config import VisualModelConfigStore

    store = VisualModelConfigStore(tmp_path / "model-configs.json")

    config = store.copy_config(
        "local_fast_gpu",
        display_name="我的快速 GPU 配置",
        description="给短视频预览使用",
    )
    reloaded = VisualModelConfigStore(tmp_path / "model-configs.json")

    assert config.id.startswith("custom-")
    assert config.builtin is False
    assert config.display_name == "我的快速 GPU 配置"
    assert reloaded.get(config.id).description == "给短视频预览使用"
    assert reloaded.get("local_fast_gpu").builtin is True


def test_visual_model_config_store_updates_and_deletes_custom_config(tmp_path) -> None:
    from ivo.core.visual_model_config import VisualModelConfigStore

    store = VisualModelConfigStore(tmp_path / "model-configs.json")
    config = store.create_blank_config(display_name="空白配置")
    updated = config.model_copy(
        update={
            "description": "使用本地模型和 LM Studio",
            "local_profiles_path": "examples/local_command_profiles.real_gpu_fast_preview.json",
        }
    )

    store.save_custom(updated)
    assert store.get(config.id).local_profiles_path.endswith("real_gpu_fast_preview.json")

    store.delete_custom(config.id)
    assert config.id not in [item.id for item in store.list_all()]
