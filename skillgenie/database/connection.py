# ============================================================================
# Project      : SkillGenie
# File         : connection.py
# Description  : PostgreSQL connection manager for SkillGenie.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from skillgenie.config import Config
from skillgenie.exceptions import DatabaseError


class Database:
    """PostgreSQL database connection manager."""

    def __init__(self, config: Config):
        """
        Initialize database connection.

        Args:
            config: SkillGenie configuration object.
        """

        # Store configuration
        self._config = config

        # Read database URL
        self._database_url = self._config.get("database.url")

        if not self._database_url:
            raise DatabaseError("Database URL is not configured.")

        # Create SQLAlchemy engine
        self._engine = create_engine(
            self._database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            future=True,
            echo=False
        )

    @property
    def engine(self) -> Engine:
        """
        Returns SQLAlchemy engine.
        """
        return self._engine

    def test_connection(self) -> bool:
        """
        Test database connectivity.

        Returns:
            True if successful.
        """

        try:

            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))

            return True

        except Exception as ex:
            raise DatabaseError(
                f"Failed to connect to PostgreSQL: {ex}"
            ) from ex

    def close(self) -> None:
        """
        Dispose all pooled database connections.
        """

        self._engine.dispose()