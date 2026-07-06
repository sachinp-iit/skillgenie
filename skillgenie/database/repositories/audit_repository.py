# ============================================================================
# Project      : SkillGenie
# File         : audit_repository.py
# Description  : Repository for CRUD operations on the audit_logs table.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from uuid import UUID

import orjson
from sqlalchemy import text

from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.base_repository import BaseRepository


class AuditRepository(BaseRepository):
    """
    Repository for the audit_logs table.
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
        audit_id: UUID,
        capability_id: UUID,
        action: str,
        performed_by: str,
        remarks: str,
        payload: dict,
    ) -> None:
        """
        Create an audit log.
        """

        session = self.session()

        try:

            session.execute(
                text(
                    """
                    INSERT INTO audit_logs
                    (
                        id,
                        capability_id,
                        action,
                        performed_by,
                        remarks,
                        payload
                    )
                    VALUES
                    (
                        :id,
                        :capability_id,
                        :action,
                        :performed_by,
                        :remarks,
                        CAST(:payload AS JSONB)
                    )
                    """
                ),
                {
                    "id": str(audit_id),
                    "capability_id": str(capability_id),
                    "action": action,
                    "performed_by": performed_by,
                    "remarks": remarks,
                    "payload": orjson.dumps(payload).decode(),
                },
            )

            self.commit(session)

        except Exception:

            self.rollback(session)

            raise

        finally:

            self.close(session)

    def get_by_capability(self, capability_id: UUID):
        """
        Return audit logs for a capability.
        """

        session = self.session()

        try:

            result = session.execute(
                text(
                    """
                    SELECT *
                    FROM audit_logs
                    WHERE capability_id = :capability_id
                    ORDER BY created_at DESC
                    """
                ),
                {
                    "capability_id": str(capability_id),
                },
            )

            return result.mappings().all()

        finally:

            self.close(session)

    def delete(self, audit_id: UUID) -> None:
        """
        Delete an audit log.
        """

        session = self.session()

        try:

            session.execute(
                text(
                    """
                    DELETE
                    FROM audit_logs
                    WHERE id = :id
                    """
                ),
                {
                    "id": str(audit_id),
                },
            )

            self.commit(session)

        except Exception:

            self.rollback(session)

            raise

        finally:

            self.close(session)