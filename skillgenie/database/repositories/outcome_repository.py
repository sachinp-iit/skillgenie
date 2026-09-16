# ============================================================================
# Project      : SkillGenie
# File         : outcome_repository.py
# Description  : Repository for CRUD operations on the skill_outcomes table.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import orjson
from sqlalchemy import text

from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.base_repository import BaseRepository


class OutcomeRepository(BaseRepository):
    """
    Repository for the skill_outcomes table.
    """

    def __init__(self, database: DatabaseManager):
        super().__init__(database)

    def create(
        self,
        outcome_id: UUID,
        capability_id: UUID,
        recommendation_id: UUID | None,
        outcome: str,
        latency_ms: float,
        rating: float | None,
        metadata: dict[str, Any],
    ) -> None:
        session = self.session()
        try:
            session.execute(
                text(
                    """
                    INSERT INTO skill_outcomes
                    (id, capability_id, recommendation_id, outcome, latency_ms,
                     rating, metadata)
                    VALUES (:id, :capability_id, :recommendation_id, :outcome,
                            :latency_ms, :rating, CAST(:metadata AS JSONB))
                    """
                ),
                {
                    "id": str(outcome_id),
                    "capability_id": str(capability_id),
                    "recommendation_id": str(recommendation_id) if recommendation_id else None,
                    "outcome": outcome,
                    "latency_ms": latency_ms,
                    "rating": rating,
                    "metadata": orjson.dumps(metadata).decode(),
                },
            )
            self.commit(session)
        except Exception:
            self.rollback(session)
            raise
        finally:
            self.close(session)

    def get_by_capability(self, capability_id: UUID):
        session = self.session()
        try:
            result = session.execute(
                text(
                    """
                    SELECT * FROM skill_outcomes
                    WHERE capability_id = :capability_id
                    ORDER BY created_at DESC
                    """
                ),
                {"capability_id": str(capability_id)},
            )
            return result.mappings().all()
        finally:
            self.close(session)

    def get_by_recommendation(self, recommendation_id: UUID):
        session = self.session()
        try:
            result = session.execute(
                text(
                    """
                    SELECT * FROM skill_outcomes
                    WHERE recommendation_id = :recommendation_id
                    ORDER BY created_at DESC
                    """
                ),
                {"recommendation_id": str(recommendation_id)},
            )
            return result.mappings().all()
        finally:
            self.close(session)

    def list(self, limit: int = 50):
        session = self.session()
        try:
            result = session.execute(
                text(
                    """
                    SELECT * FROM skill_outcomes
                    ORDER BY created_at DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
            return result.mappings().all()
        finally:
            self.close(session)

    def count_outcomes(
        self, capability_id: UUID, window_start: datetime | None = None
    ) -> dict[str, int]:
        session = self.session()
        try:
            params: dict[str, Any] = {"capability_id": str(capability_id)}
            where = "WHERE capability_id = :capability_id"
            if window_start:
                where += " AND created_at >= :window_start"
                params["window_start"] = window_start

            result = session.execute(
                text(
                    f"""
                    SELECT
                        COUNT(*) FILTER (WHERE outcome = 'SUCCESS') AS successes,
                        COUNT(*) AS total
                    FROM skill_outcomes
                    {where}
                    """
                ),
                params,
            )
            row = result.mappings().one()
            return {"successes": int(row["successes"]), "total": int(row["total"])}
        finally:
            self.close(session)