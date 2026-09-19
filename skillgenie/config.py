# ============================================================================
# Project      : SkillGenie
# File         : config.py
# Description  : Loads configuration from JSON with environment variable
#                overrides. Ships sensible defaults and auto-creates a
#                config.json when none exists.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Default configuration applied when config.json is absent
DEFAULT_CONFIG: dict[str, Any] = {
    "database": {
        "url": "postgresql+psycopg://postgres:password@localhost:5432/skillgenie",
    },
    "logging": {
        "level": "INFO",
    },
    "embeddings": {
        "provider": "sentence-transformers",
        "model": "BAAI/bge-small-en-v1.5",
        "dimensions": 384,
        "batch_size": 32,
    },
    "openrouter": {
        "api_key": "",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openai/gpt-4.1-mini",
    },
    "learning": {
        "enabled": True,
        "auto_approval": False,
        "auto_publish": False,
        "min_execution_count": 5,
        "min_success_rate": 0.90,
        "mode": "AUTOMATIC",
    },
    "similarity": {
        "threshold": 0.85,
        "recommendation_threshold": 0.80,
        "auto_approval_threshold": 0.95,
    },
    "monitoring": {
        "enabled": True,
        "interval_seconds": 60,
    },
    "feedback": {
        "drift_threshold": 0.20,
        "drift_window_hours": 168,
    },
    "ranking": {
        "mode": "hybrid",
        "fit_weight": 0.50,
        "bandit_weight": 0.20,
        "recency_weight": 0.15,
        "latency_weight": 0.15,
    },
    "arena": {
        "leaderboard_path": "arena.leaderboard.json",
    },
    "mcp": {
        "enabled": True,
        "host": "127.0.0.1",
        "port": 3100,
    },
    "integrations": {
        "enabled": True,
    },
    "benchmark": {
        "success_overlap": 0.50,
    },
    "governance": {
        "privacy": {
            "telemetry_enabled": True,
            "data_residency": "self-hosted",
            "redact_pii": True,
        },
        "vault": {
            "path": "config/secrets",
            "key_env": "VAULT_KEY",
        },
    },
}


class Config:
    """
    Configuration loader.

    Priority:
        1. Environment Variable
        2. config.json
        3. Default value
    """

    def __init__(self, config_file: str = "config/config.json") -> None:
        """
        Initialize configuration.

        Args:
            config_file: Path to configuration JSON.
        """

        self._config_file = Path(config_file)

        self._config: dict[str, Any] = {}

        self._load()

    def _load(self) -> None:
        """
        Load configuration from JSON file. When the file does not exist it is
        created from the package defaults so the library remains usable
        out-of-the-box.
        """

        if not self._config_file.exists():
            file_data = DEFAULT_CONFIG

            try:
                self._config_file.parent.mkdir(parents=True, exist_ok=True)
                self._config_file.write_text(
                    json.dumps(DEFAULT_CONFIG, indent=4),
                    encoding="utf-8",
                )
            except OSError:
                pass
        else:
            with open(self._config_file, "r", encoding="utf-8") as file:
                file_data = json.load(file)

        self._config = self._merge(DEFAULT_CONFIG, file_data)

    def _merge(
        self,
        defaults: dict[str, Any],
        override: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Deep merge `override` on top of `defaults`.
        """

        merged = dict(defaults)

        for key, value in override.items():
            if (
                isinstance(value, dict)
                and isinstance(merged.get(key), dict)
            ):
                merged[key] = self._merge(merged[key], value)
            else:
                merged[key] = value

        return merged

    def get(self, key: str, default: Any = None) -> Any:
        """
        Returns configuration value.

        Priority:
            1. Environment Variable
            2. config.json
            3. Default Value

        Example:
            config.get("database.url")
        """

        env_key = key.upper().replace(".", "_")

        env_value = os.getenv(env_key)

        if env_value is not None:
            return env_value

        value: Any = self._config

        for part in key.split("."):

            if not isinstance(value, dict):
                return default

            value = value.get(part)

            if value is None:
                return default

        return value

    def get_bool(self, key: str, default: bool = False) -> bool:
        """
        Return a boolean configuration value.
        """

        value = self.get(key)

        if value is None:
            return default

        if isinstance(value, bool):
            return value

        return str(value).strip().lower() in {
            "true",
            "1",
            "yes",
            "y",
            "on",
        }

    def get_int(self, key: str, default: int = 0) -> int:
        """
        Return an integer configuration value.
        """

        value = self.get(key)

        if value is None:
            return default

        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def get_float(self, key: str, default: float = 0.0) -> float:
        """
        Return a float configuration value.
        """

        value = self.get(key)

        if value is None:
            return default

        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def set(self, key: str, value: Any) -> None:
        """
        Set a nested configuration value in memory.

        Args:
            key: Dotted key such as "ranking.mode".
            value: New value.
        """

        parts = key.split(".")

        target = self._config

        for part in parts[:-1]:
            child = target.get(part)

            if not isinstance(child, dict):
                child = {}
                target[part] = child

            target = child

        target[parts[-1]] = value

    @property
    def config_file(self) -> Path:
        """
        Path to the loaded configuration file.
        """

        return self._config_file

    @property
    def as_dict(self) -> dict[str, Any]:
        """
        Full merged configuration as a dictionary.
        """

        return dict(self._config)

    def reload(self) -> None:
        """
        Reload configuration from disk.
        """

        self._load()