# ============================================================================
# Project      : SkillGenie
# File         : config.py
# Description  : Loads configuration from JSON with environment variable
#                overrides.
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


class Config:
    """
    Configuration loader.
    """

    def __init__(self, config_file: str = "config/config.json") -> None:
        """
        Initialize configuration.

        Args:
            config_file: Path to configuration JSON.
        """

        # Store configuration file path
        self._config_file = Path(config_file)

        # Internal configuration dictionary
        self._config: dict[str, Any] = {}

        # Load configuration
        self._load()

    def _load(self) -> None:
        """
        Load configuration from JSON file.
        """

        if not self._config_file.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self._config_file}"
            )

        with open(self._config_file, "r", encoding="utf-8") as file:
            self._config = json.load(file)

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

        # Convert nested key into environment variable
        env_key = key.upper().replace(".", "_")

        # Environment variables have highest priority
        env_value = os.getenv(env_key)

        if env_value is not None:
            return env_value

        # Read nested JSON
        value: Any = self._config

        for part in key.split("."):

            if not isinstance(value, dict):
                return default

            value = value.get(part)

            if value is None:
                return default

        return value

    def reload(self) -> None:
        """
        Reload configuration from disk.
        """

        self._load()