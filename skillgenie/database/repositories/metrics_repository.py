# ============================================================================
# Project      : SkillGenie
# File         : metrics_repository.py
# Description  : Repository for CRUD operations on the capability_metrics table.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from uuid import UUID

from sqlalchemy import text

from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.base_repository import BaseRepository


class MetricsRepository(BaseRepository):
    """
    Repository for the capability_metrics table.
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
        metric_id: UUID,
        capability_id: UUID,
        confidence_score: float,
        quality_score: float,
        success_rate: float,
        avg_latency_ms: float,
        usage_count: int,
    ) -> None:
        """
        Create capability metrics.
        """

        session = self.session()

        try:

            session.execute(
                text(
                    """
                    INSERT INTO capability_metrics
                    (
                        id,
                        capability_id,
                        confidence_score,
                        quality_score,
                        success_rate,
                        avg_latency_ms,
                        usage_count
                    )
                    VALUES
                    (
                        :id,
                        :capability_id,
                        :confidence_score,
                        :quality_score,
                        :success_rate,
                        :avg_latency_ms,
                        :usage_count
                    )
                    """
                ),
                {
                    "id": str(metric_id),
                    "capability_id": str(capability_id),
                    "confidence_score": confidence_score,
                    "quality_score": quality_score,
                    "success_rate": success_rate,
                    "avg_latency_ms": avg_latency_ms,
                    "usage_count": usage_count,
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
        Return metrics for a capability.
        """

        session = self.session()

        try:

            result = session.execute(
                text(
                    """
                    SELECT *
                    FROM capability_metrics
                    WHERE capability_id = :capability_id
                    ORDER BY recorded_at DESC
                    """
                ),
                {
                    "capability_id": str(capability_id),
                },
            )

            return result.mappings().all()

        finally:

            self.close(session)

    def delete(self, metric_id: UUID) -> None:
        """
        Delete metric.
        """

        session = self.session()

        try:

            session.execute(
                text(
                    """
                    DELETE
                    FROM capability_metrics
                    WHERE id = :id
                    """
                ),
                {
                    "id": str(metric_id),
                },
            )

            self.commit(session)

        except Exception:

            self.rollback(session)
            raise

        finally:

            self.close(session)