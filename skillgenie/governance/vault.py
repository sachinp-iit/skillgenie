# ============================================================================
# Project      : SkillGenie
# File         : vault.py
# Description  : Lightweight secret vault for API keys and provider tokens.
#                Supports an optional ``keyring`` backend when available and
#                falls back to an encrypted file store.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any


class SecretVault:
    """
    Stores and retrieves secrets without printing them.

    Backends (in order of preference):
        1. System keyring (via the ``keyring`` package, if installed)
        2. Encrypted file at ``{path}/{file}/vault.json`` protected by a
           locally-derived key from environment variable ``VAULT_KEY``.
    """

    def __init__(self, path: str = "config/secrets", vault_key_env: str = "VAULT_KEY"):
        self._path = Path(path)
        self._vault_key_env = vault_key_env
        self._file = self._path / "vault.json"

    def set(self, name: str, secret: str) -> None:
        """Store a secret by name."""
        if self._keyring_available():
            try:
                import keyring

                keyring.set_password("skillgenie", name, secret)
                return
            except Exception:
                pass
        store = self._file_store()
        store[name] = secret
        self._persist(store)

    def get(self, name: str) -> str | None:
        """Retrieve a secret by name."""
        if self._keyring_available():
            try:
                import keyring

                secret = keyring.get_password("skillgenie", name)
                if secret:
                    return secret
            except Exception:
                pass
        return self._file_store().get(name)

    def delete(self, name: str) -> None:
        """Delete a secret by name."""
        if self._keyring_available():
            try:
                import keyring

                keyring.delete_password("skillgenie", name)
            except Exception:
                pass
        data = self._file_store()
        data.pop(name, None)
        self._persist(data)

    def list_names(self) -> list[str]:
        """List stored secret names (not values)."""
        if self._keyring_available():
            try:
                import keyring

                return sorted(keyring.get_credential("skillgenie", "") or [])
            except Exception:
                pass
        return sorted(self._file_store().keys())

    # ------------------------------------------------------------------

    def _data(self) -> dict[str, str]:
        if not self._file.exists():
            return {}
        try:
            raw = self._file.read_text(encoding="utf-8").strip()
            if not raw:
                return {}
            payload = json.loads(raw)
            return self._decrypt(payload)
        except Exception:
            return {}

    def _file_store(self) -> dict[str, str]:
        if not hasattr(self, "_cache"):
            self._cache = self._data()
        return self._cache

    def _persist(self, data: dict[str, str]) -> None:
        self._path.mkdir(parents=True, exist_ok=True)
        self._file.write_text(json.dumps(self._encrypt(data)), encoding="utf-8")
        self._cache = dict(data)

    def _encrypt(self, data: dict[str, str]) -> dict[str, Any]:
        key = self._vault_key()
        if not key:
            return {"data": data}
        payload = json.dumps(data).encode("utf-8")
        xored = bytes(c ^ key[i % len(key)] for i, c in enumerate(payload))
        return {"data": base64.b64encode(xored).decode("ascii")}

    def _decrypt(self, payload: dict[str, Any]) -> dict[str, str]:
        data = payload.get("data", {})
        if isinstance(data, dict):
            return {k: str(v) for k, v in data.items()}
        key = self._vault_key()
        if not key:
            return {}
        try:
            xored = base64.b64decode(str(data))
            decrypted = bytes(c ^ key[i % len(key)] for i, c in enumerate(xored))
            return json.loads(decrypted.decode("utf-8"))
        except Exception:
            return {}

    def _vault_key(self) -> bytes | None:
        raw = os.getenv(self._vault_key_env, "")
        if not raw:
            return None
        return raw.encode("utf-8")

    @staticmethod
    def _keyring_available() -> bool:
        try:
            import keyring  # noqa: F401

            return True
        except ImportError:
            return False