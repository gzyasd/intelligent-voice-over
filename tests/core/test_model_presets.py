from __future__ import annotations


def test_builtin_model_presets_include_recommended_local_quality() -> None:
    from ivo.core.model_presets import builtin_model_presets, get_model_preset

    presets = builtin_model_presets()
    preset_ids = [preset.id for preset in presets]

    assert "local_quality_lmstudio_qwen_f5" in preset_ids
    quality = get_model_preset("local_quality_lmstudio_qwen_f5")
    assert quality.display_name == "本机高质量（LM Studio + F5-TTS）"
    assert quality.requires_gpu is True
    assert quality.requires_lm_studio is True
    assert quality.local_profiles_path.endswith("local_command_profiles.real_full_gpu_f5_diarization.json")
    assert quality.translation_profile_path.endswith(
        "http_translation_lm_studio_qwen36_35b.example.json"
    )


def test_builtin_model_presets_offer_fast_and_cpu_options() -> None:
    from ivo.core.model_presets import builtin_model_presets

    names = [preset.display_name for preset in builtin_model_presets()]

    assert "本机快速预览（GPU）" in names
    assert "CPU 快速预览" in names
    assert "自定义在线 API" in names
