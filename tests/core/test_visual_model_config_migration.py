from __future__ import annotations


def test_visual_model_config_loads_legacy_custom_config_without_visual_fields(tmp_path) -> None:
    from ivo.core.visual_model_config import VisualModelConfigStore

    config_path = tmp_path / "model-configs.json"
    config_path.write_text(
        """
        {
          "configs": [
            {
              "id": "custom-legacy",
              "display_name": "旧配置",
              "description": "旧版本保存的配置",
              "local_profiles_path": "examples/local_command_profiles.real_gpu_fast_preview.json",
              "translation_profile_path": "",
              "builtin": false,
              "recommended_models": [],
              "stages": [
                {
                  "stage": "asr",
                  "label": "语音识别",
                  "service_type": "local",
                  "provider_name": "faster-whisper",
                  "enabled": true
                }
              ]
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    config = VisualModelConfigStore(config_path).get("custom-legacy")
    stage = config.stages[0]

    assert config.quality_label == "自定义"
    assert config.prefer_gpu is True
    assert config.content_types == ["通用"]
    assert config.last_check_status == "unchecked"
    assert stage.device == "auto"
    assert stage.precision == "auto"
    assert stage.validation_status == "unchecked"


def test_builtin_visual_configs_include_tags_quality_and_validation_defaults(tmp_path) -> None:
    from ivo.core.visual_model_config import VisualModelConfigStore

    config = VisualModelConfigStore(tmp_path / "model-configs.json").get(
        "local_quality_lmstudio_qwen_f5"
    )
    stages = {stage.stage: stage for stage in config.stages}

    assert config.quality_label == "高质量"
    assert config.prefer_gpu is True
    assert "GPU" in config.tags
    assert "LM Studio" in config.tags
    assert config.last_check_status == "unchecked"
    assert stages["translation"].api_base_url == "http://127.0.0.1:1995/v1"
    assert stages["translation"].api_model == "Qwen3.6-35B-A3B"
