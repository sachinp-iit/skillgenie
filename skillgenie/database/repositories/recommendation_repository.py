# ============================================================================
# Project      : SkillGenie
# File         : recommendation_repository.py
# Description  : Repository for CRUD operations on the recommendations table.
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


class RecommendationRepository(BaseRepository):
    """
    Repository for the recommendations table.
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
        recommendation_id: UUID,
        capability_id: UUID,
        recommendation_type: str,
        confidence_score: float,
        similarity_score: float,
        ranking_score: float,
        reason: str,
        metadata: dict[str, Any],
    ) -> None:
        """
        Create a recommendation record.
        """

        session = self.session()

        try:

            session.execute(
                text(
                    """
                    INSERT INTO recommendations
                    (
                        id,
                        capability_id,
                        recommendation_type,
                        confidence_score,
                        similarity_score,
                        ranking_score,
                        reason,
                        metadata
                    )
                    VALUES
                    (
                        :id,
                        :capability_id,
                        :recommendation_type,
                        :confidence_score,
                        :similarity_score,
                        :ranking_score,
                        :reason,
                        CAST(:metadata AS JSONB)
                    )
                    """
                ),
                {
                    "id": str(recommendation_id),
                    "capability_id": str(capability_id),
                    "recommendation_type": recommendation_type,
                    "confidence_score": confidence_score,
                    "similarity_score": similarity_score,
                    "ranking_score": ranking_score,
                    "reason": reason,
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
        """
        Return recommendations for a capability.
        """

        session = self.session()

        try:

            result = session.execute(
                text(
                    """
                    SELECT *
                    FROM recommendations
                    WHERE capability_id = :capability_id
                    ORDER BY recommended_at DESC
                    """
                ),
                {
                    "capability_id": str(capability_id),
                },
            )

            return result.mappings().all()

        finally:

            self.close(session)

    def list(self, limit: int = 50):
        """
        Return the most recent recommendations.
        """

        session = self.session()

        try:

            result = session.execute(
                text(
                    """
                    SELECT *
                    FROM recommendations
                    ORDER BY recommended_at DESC
                    LIMIT :limit
                    """
                ),
                {
                    "limit": limit,
                },
            )

            return result.mappings().all()

        finally:

            self.close(session)

    def delete(self, recommendation_id: UUID) -> None:
        """
        Delete a recommendation.
        """

        session = self.session()

        try:

            session.execute(
                text(
                    """
                    DELETE
                    FROM recommendations
                    WHERE id = :id
                    """
                ),
                {
                    "id": str(recommendation_id),
                },
            )

            self.commit(session)

        except Exception:

            self.rollback(session)

            raise

        finally:

            self.close(session)