# ============================================================================
# Project      : SkillGenie
# File         : capability_repository.py
# Description  : Repository for CRUD operations on the skills table.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from uuid import UUID

from sqlalchemy import text

from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.base_repository import BaseRepository


class CapabilityRepository(BaseRepository):
    """
    Repository for the skills table.
    """

    def __init__(self, database: DatabaseManager):
        """
        Initialize repository.

        Args:
            database: Database manager.
        """

        super().__init__(database)

    def create(
        self,
        capability_id: UUID,
        name: str,
        description: str,
        category: str,
        version: str,
        status: str,
    ) -> None:
        """
        Create a new capability.
        """

        session = self.session()

        try:

            session.execute(
                text(
                    """
                    INSERT INTO skills
                    (
                        id,
                        name,
                        description,
                        category,
                        version,
                        status
                    )
                    VALUES
                    (
                        :id,
                        :name,
                        :description,
                        :category,
                        :version,
                        :status
                    )
                    """
                ),
                {
                    "id": str(capability_id),
                    "name": name,
                    "description": description,
                    "category": category,
                    "version": version,
                    "status": status,
                },
            )

            self.commit(session)

        except Exception:

            self.rollback(session)

            raise

        finally:

            self.close(session)

    def get_by_id(self, capability_id: UUID):
        """
        Get capability by id.
        """

        session = self.session()

        try:

            result = session.execute(
                text(
                    """
                    SELECT *
                    FROM skills
                    WHERE id = :id
                    """
                ),
                {
                    "id": str(capability_id),
                },
            )

            return result.mappings().first()

        finally:

            self.close(session)

    def get_by_name(self, name: str):
        """
        Get capability by name.
        """

        session = self.session()

        try:

            result = session.execute(
                text(
                    """
                    SELECT *
                    FROM skills
                    WHERE name = :name
                    """
                ),
                {
                    "name": name,
                },
            )

            return result.mappings().first()

        finally:

            self.close(session)

    def list(self):
        """
        Return all capabilities.
        """

        session = self.session()

        try:

            result = session.execute(
                text(
                    """
                    SELECT *
                    FROM skills
                    ORDER BY created_at DESC
                    """
                )
            )

            return result.mappings().all()

        finally:

            self.close(session)

    def delete(self, capability_id: UUID) -> None:
        """
        Delete capability.
        """

        session = self.session()

        try:

            session.execute(
                text(
                    """
                    DELETE
                    FROM skills
                    WHERE id = :id
                    """
                ),
                {
                    "id": str(capability_id),
                },
            )

            self.commit(session)

        except Exception:

            self.rollback(session)

            raise

        finally:

            self.close(session)