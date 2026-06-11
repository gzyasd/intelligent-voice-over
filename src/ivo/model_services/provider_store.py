"""JSON-based persistence for provider accounts and stage configs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ivo.model_services.provider_config import (
    DubbingScheme,
    ProviderAccount,
    StageProviderConfig,
)


class ProviderStore:
    """Stores provider accounts and stage configs as JSON files.

    No plaintext API keys are stored here; secrets are managed by SecretStore.
    """

    def __init__(self, store_dir: Path) -> None:
        self._dir = store_dir
        self._accounts_file = store_dir / "provider-accounts.json"
        self._configs_file = store_dir / "stage-provider-configs.json"
        self._schemes_file = store_dir / "schemes.json"
        self._dir.mkdir(parents=True, exist_ok=True)

    # -- Accounts --

    def save_account(self, account: ProviderAccount) -> None:
        accounts = self._load_json_list(self._accounts_file)
        # Update or append
        for i, item in enumerate(accounts):
            if item.get("id") == account.id:
                accounts[i] = account.model_dump()
                break
        else:
            accounts.append(account.model_dump())
        self._save_json_list(self._accounts_file, accounts)

    def load_accounts(self) -> list[ProviderAccount]:
        items = self._load_json_list(self._accounts_file)
        return [ProviderAccount.model_validate(item) for item in items]

    def get_account(self, account_id: str) -> ProviderAccount | None:
        for account in self.load_accounts():
            if account.id == account_id:
                return account
        return None

    def delete_account(self, account_id: str) -> None:
        accounts = self._load_json_list(self._accounts_file)
        accounts = [a for a in accounts if a.get("id") != account_id]
        self._save_json_list(self._accounts_file, accounts)

    # -- Stage Configs --

    def save_stage_config(self, config: StageProviderConfig) -> None:
        configs = self._load_json_list(self._configs_file)
        for i, item in enumerate(configs):
            if item.get("id") == config.id:
                configs[i] = config.model_dump()
                break
        else:
            configs.append(config.model_dump())
        self._save_json_list(self._configs_file, configs)

    def load_stage_configs(self) -> list[StageProviderConfig]:
        items = self._load_json_list(self._configs_file)
        return [StageProviderConfig.model_validate(item) for item in items]

    def get_stage_config(self, config_id: str) -> StageProviderConfig | None:
        for config in self.load_stage_configs():
            if config.id == config_id:
                return config
        return None

    def delete_stage_config(self, config_id: str) -> None:
        configs = self._load_json_list(self._configs_file)
        configs = [c for c in configs if c.get("id") != config_id]
        self._save_json_list(self._configs_file, configs)

    # -- Schemes --

    def save_scheme(self, scheme: DubbingScheme) -> None:
        schemes = self._load_json_list(self._schemes_file)
        for i, item in enumerate(schemes):
            if item.get("id") == scheme.id:
                schemes[i] = scheme.model_dump()
                break
        else:
            schemes.append(scheme.model_dump())
        self._save_json_list(self._schemes_file, schemes)

    def load_schemes(self) -> list[DubbingScheme]:
        items = self._load_json_list(self._schemes_file)
        return [DubbingScheme.model_validate(item) for item in items]

    def get_scheme(self, scheme_id: str) -> DubbingScheme | None:
        for scheme in self.load_schemes():
            if scheme.id == scheme_id:
                return scheme
        return None

    def delete_scheme(self, scheme_id: str) -> None:
        schemes = self._load_json_list(self._schemes_file)
        schemes = [s for s in schemes if s.get("id") != scheme_id]
        self._save_json_list(self._schemes_file, schemes)

    def load_default_scheme_id(self) -> str | None:
        """Return the ID of the default scheme, if set."""
        default_file = self._dir / "default-scheme.json"
        if not default_file.is_file():
            return None
        import json as _json
        try:
            data = _json.loads(default_file.read_text(encoding="utf-8"))
            result: str | None = data.get("scheme_id")
            return result
        except Exception:
            return None

    def save_default_scheme_id(self, scheme_id: str) -> None:
        """Persist the default scheme ID."""
        import json as _json
        default_file = self._dir / "default-scheme.json"
        default_file.write_text(
            _json.dumps({"scheme_id": scheme_id}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # -- Export (without secrets) --

    def export_config(self) -> dict[str, Any]:
        """Export accounts and configs without secret references.

        Users must re-enter API keys after importing.
        """
        accounts = []
        for account in self.load_accounts():
            exported = account.model_dump()
            # Strip secret references for export
            exported.pop("api_key_ref", None)
            accounts.append(exported)

        configs = [config.model_dump() for config in self.load_stage_configs()]

        return {
            "accounts": accounts,
            "stage_configs": configs,
        }

    # -- Internal JSON helpers --

    def _load_json_list(self, path: Path) -> list[dict[str, Any]]:
        if not path.is_file():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
        return []

    def _save_json_list(self, path: Path, items: list[dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
