"""Encrypted secret storage with DPAPI / keyring / portable fallback."""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Literal


ProtectionLevel = Literal["dpapi", "keyring", "portable_fallback"]

# Try to import DPAPI (Windows only)
_DPAPI_AVAILABLE = False
try:
    import ctypes  # noqa: F401
    import ctypes.wintypes  # noqa: F401

    # Test if win32crypt is available
    import win32crypt  # type: ignore[import-untyped]  # noqa: F401

    _DPAPI_AVAILABLE = True
except (ImportError, OSError):
    pass

# Try to import keyring
_KEYRING_AVAILABLE = False
try:
    import keyring  # type: ignore[import-not-found]  # noqa: F401

    _KEYRING_AVAILABLE = True
except ImportError:
    pass


class SecretStore:
    """Stores API keys with platform-appropriate encryption.

    Protection priority:
    1. Windows DPAPI (via win32crypt)
    2. keyring library
    3. Portable XOR + hash fallback (NOT secure, only prevents casual reading)
    """

    _KEYRING_SERVICE = "ivo-model-services"
    _FALLBACK_KEY_FILE = "provider-secrets.json"

    def __init__(self, store_dir: Path) -> None:
        self._dir = store_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._fallback_file = store_dir / self._FALLBACK_KEY_FILE
        self._protection_level: ProtectionLevel = self._detect_level()

    @property
    def protection_level(self) -> ProtectionLevel:
        return self._protection_level

    def save(self, secret_id: str, plaintext: str) -> None:
        """Encrypt and store a secret."""
        if self._protection_level == "dpapi":
            self._save_dpapi(secret_id, plaintext)
        elif self._protection_level == "keyring":
            self._save_keyring(secret_id, plaintext)
        else:
            self._save_fallback(secret_id, plaintext)

    def load(self, secret_id: str) -> str | None:
        """Decrypt and return a secret, or None if not found."""
        if self._protection_level == "dpapi":
            return self._load_dpapi(secret_id)
        elif self._protection_level == "keyring":
            return self._load_keyring(secret_id)
        else:
            return self._load_fallback(secret_id)

    def delete(self, secret_id: str) -> None:
        """Remove a secret."""
        if self._protection_level == "dpapi":
            self._delete_dpapi(secret_id)
        elif self._protection_level == "keyring":
            self._delete_keyring(secret_id)
        else:
            self._delete_fallback(secret_id)

    def list_ids(self) -> list[str]:
        """List all stored secret IDs."""
        if self._protection_level == "dpapi":
            return self._list_dpapi()
        elif self._protection_level == "keyring":
            return self._list_keyring()
        else:
            return self._list_fallback()

    # -- DPAPI implementation --

    def _save_dpapi(self, secret_id: str, plaintext: str) -> None:
        try:
            encrypted = win32crypt.CryptProtectData(  # type: ignore[name-defined,unused-ignore]
                plaintext.encode("utf-8"),
                None,
                None,
                None,
                None,
                0,
            )
            encoded = base64.b64encode(encrypted).decode("ascii")
            self._update_fallback_file_for_index(secret_id, encoded)
        except Exception:
            # Fall back to portable
            self._protection_level = "portable_fallback"
            self._save_fallback(secret_id, plaintext)

    def _load_dpapi(self, secret_id: str) -> str | None:
        data = self._read_fallback_index(secret_id)
        if data is None:
            return None
        try:
            encrypted = base64.b64decode(data)
            decrypted = win32crypt.CryptUnprotectData(  # type: ignore[name-defined,unused-ignore]
                encrypted, None, None, None, None, 0
            )
            result: str = decrypted[1].decode("utf-8")
            return result
        except Exception:
            return None

    def _delete_dpapi(self, secret_id: str) -> None:
        self._remove_fallback_index(secret_id)

    def _list_dpapi(self) -> list[str]:
        return self._list_fallback_ids()

    # -- Keyring implementation --

    def _save_keyring(self, secret_id: str, plaintext: str) -> None:
        keyring.set_password(self._KEYRING_SERVICE, secret_id, plaintext)
        self._update_fallback_file_for_index(secret_id, "[keyring]")

    def _load_keyring(self, secret_id: str) -> str | None:
        result = keyring.get_password(self._KEYRING_SERVICE, secret_id)
        return result  # type: ignore[no-any-return]

    def _delete_keyring(self, secret_id: str) -> None:
        try:
            keyring.delete_password(self._KEYRING_SERVICE, secret_id)
        except keyring.errors.PasswordDeleteError:
            pass
        self._remove_fallback_index(secret_id)

    def _list_keyring(self) -> list[str]:
        return self._list_fallback_ids()

    # -- Portable fallback implementation --

    def _save_fallback(self, secret_id: str, plaintext: str) -> None:
        # XOR with a derived key (NOT cryptographically secure, just prevents casual reading)
        encoded = self._xor_obfuscate(plaintext)
        self._update_fallback_file_for_index(secret_id, encoded)

    def _load_fallback(self, secret_id: str) -> str | None:
        data = self._read_fallback_index(secret_id)
        if data is None:
            return None
        return self._xor_deobfuscate(data)

    def _delete_fallback(self, secret_id: str) -> None:
        self._remove_fallback_index(secret_id)

    def _list_fallback(self) -> list[str]:
        return self._list_fallback_ids()

    # -- Shared file-based index --

    def _load_index(self) -> dict[str, str]:
        if not self._fallback_file.is_file():
            return {}
        data = json.loads(self._fallback_file.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
        return {}

    def _save_index(self, index: dict[str, str]) -> None:
        self._fallback_file.write_text(
            json.dumps(index, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _update_fallback_file_for_index(self, secret_id: str, encoded: str) -> None:
        index = self._load_index()
        index[secret_id] = encoded
        self._save_index(index)

    def _read_fallback_index(self, secret_id: str) -> str | None:
        index = self._load_index()
        return index.get(secret_id)

    def _remove_fallback_index(self, secret_id: str) -> None:
        index = self._load_index()
        index.pop(secret_id, None)
        self._save_index(index)

    def _list_fallback_ids(self) -> list[str]:
        index = self._load_index()
        return list(index.keys())

    # -- XOR obfuscation (portable fallback only) --

    @staticmethod
    def _derive_xor_key() -> bytes:
        """Derive a deterministic key from machine-specific info."""
        machine_id = os.environ.get("COMPUTERNAME", os.environ.get("HOSTNAME", "default"))
        return hashlib.sha256(f"ivo-ms-{machine_id}".encode()).digest()

    def _xor_obfuscate(self, plaintext: str) -> str:
        key = self._derive_xor_key()
        data = plaintext.encode("utf-8")
        xored = bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
        return base64.b64encode(xored).decode("ascii")

    def _xor_deobfuscate(self, encoded: str) -> str:
        key = self._derive_xor_key()
        xored = base64.b64decode(encoded)
        data = bytes(b ^ key[i % len(key)] for i, b in enumerate(xored))
        return data.decode("utf-8")

    # -- Level detection --

    def _detect_level(self) -> ProtectionLevel:
        if _DPAPI_AVAILABLE:
            return "dpapi"
        if _KEYRING_AVAILABLE:
            return "keyring"
        return "portable_fallback"
