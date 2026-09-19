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
from skillgenie.core.feedback import SkillFeedbackService
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
from skillgenie.database.repositories.outcome_repository import OutcomeRepository
from skillgenie.database.repositories.recommendation_repository import (
    RecommendationRepository,
)
from skillgenie.database.repositories.trace_repository import TraceRepository
from skillgenie.exceptions import CapabilityNotFoundError
from skillgenie.governance.manager import GovernanceManager
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

        # Outcome repository (feedback loop)
        self.outcomes = OutcomeRepository(self.database)

        # Governance (privacy + secrets vault)
        self.governance = GovernanceManager(
            self.config,
            vault_path=self.config.get(
                "governance.vault.path",
                "config/secrets",
            ),
        )

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

        # Validation harness
        from skillgenie.core.validator import SkillValidator

        self.validator = SkillValidator(self.config)

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
            outcome_repository=self.outcomes,
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

        self.feedback = SkillFeedbackService(
            config=self.config,
            database=self.database,
            skill_repository=self.capabilities,
            outcome_repository=self.outcomes,
            audit_repository=self.audit,
        )

        self.graph_builder = SkillGraphBuilder(
            config=self.config,
            store=self.store,
            scorer=self.scorer,
        )

        from skillgenie.planning.composer import SkillComposer

        self.composer = SkillComposer(
            config=self.config,
            store=self.store,
            recommender=self.recommender,
        )

        # Autonomous drift remediation
        from skillgenie.core.remediator import SkillRemediator

        self.remediator = SkillRemediator(
            config=self.config,
            store=self.store,
            feedback=self.feedback,
            validator=self.validator,
            lifecycle=self.lifecycle,
            audit_repository=self.audit,
        )

        # Gap & novelty discovery
        from skillgenie.core.gaps import SkillGapAnalyzer

        self.gap_analyzer = SkillGapAnalyzer(
            config=self.config,
            store=self.store,
            trace_repository=self.traces,
        )

        # Provenance & explainability
        from skillgenie.core.provenance import SkillProvenance

        self.provenance = SkillProvenance(
            config=self.config,
            store=self.store,
            audit_repository=self.audit,
            outcome_repository=self.outcomes,
            trace_repository=self.traces,
        )

        # SkillGenie Arena
        from skillgenie.arena import SkillGenieArena

        self.arena = SkillGenieArena(
            config=self.config,
            leaderboard_path=self.config.get(
                "arena.leaderboard_path",
                "arena.leaderboard.json",
            ),
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

    def record_outcome(
        self,
        capability_id: UUID,
        outcome: str = "SUCCESS",
        recommendation_id: UUID | None = None,
        latency_ms: float = 0.0,
        rating: float | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        """
        Record a real-world outcome for a recommendation.
        """

        return self.feedback.record_outcome(
            capability_id=capability_id,
            outcome=outcome,
            recommendation_id=recommendation_id,
            latency_ms=latency_ms,
            rating=rating,
            metadata=metadata,
        )

    def detect_drift(self, capability_id: UUID) -> dict[str, Any] | None:
        """
        Detect performance drift for a skill.
        """

        return self.feedback.detect_drift(capability_id)

    def recent_failures(
        self, capability_id: UUID, limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        Return recent failed outcomes for a skill.
        """

        return self.feedback.recent_failures(capability_id, limit=limit)

    def health_explanation(self, skill_id: UUID) -> dict[str, Any]:
        """
        Explainable health breakdown for a skill.
        """

        skill = self.store.get(skill_id)

        if skill is None:
            raise CapabilityNotFoundError(
                f"Skill '{skill_id}' does not exist."
            )

        return self.feedback.health_explanation(skill)

    def validate_skill(self, skill_id: UUID) -> dict[str, Any]:
        """
        Validate a skill and return a readiness report.
        """

        skill = self.store.get(skill_id)

        if skill is None:
            raise CapabilityNotFoundError(
                f"Skill '{skill_id}' does not exist."
            )

        return self.validator.validate(skill)

    def remediate(
        self,
        skill_id: UUID,
        mode: str = "auto",
        force: bool = False,
        actor: str = "system",
    ) -> dict[str, Any]:
        """
        Assess a skill and apply autonomous remediation actions.
        """

        skill = self.store.get(skill_id)

        if skill is None:
            raise CapabilityNotFoundError(
                f"Skill '{skill_id}' does not exist."
            )

        return self.remediator.remediate(
            skill_id=skill_id,
            mode=mode,
            force=force,
            actor=actor,
        )

    def analyze_gaps(self) -> dict[str, Any]:
        """
        Discover registry coverage gaps and novelty opportunities.
        """

        return self.gap_analyzer.analyze()

    def export_skill(
        self,
        skill_id: UUID,
        fmt: str = "mcp",
        output_dir: str | None = None,
    ) -> Any:
        """
        Export a skill in the requested format, optionally publishing it to a
        marketplace catalog directory.
        """

        from skillgenie.marketplace import MarketplaceIndex, export_skill

        skill = self.store.get(skill_id)

        if skill is None:
            raise CapabilityNotFoundError(
                f"Skill '{skill_id}' does not exist."
            )

        if output_dir:
            return MarketplaceIndex(output_dir).publish(skill, fmt=fmt)

        return export_skill(skill, fmt)

    def skill_provenance(self, skill_id: UUID) -> dict[str, Any]:
        """
        Provenance dossier and explainability narrative for a skill.
        """

        skill = self.store.get(skill_id)

        if skill is None:
            raise CapabilityNotFoundError(
                f"Skill '{skill_id}' does not exist."
            )

        return self.provenance.provenance(skill_id)

    def arena_battle(
        self,
        task: str,
        skill_a: UUID,
        skill_b: UUID,
        rounds: int = 5,
        failure_rate: float = 0.30,
    ) -> dict[str, Any]:
        """
        Run a head-to-head skill battle in the arena.
        """

        skill_a_model = self.store.get(skill_a)
        skill_b_model = self.store.get(skill_b)

        if skill_a_model is None:
            raise CapabilityNotFoundError(
                f"Skill '{skill_a}' does not exist."
            )

        if skill_b_model is None:
            raise CapabilityNotFoundError(
                f"Skill '{skill_b}' does not exist."
            )

        return self.arena.battle(
            skill_a=skill_a_model,
            skill_b=skill_b_model,
            task=task,
            rounds=rounds,
            failure_rate=failure_rate,
        )

    def arena_leaderboard(
        self,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Arena ELO leaderboard.
        """

        return self.arena.leaderboard(limit=limit)

    def governance_report(self) -> dict[str, Any]:
        """
        Governance and privacy compliance summary.
        """

        return self.governance.report()

    def redact(self, value: Any) -> Any:
        """
        Redact PII from a value under governance policy.
        """

        return self.governance.redact(value)

    def compose(
        self,
        task: str,
        top_k: int = 3,
        status: str | None = None,
    ) -> dict[str, Any]:
        """
        Compose a multi-skill plan for a composite task.
        """

        if not task or not task.strip():
            raise ValueError("A non-empty task is required.")

        plan = self.composer.compose(
            task=task,
            top_k=top_k,
            status=status,
        )

        return plan.to_dict()

    def execute_plan(
        self,
        task: str,
        top_k: int = 3,
        status: str | None = None,
        learn: bool = False,
    ) -> dict[str, Any]:
        """
        Plan, execute and optionally learn a composite task.
        """

        plan = self.composer.compose(
            task=task,
            top_k=top_k,
            status=status,
        )

        result = self.composer.execute(plan)

        payload = {
            "plan": plan.to_dict(),
            "result": result.to_dict(),
            "learned": None,
        }

        if learn:
            composite = self.composer.learn(result)
            payload["learned"] = (
                {
                    "id": str(composite.id),
                    "name": composite.name,
                    "status": composite.status.value,
                }
                if composite
                else None
            )

        return payload

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