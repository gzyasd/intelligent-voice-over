from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from ivo.core.timeline import ModelProfile
from ivo.models.licenses import LicenseStore
from ivo.models.registry import ModelRegistry


class StoredModelProfiles(BaseModel):
    profiles: list[ModelProfile] = Field(default_factory=list)
    confirmed_licenses: list[str] = Field(default_factory=list)


class ModelProfileStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> StoredModelProfiles:
        if not self.path.exists():
            return StoredModelProfiles()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return StoredModelProfiles.model_validate(data)

    def save(self, data: StoredModelProfiles) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            data.model_dump_json(indent=2),
            encoding="utf-8",
        )


class ModelManager:
    def __init__(
        self,
        registry: ModelRegistry,
        licenses: LicenseStore,
        store: ModelProfileStore | None = None,
    ) -> None:
        self.registry = registry
        self.licenses = licenses
        self.store = store

    @classmethod
    def from_store(cls, path: Path) -> ModelManager:
        store = ModelProfileStore(path)
        data = store.load()
        registry = ModelRegistry()
        for profile in data.profiles:
            registry.register(profile)
        return cls(
            registry,
            LicenseStore(set(data.confirmed_licenses)),
            store,
        )

    def register_local_model(
        self,
        *,
        model_id: str,
        stage: str,
        name: str,
        path: Path,
        languages: list[str],
    ) -> ModelProfile:
        profile = ModelProfile(
            id=model_id,
            stage=stage,  # type: ignore[arg-type]
            backend="local",
            name=name,
            config={"path": str(path), "languages": languages},
        )
        self.registry.register(profile)
        return profile

    def can_use(self, model_id: str) -> bool:
        return self.licenses.is_confirmed(model_id)

    def save(self) -> None:
        if self.store is None:
            raise RuntimeError("model manager has no backing store")
        self.store.save(
            StoredModelProfiles(
                profiles=self.registry.list_all(),
                confirmed_licenses=self.licenses.list_confirmed(),
            )
        )
