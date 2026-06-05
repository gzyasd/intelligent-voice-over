from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


class SpeakerProfile(BaseModel):
    id: str
    display_name: str
    reference_segment_ids: list[str] = Field(default_factory=list)
    preferred_tts_profile_id: str | None = None
    notes: str = ""

    @field_validator("id", "display_name")
    @classmethod
    def require_non_empty_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("speaker profile text cannot be empty")
        return value


class SpeakerProfileStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def get(self, speaker_id: str) -> SpeakerProfile | None:
        return self._load().get(speaker_id)

    def list_profiles(self) -> list[SpeakerProfile]:
        return sorted(self._load().values(), key=lambda profile: profile.id)

    def upsert(self, profile: SpeakerProfile) -> SpeakerProfile:
        profiles = self._load()
        profiles[profile.id] = profile
        self._save(profiles)
        return profile

    def set_reference_segment(
        self,
        speaker_id: str,
        segment_id: str,
        *,
        display_name: str | None = None,
    ) -> SpeakerProfile:
        profile = self.get(speaker_id) or SpeakerProfile(
            id=speaker_id,
            display_name=display_name or speaker_id,
        )
        reference_ids = [
            segment_id,
            *[
                existing_id
                for existing_id in profile.reference_segment_ids
                if existing_id != segment_id
            ],
        ]
        return self.upsert(profile.model_copy(update={"reference_segment_ids": reference_ids}))

    def clear_reference_segment(self, speaker_id: str, segment_id: str) -> SpeakerProfile:
        profile = self.get(speaker_id) or SpeakerProfile(id=speaker_id, display_name=speaker_id)
        reference_ids = [
            existing_id
            for existing_id in profile.reference_segment_ids
            if existing_id != segment_id
        ]
        return self.upsert(profile.model_copy(update={"reference_segment_ids": reference_ids}))

    def rename(self, speaker_id: str, display_name: str) -> SpeakerProfile:
        profile = self.get(speaker_id) or SpeakerProfile(id=speaker_id, display_name=display_name)
        return self.upsert(profile.model_copy(update={"display_name": display_name}))

    def _load(self) -> dict[str, SpeakerProfile]:
        if not self.path.is_file():
            return {}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        raw_profiles = raw.get("speakers", [])
        if not isinstance(raw_profiles, list):
            return {}
        profiles: dict[str, SpeakerProfile] = {}
        for raw_profile in raw_profiles:
            profile = SpeakerProfile.model_validate(raw_profile)
            profiles[profile.id] = profile
        return profiles

    def _save(self, profiles: dict[str, SpeakerProfile]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "speakers": [
                profile.model_dump()
                for profile in sorted(profiles.values(), key=lambda item: item.id)
            ]
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
