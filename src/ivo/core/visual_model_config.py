from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from ivo.core.model_presets import ModelPreset, builtin_model_presets


STAGE_LABELS: dict[str, str] = {
    "separation": "人声分离",
    "asr": "语音识别",
    "diarization": "说话人识别",
    "translation": "翻译",
    "tts": "语音合成",
}


class VisualStageConfig(BaseModel):
    stage: str
    label: str
    service_type: str = "local"
    provider_name: str = ""
    enabled: bool = True
    model_path: str = ""
    device: str = "auto"
    precision: str = "auto"
    api_base_url: str = ""
    api_model: str = ""
    validation_status: str = "unchecked"
    validation_message: str = "尚未检查"


class VisualModelConfig(BaseModel):
    id: str
    display_name: str
    description: str = ""
    local_profiles_path: str = ""
    translation_profile_path: str = ""
    builtin: bool = False
    recommended_models: list[str] = Field(default_factory=list)
    quality_label: str = "自定义"
    prefer_gpu: bool = True
    content_types: list[str] = Field(default_factory=lambda: ["通用"])
    tags: list[str] = Field(default_factory=list)
    last_check_status: str = "unchecked"
    last_check_summary: str = "尚未检查"
    stages: list[VisualStageConfig] = Field(default_factory=list)


class _VisualModelConfigPayload(BaseModel):
    configs: list[VisualModelConfig] = Field(default_factory=list)


class VisualModelConfigStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def list_all(self) -> list[VisualModelConfig]:
        return [*_builtin_visual_configs(), *self._load_custom()]

    def get(self, config_id: str) -> VisualModelConfig:
        for config in self.list_all():
            if config.id == config_id:
                return config
        raise KeyError(config_id)

    def create_blank_config(self, *, display_name: str = "新的模型配置") -> VisualModelConfig:
        config = VisualModelConfig(
            id=_new_custom_id(),
            display_name=display_name,
            description="",
            local_profiles_path="",
            translation_profile_path="",
            builtin=False,
            recommended_models=[],
            stages=_default_stages(),
        )
        self.save_custom(config)
        return config

    def copy_config(
        self,
        source_id: str,
        *,
        display_name: str | None = None,
        description: str | None = None,
    ) -> VisualModelConfig:
        source = self.get(source_id)
        config = source.model_copy(
            update={
                "id": _new_custom_id(),
                "display_name": display_name or f"{source.display_name} 副本",
                "description": description if description is not None else source.description,
                "builtin": False,
            },
            deep=True,
        )
        self.save_custom(config)
        return config

    def save_custom(self, config: VisualModelConfig) -> VisualModelConfig:
        if config.builtin:
            raise ValueError("内置配置不能直接保存，请先复制为自定义配置。")
        customs = [item for item in self._load_custom() if item.id != config.id]
        customs.append(config)
        self._save_custom(customs)
        return config

    def delete_custom(self, config_id: str) -> None:
        config = self.get(config_id)
        if config.builtin:
            raise ValueError("内置配置不能删除。")
        self._save_custom([item for item in self._load_custom() if item.id != config_id])

    def _load_custom(self) -> list[VisualModelConfig]:
        if not self.path.is_file():
            return []
        payload = _VisualModelConfigPayload.model_validate(
            json.loads(self.path.read_text(encoding="utf-8"))
        )
        return payload.configs

    def _save_custom(self, configs: list[VisualModelConfig]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            _VisualModelConfigPayload(configs=configs).model_dump_json(indent=2),
            encoding="utf-8",
        )


def _builtin_visual_configs() -> list[VisualModelConfig]:
    return [_from_preset(preset) for preset in builtin_model_presets()]


def _from_preset(preset: ModelPreset) -> VisualModelConfig:
    # 尝试从翻译 profile 文件读取实际模型名称和 API 地址
    translation_model = ""
    translation_base_url = ""
    if preset.translation_profile_path:
        translation_model, translation_base_url = _read_translation_profile(
            preset.translation_profile_path
        )
    return VisualModelConfig(
        id=preset.id,
        display_name=preset.display_name,
        description=preset.description,
        local_profiles_path=preset.local_profiles_path,
        translation_profile_path=preset.translation_profile_path,
        builtin=True,
        recommended_models=preset.recommended_models,
        quality_label=_quality_label(preset.quality),
        prefer_gpu=preset.requires_gpu or preset.quality in {"high", "fast"},
        content_types=["美剧", "日剧", "韩剧", "通用"],
        tags=_preset_tags(preset),
        stages=_default_stages(
            translation_is_http=bool(preset.translation_profile_path),
            quality=preset.quality,
            translation_model=translation_model,
            translation_base_url=translation_base_url,
        ),
    )


