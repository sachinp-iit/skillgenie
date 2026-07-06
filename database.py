# ============================================================================
# Project      : SkillGenie
# File         : database.py
# Description  : PostgreSQL database manager for SkillGenie.
#                Creates SQLAlchemy engine and session factory.
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from skillgenie.config import Config
from skillgenie.exceptions import DatabaseError


class Database:
    """Database manager."""

    def __init__(self, config: Config) -> None:

        # Store configuration
        self._config = config

        # Read database URL
        self._database_url = self._config.get("database.url")

        if not self._database_url:
            raise DatabaseError("Database URL not found.")

        # Create SQLAlchemy engine
        self._engine = create_engine(

            self._database_url,

            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )

        # Session factory
        self._session_factory = sessionmaker(

            bind=self._engine,

            autoflush=False,
            autocommit=False,
            expire_on_commit=False
        )

    @property
    def engine(self):
        """Return SQLAlchemy engine."""
        return self._engine

    def get_session(self):
        """Return a new database session."""
        return self._session_factory()

    def test_connection(self) -> bool:
        """Test PostgreSQL connection."""

        try:

            with self._engine.connect() as connection:

                connection.execute(text("SELECT 1"))

            return True

        except Exception as ex:

            raise DatabaseError(
                f"Database connection failed: {ex}"
            ) from ex

    def close(self) -> None:
        """Dispose engine."""

        self._engine.dispose()