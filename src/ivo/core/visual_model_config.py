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


class VisualModelConfig(BaseModel):
    id: str
    display_name: str
    description: str = ""
    local_profiles_path: str = ""
    translation_profile_path: str = ""
    builtin: bool = False
    recommended_models: list[str] = Field(default_factory=list)
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
    return VisualModelConfig(
        id=preset.id,
        display_name=preset.display_name,
        description=preset.description,
        local_profiles_path=preset.local_profiles_path,
        translation_profile_path=preset.translation_profile_path,
        builtin=True,
        recommended_models=preset.recommended_models,
        stages=_default_stages(translation_is_http=bool(preset.translation_profile_path)),
    )


def _default_stages(*, translation_is_http: bool = False) -> list[VisualStageConfig]:
    stages: list[VisualStageConfig] = []
    for stage, label in STAGE_LABELS.items():
        service_type = "http" if stage == "translation" and translation_is_http else "local"
        stages.append(
            VisualStageConfig(
                stage=stage,
                label=label,
                service_type=service_type,
                provider_name="在线 API" if service_type == "http" else "本地模型",
                enabled=stage != "diarization" or translation_is_http,
            )
        )
    return stages


def _new_custom_id() -> str:
    return f"custom-{uuid4().hex[:12]}"
