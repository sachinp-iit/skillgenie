# ============================================================================
# Project      : SkillGenie
# File         : logger.py
# Description  : Centralized logger used across the SkillGenie library.
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

import sys

from loguru import logger

from skillgenie.config import Config


class Logger:
    """Central logger."""

    def __init__(self, config: Config):

        # Read log level from configuration
        log_level = config.get("logging.level", "INFO")

        # Remove default logger
        logger.remove()

        # Console logger
        logger.add(
            sys.stdout,
            level=log_level,
            colorize=True,
            enqueue=True,
            backtrace=True,
            diagnose=False
        )

        self._logger = logger

    @property
    def log(self):
        """Return logger instance."""
        return self._logger