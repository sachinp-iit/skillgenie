# ============================================================================
# Project      : SkillGenie
# File         : engine.py
# Description  : Main entry point for the SkillGenie library.
#
#                This class initializes the configuration, database,
#                repositories, and all future SkillGenie components.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from skillgenie.config import Config
from skillgenie.database.bootstrap import bootstrap_database
from skillgenie.database.repositories.audit_repository import AuditRepository
from skillgenie.database.repositories.capability_repository import (
    CapabilityRepository,
)
from skillgenie.database.repositories.metrics_repository import MetricsRepository
from skillgenie.database.repositories.trace_repository import TraceRepository
from skillgenie.utils.logger import Logger


class SkillGenie:
    """
    Main SkillGenie Engine.
    """

    def __init__(self, config_file: str = "config/config.json"):
        """
        Initialize SkillGenie.

        Args:
            config_file: Path to configuration file.
        """

        # Load configuration
        self.config = Config(config_file)

        # Initialize logger
        self.logger = Logger(self.config).log

        self.logger.info("Initializing SkillGenie...")

        # Initialize database
        self.database = bootstrap_database(self.config)

        # Initialize repositories
        self.capabilities = CapabilityRepository(self.database)

        self.traces = TraceRepository(self.database)

        self.metrics = MetricsRepository(self.database)

        self.audit = AuditRepository(self.database)

        self.logger.info("SkillGenie initialized successfully.")

    def shutdown(self) -> None:
        """
        Shutdown SkillGenie.
        """

        self.database.close()

        self.logger.info("SkillGenie shutdown completed.")