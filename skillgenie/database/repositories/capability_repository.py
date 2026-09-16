# ============================================================================
# Project      : SkillGenie
# File         : capability_repository.py
# Description  : Repository for CRUD operations on the skills table.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any
from uuid import UUID

import orjson
from sqlalchemy import text

from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.base_repository import BaseRepository


class CapabilityRepository(BaseRepository):
    """
    Repository for the skills table.
    """

    # Skills table columns that may be updated dynamically
    _UPDATABLE_COLUMNS = {
        "name",
        "description",
        "category",
        "version",
        "status",
        "confidence_score",
        "quality_score",
        "success_rate",
        "usage_count",
        "avg_latency_ms",
        "health",
        "embedding",
        "relationship_graph",
        "workflow",
        "metadata",
        "created_from",
        "last_used_at",
        "updated_at",
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

    def update(
        self,
        capability_id: UUID,
        **fields: Any,
    ) -> None:
        """
        Update one or more columns on an existing capability.

        Args:
            capability_id: Skill identifier.
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
            "id": str(capability_id),
        }

        for column, value in fields.items():

            if column == "embedding" and value:
                params[column] = str(list(value))
            elif isinstance(value, (dict, list)) and column in {
                "relationship_graph",
                "workflow",
                "metadata",
                "created_from",
            }:
                params[column] = orjson.dumps(value).decode()
            else:
                params[column] = value

        session = self.session()

        try:

            session.execute(
                text(
                    f"""
                    UPDATE skills
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

    def list(
        self,
        status: str | None = None,
        category: str | None = None,
    ):
        """
        Return capabilities, optionally filtered.

        Args:
            status: Filter by lifecycle status.
            category: Filter by category.
        """

        conditions = []
        params: dict[str, Any] = {}

        if status is not None:
            conditions.append("status = :status")
            params["status"] = status

        if category is not None:
            conditions.append("category = :category")
            params["category"] = category

        where_clause = (
            f" WHERE {' AND '.join(conditions)}"
            if conditions
            else ""
        )

        session = self.session()

        try:

            result = session.execute(
                text(
                    f"""
                    SELECT *
                    FROM skills
                    {where_clause}
                    ORDER BY created_at DESC
                    """
                ),
                params,
            )

            return result.mappings().all()

        finally:

            self.close(session)

    def search_similar(
        self,
        embedding: list[float],
        limit: int = 10,
        threshold: float = 0.0,
        status: str | None = None,
    ):
        """
        Vector similarity search using pgvector cosine distance.

        Args:
            embedding: Query embedding.
            limit: Maximum number of results.
            threshold: Minimum cosine similarity.
            status: Optionally restrict to a lifecycle status.
        """

        status_clause = ""

        if status is not None:
            status_clause = "AND status = :status"

        session = self.session()

        try:

            result = session.execute(
                text(
                    f"""
                    SELECT
                        *,
                        1 - (embedding <=> :embedding) AS similarity
                    FROM skills
                    WHERE embedding IS NOT NULL
                        {status_clause}
                        AND 1 - (embedding <=> :embedding) >= :threshold
                    ORDER BY similarity DESC
                    LIMIT :limit
                    """
                ),
                {
                    "embedding": str(list(embedding)),
                    "threshold": threshold,
                    "limit": limit,
                    **({"status": status} if status else {}),
                },
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