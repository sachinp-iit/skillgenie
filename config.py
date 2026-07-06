# ============================================================================
# Project      : SkillGenie
# File         : config.py
# Description  : Loads configuration from JSON with environment variable
#                overrides. Used across the SkillGenie library.
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


class Config:
    """Configuration loader."""

    def __init__(self, config_file: str = "config/config.json") -> None:

        # Store config path
        self._config_file = Path(config_file)

        # Internal config dictionary
        self._config: dict[str, Any] = {}

        # Load configuration
        self._load()

    def _load(self) -> None:
        """Load JSON configuration."""

        if not self._config_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self._config_file}"
            )

        with open(self._config_file, "r", encoding="utf-8") as file:
            self._config = json.load(file)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.

        Example:
            config.get("database.url")
        """

        # Environment variable has highest priority
        env_key = key.upper().replace(".", "_")

        if env_key in os.environ:
            return os.environ[env_key]

        # Read nested JSON keys
        value = self._config

        for part in key.split("."):

            if not isinstance(value, dict):
                return default

            value = value.get(part)

            if value is None:
                return default

        return value

    def reload(self) -> None:
        """Reload configuration from disk."""

        self._load()