def _default_stages(
    *,
    translation_is_http: bool = False,
    quality: str = "custom",
    translation_model: str = "",
    translation_base_url: str = "",
) -> list[VisualStageConfig]:
    stages: list[VisualStageConfig] = []
    for stage, label in STAGE_LABELS.items():
        service_type = "http" if stage == "translation" and translation_is_http else "local"
        provider_name = _default_provider_name(stage, service_type, quality)
        # 使用实际的翻译模型名称和 API 地址，如果没有则使用默认值
        api_model = ""
        api_base_url = ""
        if stage == "translation" and service_type == "http":
            api_model = translation_model or "Qwen3.6-35B-A3B"
            api_base_url = translation_base_url or "http://127.0.0.1:1995/v1"
        stages.append(
            VisualStageConfig(
                stage=stage,
                label=label,
                service_type=service_type,
                provider_name=provider_name,
                enabled=stage != "diarization" or translation_is_http,
                device="cuda" if quality in {"high", "fast"} else "auto",
                precision="float16" if quality in {"high", "fast"} else "auto",
                api_base_url=api_base_url,
                api_model=api_model,
            )
        )
    return stages


def _new_custom_id() -> str:
    return f"custom-{uuid4().hex[:12]}"


def _quality_label(quality: str) -> str:
    labels = {
        "high": "高质量",
        "fast": "快速预览",
        "preview": "CPU 预览",
        "custom": "自定义",
    }
    return labels.get(quality, "自定义")


def _preset_tags(preset: ModelPreset) -> list[str]:
    tags: list[str] = [_quality_label(preset.quality)]
    if preset.requires_gpu:
        tags.append("GPU")
    if preset.requires_lm_studio:
        tags.append("LM Studio")
    if preset.translation_profile_path:
        tags.append("在线 API")
    tags.append("本地模型" if preset.local_profiles_path else "自定义")
    return list(dict.fromkeys(tags))


def _default_provider_name(stage: str, service_type: str, quality: str) -> str:
    if service_type == "http":
        return "LM Studio / Qwen3.6"
    if stage == "separation":
        return "Demucs"
    if stage == "asr":
        return "faster-whisper large-v3" if quality == "high" else "faster-whisper small"
    if stage == "diarization":
        return "pyannote"
    if stage == "tts":
        return "F5-TTS"
    return "本地模型"


def _read_translation_profile(profile_path: str) -> tuple[str, str]:
    """从翻译 profile JSON 文件中读取模型名称和 API 基础地址"""
    try:
        path = Path(profile_path)
        if not path.is_file():
            return ("", "")
        data = json.loads(path.read_text(encoding="utf-8"))
        # 模型名称通常在 request_template.model 中
        request_template = data.get("request_template", {})
        model = request_template.get("model", "")
        model_name = model if isinstance(model, str) else ""
        # 从完整 URL 提取基础地址（去掉 /chat/completions 等后缀）
        full_url = data.get("url", "")
        base_url = _extract_base_url(full_url) if isinstance(full_url, str) else ""
        return (model_name, base_url)
    except (json.JSONDecodeError, OSError, KeyError):
        return ("", "")


def _extract_base_url(full_url: str) -> str:
    """从完整 API URL 中提取基础地址

    例如：http://127.0.0.1:1995/v1/chat/completions -> http://127.0.0.1:1995/v1
    """
    if not full_url:
        return ""
    # 常见的 API 后缀路径
    suffixes = ["/chat/completions", "/completions", "/v1/chat", "/generate"]
    for suffix in suffixes:
        if full_url.endswith(suffix):
            return full_url[: -len(suffix)]
    # 如果没有匹配的后缀，返回原 URL
    return full_url
