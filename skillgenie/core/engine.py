# ============================================================================
# Project      : SkillGenie
# File         : engine.py
# Description  : Main entry point for the SkillGenie library.
#
#                Initializes configuration, database, repositories, embeddings,
#                and the complete core pipeline (learning, evaluation,
#                recommendation, lifecycle, health and evolution).
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any
from uuid import UUID

from skillgenie.config import Config
from skillgenie.core.evaluator import SkillEvaluator
from skillgenie.core.evolution import SkillEvolutionEngine
from skillgenie.core.execution_service import ExecutionService
from skillgenie.core.health import SkillHealthEngine
from skillgenie.core.learner import SkillLearner
from skillgenie.core.lifecycle import SkillLifecycle
from skillgenie.core.recommender import SkillRecommender
from skillgenie.core.scorer import SkillScorer
from skillgenie.database.bootstrap import bootstrap_database
from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.audit_repository import AuditRepository
from skillgenie.database.repositories.capability_repository import (
    CapabilityRepository,
)
from skillgenie.database.repositories.execution_repository import (
    ExecutionRepository,
)
from skillgenie.database.repositories.metrics_repository import MetricsRepository
from skillgenie.database.repositories.recommendation_repository import (
    RecommendationRepository,
)
from skillgenie.database.repositories.trace_repository import TraceRepository
from skillgenie.embeddings.factory import get_embedding_provider
from skillgenie.graph.relationship_graph import SkillGraphBuilder
from skillgenie.models.capability import Capability
from skillgenie.storage.skill_store import SkillStore
from skillgenie.utils.logger import Logger


class SkillGenie:
    """
    Main SkillGenie Engine.
    """

    def __init__(
        self,
        config_file: str = "config/config.json",
        database: DatabaseManager | None = None,
        embeddings_enabled: bool | None = None,
    ):
        """
        Initialize SkillGenie.

        Args:
            config_file: Path to configuration file.
            database: Optional pre-built database manager (useful for tests).
            embeddings_enabled: Override for `learning` of embeddings.
        """

        self.config = Config(config_file)

        self.logger = Logger(self.config).log

        self.logger.info("Initializing SkillGenie...")

        self.database = (
            database
            if database is not None
            else bootstrap_database(self.config)
        )

        # Capabilities repository
        self.capabilities = CapabilityRepository(self.database)

        # Trace repository
        self.traces = TraceRepository(self.database)

        # Metrics repository
        self.metrics = MetricsRepository(self.database)

        # Audit repository
        self.audit = AuditRepository(self.database)

        # Execution repository
        self.executions = ExecutionRepository(self.database)

        # Recommendation repository
        self.recommendations = RecommendationRepository(self.database)

        # Embedding provider
        should_enable_embeddings = (
            embeddings_enabled
            if embeddings_enabled is not None
            else True
        )

        self.embedding_provider = None

        if should_enable_embeddings:

            try:
                self.embedding_provider = get_embedding_provider(
                    self.config
                )
            except Exception as exc:
                self.logger.warning(
                    f"Embedding provider unavailable: {exc}"
                )

        # Scoring / health
        self.scorer = SkillScorer(self.config)
        self.health_engine = SkillHealthEngine(self.config)

        # Skill storage
        self.store = SkillStore(
            config=self.config,
            repository=self.capabilities,
            embedding_provider=self.embedding_provider,
            scorer=self.scorer,
        )

        # Core pipeline
        self.learner = SkillLearner(
            config=self.config,
            database=self.database,
            trace_repository=self.traces,
            skill_repository=self.capabilities,
            metrics_repository=self.metrics,
            audit_repository=self.audit,
            execution_repository=self.executions,
            embedding_provider=self.embedding_provider,
        )

        self.evaluator = SkillEvaluator(
            config=self.config,
            database=self.database,
            skill_repository=self.capabilities,
            metrics_repository=self.metrics,
            audit_repository=self.audit,
            execution_repository=self.executions,
            scorer=self.scorer,
        )

        self.lifecycle = SkillLifecycle(
            config=self.config,
            database=self.database,
            skill_repository=self.capabilities,
            audit_repository=self.audit,
        )

        self.recommender = SkillRecommender(
            config=self.config,
            database=self.database,
            store=self.store,
            recommendation_repository=self.recommendations,
            trace_repository=self.traces,
        )

        self.evolution = SkillEvolutionEngine(
            config=self.config,
            database=self.database,
            store=self.store,
            lifecycle=self.lifecycle,
            health_engine=self.health_engine,
            skill_repository=self.capabilities,
            audit_repository=self.audit,
        )

        self.execution_service = ExecutionService(
            config=self.config,
            database=self.database,
            skill_repository=self.capabilities,
            execution_repository=self.executions,
            audit_repository=self.audit,
        )

        self.graph_builder = SkillGraphBuilder(
            config=self.config,
            store=self.store,
            scorer=self.scorer,
        )

        self.logger.info("SkillGenie initialized successfully.")

    # ------------------------------------------------------------------
    # Convenience entry points
    # ------------------------------------------------------------------

    def learn(self, trace_id: str) -> Capability:
        """
        Learn a skill from a trace.
        """

        return self.learner.learn(trace_id)

    def learn_all(self) -> list[Capability]:
        """
        Learn skills from all traces.
        """

        return self.learner.learn_all()

    def recommend(
        self,
        query: str,
        top_k: int = 5,
        status: str | None = None,
    ):
        """
        Recommend skills for a task.
        """

        return self.recommender.recommend(
            query=query,
            top_k=top_k,
            status=status,
        )

    def record_execution(
        self,
        capability_id: UUID,
        task_name: str,
        execution_status: str,
        **kwargs: Any,
    ):
        """
        Record a skill execution and refresh runtime metrics.
        """

        return self.execution_service.record(
            capability_id=capability_id,
            task_name=task_name,
            execution_status=execution_status,
            **kwargs,
        )

    def refresh_graphs(self) -> dict:
        """
        Rebuild relationship graphs for all skills.
        """

        return self.graph_builder.refresh(self.store.list())

    def health_overview(self) -> dict[str, Any]:
        """
        Registry-level health summary.
        """

        skills = self.store.list()

        return {
            "total_skills": len(skills),
            "health": self.evolution.health_snapshot(),
            "statuses": self._status_distribution(skills),
        }

    def shutdown(self) -> None:
        """
        Shutdown SkillGenie.
        """

        self.database.close()

        self.logger.info("SkillGenie shutdown completed.")

    def _status_distribution(
        self,
        skills: list[Capability],
    ) -> dict[str, int]:
        """
        Count skills by lifecycle status.
        """

        distribution: dict[str, int] = {}

        for skill in skills:
            status = skill.status.value
            distribution[status] = distribution.get(status, 0) + 1

        return distribution