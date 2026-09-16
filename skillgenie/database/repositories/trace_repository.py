# ============================================================================
# Project      : SkillGenie
# File         : trace_repository.py
# Description  : Repository for CRUD operations on the traces table.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from typing import Any
from uuid import UUID

import orjson
from sqlalchemy import text

from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.base_repository import BaseRepository


class TraceRepository(BaseRepository):
    """
    Repository for the traces table.
    """

    _UPDATABLE_COLUMNS = {
        "trace_name",
        "agent_framework",
        "task_description",
        "execution_status",
        "execution_time_ms",
        "trace",
        "metadata",
    }

    def __init__(self, database: DatabaseManager):
        """
        Initialize repository.

        Args:
            database: Database manager.
        """

        super().__init__(database)

    def create(
        self,
        trace_id: UUID,
        trace_name: str,
        agent_framework: str,
        task_description: str,
        execution_status: str,
        execution_time_ms: float,
        trace: dict,
        metadata: dict,
    ) -> None:
        """
        Create a new execution trace.
        """

        session = self.session()

        try:

            session.execute(
                text(
                    """
                    INSERT INTO traces
                    (
                        id,
                        trace_name,
                        agent_framework,
                        task_description,
                        execution_status,
                        execution_time_ms,
                        trace,
                        metadata
                    )
                    VALUES
                    (
                        :id,
                        :trace_name,
                        :agent_framework,
                        :task_description,
                        :execution_status,
                        :execution_time_ms,
                        CAST(:trace AS JSONB),
                        CAST(:metadata AS JSONB)
                    )
                    """
                ),
                {
                    "id": str(trace_id),
                    "trace_name": trace_name,
                    "agent_framework": agent_framework,
                    "task_description": task_description,
                    "execution_status": execution_status,
                    "execution_time_ms": execution_time_ms,
                    "trace": text.__module__ and __import__("orjson").dumps(trace).decode(),
                    "metadata": text.__module__ and __import__("orjson").dumps(metadata).decode(),
                },
            )

            self.commit(session)

        except Exception:

            self.rollback(session)

            raise

        finally:

            self.close(session)

    def get_by_id(self, trace_id: UUID):
        """
        Get trace by id.
        """

        session = self.session()

        try:

            result = session.execute(
                text(
                    """
                    SELECT *
                    FROM traces
                    WHERE id = :id
                    """
                ),
                {
                    "id": str(trace_id),
                },
            )

            return result.mappings().first()

        finally:

            self.close(session)

    def list(self):
        """
        Return all traces.
        """

        session = self.session()

        try:

            result = session.execute(
                text(
                    """
                    SELECT *
                    FROM traces
                    ORDER BY created_at DESC
                    """
                )
            )

            return result.mappings().all()

        finally:

            self.close(session)

    def delete(self, trace_id: UUID) -> None:
        """
        Delete trace.
        """

        session = self.session()

        try:

            session.execute(
                text(
                    """
                    DELETE
                    FROM traces
                    WHERE id = :id
                    """
                ),
                {
                    "id": str(trace_id),
                },
            )

            self.commit(session)

        except Exception:

            self.rollback(session)

            raise

        finally:

            self.close(session)

    def update(
        self,
        trace_id: UUID,
        **fields: Any,
    ) -> None:
        """
        Update one or more columns on an existing trace.

        Args:
            trace_id: Trace identifier.
            **fields: Column values keyed by column name.
        """

        unsupported = set(fields) - self._UPDATABLE_COLUMNS

        if unsupported:
            raise ValueError(
                f"Unsupported columns: {sorted(unsupported)}"
            )

        if not fields:
            return

        assignments = ", ".join(
            f"{column} = :{column}"
            for column in fields
        )

        params: dict[str, Any] = {
            "id": str(trace_id),
        }

        for column, value in fields.items():

            if isinstance(value, (dict, list)) and column in {
                "trace",
                "metadata",
            }:
                params[column] = orjson.dumps(value).decode()
            else:
                params[column] = value

        session = self.session()

        try:

            session.execute(
                text(
                    f"""
                    UPDATE traces
                    SET {assignments}
                    WHERE id = :id
                    """
                ),
                params,
            )

            self.commit(session)

        except Exception:

            self.rollback(session)

            raise

        finally:

            self.close(session)