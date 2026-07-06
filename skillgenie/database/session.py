# ============================================================================
# Project      : SkillGenie
# File         : session.py
# Description  : SQLAlchemy session manager.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from contextlib import contextmanager

from sqlalchemy.orm import Session
from sqlalchemy.orm import sessionmaker

from skillgenie.database.connection import Database


class DatabaseSession:
    """Database session manager."""

    def __init__(self, database: Database):
        """
        Initialize session factory.

        Args:
            database: Database connection instance.
        """

        # Store database reference
        self._database = database

        # Create session factory
        self._session_factory = sessionmaker(
            bind=self._database.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )

    def get_session(self) -> Session:
        """
        Create and return a new database session.

        Returns:
            SQLAlchemy Session.
        """

        return self._session_factory()

    @contextmanager
    def session_scope(self):
        """
        Context manager for automatic commit/rollback.

        Usage:

            with db_session.session_scope() as session:
                ...
        """

        session = self.get_session()

        try:

            yield session

            session.commit()

        except Exception:

            session.rollback()

            raise

        finally:

            session.close()