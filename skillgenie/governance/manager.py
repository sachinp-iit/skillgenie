# ============================================================================
# Project      : SkillGenie
# File         : manager.py
# Description  : Single entry point for governance controls (privacy, secrets
#                and compliance headers) as used by the engine and API.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any

from skillgenie.config import Config
from skillgenie.governance.privacy import PrivacyGovernor
from skillgenie.governance.vault import SecretVault


class GovernanceManager:
    """
    Aggregates privacy controls and the secret vault.
    """

    def __init__(
        self,
        config: Config,
        vault_path: str = "config/secrets",
        vault_key_env: str = "VAULT_KEY",
    ):
        self._config = config
        self.privacy = PrivacyGovernor(config)
        self.vault = SecretVault(path=vault_path, vault_key_env=vault_key_env)

    @property
    def telemetry_enabled(self) -> bool:
        return self.privacy.telemetry_enabled

    @property
    def data_residency(self) -> str:
        return self.privacy.data_residency

    def redact(self, value: Any) -> Any:
        """Redact PII before persistence/external calls when enabled."""
        if self.privacy._redact_enabled:
            return self.privacy.redact(value)
        return value

    def report(self) -> dict[str, Any]:
        """Return a governance compliance summary."""
        return {
            "telemetry_enabled": self.telemetry_enabled,
            "data_residency": self.data_residency,
            "vault_backend": "keyring" if self.vault._keyring_available() else "file",
            "vault_secrets": len(self.vault.list_names()),
            "pii_redaction_enabled": bool(self.privacy._redact_enabled),
        }