from __future__ import annotations

from ivo.core.timeline import ModelProfile, ModelStage


class ModelRegistry:
    def __init__(self) -> None:
        self._profiles: dict[str, ModelProfile] = {}

    def register(self, profile: ModelProfile) -> None:
        self._profiles[profile.id] = profile

    def get(self, model_id: str) -> ModelProfile:
        return self._profiles[model_id]

    def list_all(self) -> list[ModelProfile]:
        return list(self._profiles.values())

    def list_by_stage(self, stage: ModelStage) -> list[ModelProfile]:
        return [profile for profile in self._profiles.values() if profile.stage == stage]
