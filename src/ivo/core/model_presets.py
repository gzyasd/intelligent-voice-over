from __future__ import annotations

from pydantic import BaseModel, Field


class ModelPreset(BaseModel):
    id: str
    display_name: str
    description: str
    quality: str
    local_profiles_path: str
    translation_profile_path: str = ""
    requires_lm_studio: bool = False
    requires_gpu: bool = False
    recommended_models: list[str] = Field(default_factory=list)


def builtin_model_presets() -> list[ModelPreset]:
    return [
        ModelPreset(
            id="local_quality_lmstudio_qwen_f5",
            display_name="本机高质量（LM Studio + F5-TTS）",
            description="适合正式生成：本地分离、识别、说话人识别、F5-TTS，翻译使用 LM Studio。",
            quality="high",
            local_profiles_path="examples/local_command_profiles.real_full_gpu_f5_diarization.json",
            translation_profile_path=(
                "examples/http_translation_lm_studio_qwen36_35b.example.json"
            ),
            requires_lm_studio=True,
            requires_gpu=True,
            recommended_models=[
                "Systran/faster-whisper-large-v3",
                "pyannote/speaker-diarization-community-1",
                "SWivid/F5-TTS",
                "Qwen3.6-35B-A3B via LM Studio",
            ],
        ),
        ModelPreset(
            id="local_fast_gpu",
            display_name="本机快速预览（GPU）",
            description="适合先看效果：速度优先，使用较轻的本地 GPU 配置。",
            quality="fast",
            local_profiles_path="examples/local_command_profiles.real_gpu_fast_preview.json",
            requires_gpu=True,
        ),
        ModelPreset(
            id="local_cpu_preview",
            display_name="CPU 快速预览",
            description="没有 NVIDIA GPU 时使用，速度较慢但配置简单。",
            quality="preview",
            local_profiles_path="examples/local_command_profiles.real_separation_asr_tts_f5_cpu_small.json",
        ),
        ModelPreset(
            id="online_custom",
            display_name="自定义在线 API",
            description="每个阶段可以接入自己的在线模型服务。",
            quality="custom",
            local_profiles_path="examples/local_command_profiles.real_dry_run.json",
        ),
    ]


def get_model_preset(preset_id: str) -> ModelPreset:
    for preset in builtin_model_presets():
        if preset.id == preset_id:
            return preset
    raise KeyError(preset_id)
