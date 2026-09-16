# ============================================================================
# Project      : SkillGenie
# File         : execution_repository.py
# Description  : Repository for CRUD operations on the executions table.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from datetime import datetime
from typing import Any
from uuid import UUID

import orjson
from sqlalchemy import text

from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.base_repository import BaseRepository


class ExecutionRepository(BaseRepository):
    """
    Repository for the executions table.
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
        execution_id: UUID,
        capability_id: UUID,
        trace_id: UUID | None,
        task_name: str,
        execution_status: str,
        started_at: datetime,
        completed_at: datetime | None,
        execution_time_ms: float,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        error_message: str | None,
        metadata: dict[str, Any],
    ) -> None:
        """
        Create a capability execution record.
        """

        session = self.session()

        try:

            session.execute(
                text(
                    """
                    INSERT INTO executions
                    (
                        id,
                        capability_id,
                        trace_id,
                        task_name,
                        execution_status,
                        started_at,
                        completed_at,
                        execution_time_ms,
                        input_data,
                        output_data,
                        error_message,
                        metadata
                    )
                    VALUES
                    (
                        :id,
                        :capability_id,
                        :trace_id,
                        :task_name,
                        :execution_status,
                        :started_at,
                        :completed_at,
                        :execution_time_ms,
                        CAST(:input_data AS JSONB),
                        CAST(:output_data AS JSONB),
                        :error_message,
                        CAST(:metadata AS JSONB)
                    )
                    """
                ),
                {
                    "id": str(execution_id),
                    "capability_id": str(capability_id),
                    "trace_id": str(trace_id) if trace_id else None,
                    "task_name": task_name,
                    "execution_status": execution_status,
                    "started_at": started_at,
                    "completed_at": completed_at,
                    "execution_time_ms": execution_time_ms,
                    "input_data": orjson.dumps(input_data).decode(),
                    "output_data": orjson.dumps(output_data).decode(),
                    "error_message": error_message,
                    "metadata": orjson.dumps(metadata).decode(),
                },
            )

            self.commit(session)

        except Exception:

            self.rollback(session)

            raise

        finally:

            self.close(session)

    def get_by_id(self, execution_id: UUID):
        """
        Get an execution by id.
        """

        session = self.session()

        try:

            result = session.execute(
                text(
                    """
                    SELECT *
                    FROM executions
                    WHERE id = :id
                    """
                ),
                {
                    "id": str(execution_id),
                },
            )

            return result.mappings().first()

        finally:

            self.close(session)

    def get_by_capability(self, capability_id: UUID):
        """
        Return executions for a capability.
        """

        session = self.session()

        try:

            result = session.execute(
                text(
                    """
                    SELECT *
                    FROM executions
                    WHERE capability_id = :capability_id
                    ORDER BY started_at DESC
                    """
                ),
                {
                    "capability_id": str(capability_id),
                },
            )

            return result.mappings().all()

        finally:

            self.close(session)

    def list(self):
        """
        Return all executions.
        """

        session = self.session()

        try:

            result = session.execute(
                text(
                    """
                    SELECT *
                    FROM executions
                    ORDER BY started_at DESC
                    """
                )
            )

            return result.mappings().all()

        finally:

            self.close(session)

    def delete(self, execution_id: UUID) -> None:
        """
        Delete an execution.
        """

        session = self.session()

        try:

            session.execute(
                text(
                    """
                    DELETE
                    FROM executions
                    WHERE id = :id
                    """
                ),
                {
                    "id": str(execution_id),
                },
            )

            self.commit(session)

        except Exception:

            self.rollback(session)

            raise

        finally:

            self.close(session)