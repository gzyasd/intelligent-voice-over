from __future__ import annotations

import json
from pathlib import Path

from ivo.adapters.http import ApiAdapterProfile


class AdapterProfileStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[ApiAdapterProfile]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [ApiAdapterProfile.model_validate(item) for item in data["profiles"]]

    def save(self, profiles: list[ApiAdapterProfile]) -> None:
        seen: set[str] = set()
        for profile in profiles:
            if profile.id in seen:
                raise ValueError(f"duplicate adapter profile id: {profile.id}")
            seen.add(profile.id)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {"profiles": [profile.model_dump() for profile in profiles]},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
