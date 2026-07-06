# ============================================================================
# Project      : SkillGenie
# File         : manager.py
# Description  : Central database manager used by the SkillGenie library.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from skillgenie.config import Config
from skillgenie.database.connection import Database
from skillgenie.database.session import DatabaseSession


class DatabaseManager:
    """
    Central database manager.

    Responsible for:
        - Loading configuration
        - Creating database connection
        - Creating session manager
        - Exposing engine and sessions
    """

    def __init__(self, config: Config):
        """
        Initialize database manager.

        Args:
            config: SkillGenie configuration instance.
        """

        # Store configuration
        self._config = config

        # Initialize PostgreSQL connection
        self._database = Database(config)

        # Initialize session manager
        self._session = DatabaseSession(self._database)

    @property
    def engine(self):
        """
        Returns SQLAlchemy engine.
        """

        return self._database.engine

    def get_session(self):
        """
        Returns a new SQLAlchemy session.
        """

        return self._session.get_session()

    def session_scope(self):
        """
        Returns transactional session context manager.
        """

        return self._session.session_scope()

    def test_connection(self):
        """
        Test PostgreSQL connectivity.
        """

        return self._database.test_connection()

    def close(self):
        """
        Dispose all database connections.
        """

        self._database.close()