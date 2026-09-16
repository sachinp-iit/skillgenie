# ============================================================================
# Project      : SkillGenie
# File         : privacy.py
# Description  : Privacy controls: telemetry opt-out, data residency flags
#                and PII redaction for traces and outcomes.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import re
from typing import Any

from skillgenie.config import Config


_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("phone", re.compile(r"(\+?\d[\d\s\-]{7,}\d)")),
    ("credit_card", re.compile(r"\b(?:\d[ -]*?){13,16}\b")),
    ("ip_address", re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
]

_NAMES = ["pii", "password", "secret", "token", "api_key", "apikey", "authorization", "private_key"]


class PrivacyGovernor:
    """
    Enforces privacy and data-residency policies.

    Features:
        - ``telemetry_enabled``: disable all optional telemetry/logging of
          payload content
        - ``data_residency``: restrict which categories may leave the cluster
        - ``redact``: mask PII inside strings, dicts and lists
    """

    def __init__(self, config: Config):
        self._config = config
        self._telemetry_enabled = config.get_bool("governance.privacy.telemetry_enabled", True)
        self._data_residency = config.get(
            "governance.privacy.data_residency",
            "self-hosted",
        )
        self._redact_enabled = config.get_bool("governance.privacy.redact_pii", True)

    @property
    def telemetry_enabled(self) -> bool:
        return self._telemetry_enabled

    @property
    def data_residency(self) -> str:
        return str(self._data_residency)

    def allows_provider(self, provider: str, allowed: list[str] | None = None) -> bool:
        """
        Whether a cloud provider is permitted under residency rules.

        Providers: ``self-hosted``, ``local``, ``us``, ``eu``, ``global``.
        """
        if self._data_residency == "self-hosted":
            return provider in {"self-hosted", "local"}
        if allowed is None:
            allowed = ["us", "eu", "global"]
        return provider in allowed or provider == "self-hosted"

    def redact(self, value: Any) -> Any:
        """
        Recursively mask PII within a value.
        """
        if not self._redact_enabled:
            return value
        return self._redact_value(value)

    def inspect(self, value: Any) -> dict[str, int]:
        """
        Count PII categories found in a value (no mutation).
        """
        counts: dict[str, int] = {}
        self._scan(value, counts)
        return counts

    # ------------------------------------------------------------------

    def _redact_value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self._redact_str(value)
        if isinstance(value, dict):
            return {
                key: (self._redact_secret_key(key, value[key]) if isinstance(key, str) else value[key])
                for key in value
            }
        if isinstance(value, list):
            return [self._redact_value(item) for item in value]
        return value

    def _redact_secret_key(self, key: str, value: Any) -> Any:
        lowered = key.lower()
        if any(name in lowered for name in _NAMES):
            return self._redact_value("[REDACTED]")
        return self._redact_value(value)

    def _redact_str(self, text: str) -> str:
        for name, pattern in _PII_PATTERNS:
            text = pattern.sub(f"[{name.upper()}_REDACTED]", text)
        return text

    def _scan(self, value: Any, counts: dict[str, int]) -> None:
        if isinstance(value, str):
            for name, pattern in _PII_PATTERNS:
                matches = pattern.findall(value)
                if matches:
                    counts[name] = counts.get(name, 0) + len(matches)
            lowered = value.lower()
            for name in _NAMES:
                if f"{name}=" in lowered or f"{name}:" in lowered:
                    counts["secret_like"] = counts.get("secret_like", 0) + 1
            return
        if isinstance(value, dict):
            for key, item in value.items():
                if isinstance(key, str) and any(name in key.lower() for name in _NAMES):
                    counts["secret_keys"] = counts.get("secret_keys", 0) + 1
                self._scan(item, counts)
            return
        if isinstance(value, list):
            for item in value:
                self._scan(item, counts)