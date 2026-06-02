from __future__ import annotations


class LicenseStore:
    def __init__(self, confirmed_model_ids: set[str] | None = None) -> None:
        self._confirmed_model_ids: set[str] = confirmed_model_ids or set()

    def confirm(self, model_id: str) -> None:
        self._confirmed_model_ids.add(model_id)

    def is_confirmed(self, model_id: str) -> bool:
        return model_id in self._confirmed_model_ids

    def list_confirmed(self) -> list[str]:
        return sorted(self._confirmed_model_ids)
