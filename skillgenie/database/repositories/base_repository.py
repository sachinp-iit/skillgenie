# ============================================================================
# Project      : SkillGenie
# File         : base_repository.py
# Description  : Base repository for all database repositories.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from sqlalchemy.orm import Session

from skillgenie.database.manager import DatabaseManager


class BaseRepository:
    """
    Base repository.
    """

    def __init__(self, database: DatabaseManager):
        """
        Initialize repository.

        Args:
            database: Database manager instance.
        """

        # Store database manager
        self._database = database

    def session(self) -> Session:
        """
        Create and return a new database session.
        """

        return self._database.get_session()

    def commit(self, session: Session) -> None:
        """
        Commit transaction.
        """

        session.commit()

    def rollback(self, session: Session) -> None:
        """
        Rollback transaction.
        """

        session.rollback()

    def close(self, session: Session) -> None:
        """
        Close database session.
        """

        session.close()