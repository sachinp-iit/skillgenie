# ============================================================================
# Project      : SkillGenie
# File         : evaluator.py
# Description  : Evaluates generated skills before they become available for
#                recommendation and execution.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from skillgenie.config import Config
from skillgenie.constants import SkillStatus
from skillgenie.core.health import SkillHealthEngine
from skillgenie.core.lifecycle import SkillLifecycle
from skillgenie.core.scorer import SkillScorer
from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.audit_repository import AuditRepository
from skillgenie.database.repositories.capability_repository import (
    CapabilityRepository,
)
from skillgenie.database.repositories.execution_repository import (
    ExecutionRepository,
)
from skillgenie.database.repositories.metrics_repository import (
    MetricsRepository,
)
from skillgenie.models.capability import Capability
from skillgenie.utils.logger import Logger

# Ordering used to prevent demotion during evaluation.
_STATUS_RANK = {
    SkillStatus.DRAFT: 0,
    SkillStatus.CANDIDATE: 1,
    SkillStatus.APPROVED: 2,
    SkillStatus.PUBLISHED: 3,
    SkillStatus.DEPRECATED: 4,
    SkillStatus.ARCHIVED: 5,
}


class SkillEvaluator:
    """
    Evaluates generated skills.
    """

    def __init__(
        self,
        config: Config,
        database: DatabaseManager,
        skill_repository: CapabilityRepository | None = None,
        metrics_repository: MetricsRepository | None = None,
        audit_repository: AuditRepository | None = None,
        execution_repository: ExecutionRepository | None = None,
        scorer: SkillScorer | None = None,
    ):
        """
        Initialize Skill Evaluator.

        Args:
            config: SkillGenie configuration.
            database: Database manager.
            skill_repository: Optional repository override.
            metrics_repository: Optional repository override.
            audit_repository: Optional repository override.
            execution_repository: Optional repository override.
            scorer: Optional scoring engine override.
        """

        self._config = config
        self._database = database

        self._logger = Logger(config).log

        self._skill_repository = (
            skill_repository or CapabilityRepository(database)
        )

        self._metrics_repository = (
            metrics_repository or MetricsRepository(database)
        )

        self._audit_repository = (
            audit_repository or AuditRepository(database)
        )

        self._execution_repository = (
            execution_repository or ExecutionRepository(database)
        )

        self._scorer = scorer or SkillScorer(config)

        self._health_engine = SkillHealthEngine(config)

        self._lifecycle = SkillLifecycle(
            config=config,
            database=database,
            skill_repository=self._skill_repository,
            audit_repository=self._audit_repository,
        )

    def evaluate(
        self,
        skill: Capability,
    ) -> Capability:
        """
        Evaluate a generated skill.

        Args:
            skill: Generated skill.

        Returns:
            Evaluated skill.
        """

        self._logger.info(
            f"Evaluating skill '{skill.name}'."
        )

        skill.confidence_score = self._scorer.confidence_score(skill)
        skill.quality_score = self._scorer.quality_score(skill)
        skill.success_rate = self._calculate_success_rate(skill)
        skill.health = self._health_engine.health(skill)

        self._persist_scores(skill)

        self._save_metrics(skill)

        target_status = self._determine_status(skill)

        self._promote(skill=skill, target=target_status)

        if target_status is not None:
            skill.status = target_status

        self._audit(
            capability_id=skill.id,
            action="EVALUATED",
            remarks=(
                f"confidence={skill.confidence_score}, "
                f"quality={skill.quality_score}, "
                f"success_rate={skill.success_rate}"
            ),
            payload={
                "confidence_score": skill.confidence_score,
                "quality_score": skill.quality_score,
                "success_rate": skill.success_rate,
                "health": skill.health.value,
            },
        )

        self._logger.info(
            f"Evaluation completed for '{skill.name}'."
        )

        return skill

    def _persist_scores(self, skill: Capability) -> None:
        """
        Persist computed scores to the capability row.
        """

        self._skill_repository.update(
            capability_id=skill.id,
            confidence_score=skill.confidence_score,
            quality_score=skill.quality_score,
            success_rate=skill.success_rate,
            health=skill.health.value,
            updated_at=datetime.utcnow(),
        )

    def _calculate_success_rate(
        self,
        skill: Capability,
    ) -> float:
        """
        Compute success rate from recorded executions.

        Freshly-created skills default to 1.0 because they originate from a
        successful execution trace.
        """

        executions = self._execution_repository.get_by_capability(
            skill.id
        )

        if not executions:
            return 1.0

        successful = 0

        for execution in executions:
            status = execution.get("execution_status", "")

            if status == "SUCCESS":
                successful += 1

        if len(executions) == 0:
            return 1.0

        return round(successful / len(executions), 3)

    def _determine_status(
        self,
        skill: Capability,
    ) -> SkillStatus | None:
        """
        Determine the lifecycle status for the evaluated skill.

        Returns None when no change is required.
        """

        current = skill.status

        if self._config.get_bool("learning.auto_approval", False):
            auto_approve_threshold = self._config.get_float(
                "similarity.auto_approval_threshold",
                0.95,
            )

            if skill.confidence_score >= auto_approve_threshold:
                return (
                    SkillStatus.PUBLISHED
                    if self._config.get_bool(
                        "learning.auto_publish",
                        False,
                    )
                    else SkillStatus.APPROVED
                )

        candidate_threshold = self._config.get_float(
            "learning.candidate_threshold",
            0.55,
        )

        if skill.confidence_score >= candidate_threshold:
            return SkillStatus.CANDIDATE

        return current

    def _promote(
        self,
        skill: Capability,
        target: SkillStatus | None,
    ) -> None:
        """
        Promote a skill through lifecycle transitions until the target status
        is reached. Never demotes.
        """

        if target is None or target == skill.status:
            return

        if _STATUS_RANK[target] <= _STATUS_RANK[skill.status]:
            return

        steps: list[SkillStatus] = []

        if skill.status == SkillStatus.DRAFT and target != SkillStatus.DRAFT:
            steps.append(SkillStatus.CANDIDATE)

        if (
            skill.status != SkillStatus.APPROVED
            and _STATUS_RANK[target] >= _STATUS_RANK[SkillStatus.APPROVED]
        ):
            steps.append(SkillStatus.APPROVED)

        if target == SkillStatus.PUBLISHED:
            steps.append(SkillStatus.PUBLISHED)

        for step in steps:
            self._lifecycle.transition(str(skill.id), step)

    def approve(
        self,
        skill: Capability,
    ) -> Capability:
        """
        Approve a skill.
        """

        self._logger.info(
            f"Approving skill '{skill.name}'."
        )

        self._lifecycle.approve(str(skill.id))

        skill.status = SkillStatus.APPROVED

        return skill

    def reject(
        self,
        skill: Capability,
        reason: str,
    ) -> Capability:
        """
        Reject a generated skill.
        """

        self._logger.warning(
            f"Rejecting skill '{skill.name}': {reason}"
        )

        self._lifecycle.reject(str(skill.id), reason)

        skill.status = SkillStatus.DRAFT
        skill.metadata["rejection_reason"] = reason

        return skill

    def publish(
        self,
        skill: Capability,
    ) -> Capability:
        """
        Publish a skill.
        """

        self._logger.info(
            f"Publishing skill '{skill.name}'."
        )

        self._lifecycle.publish(str(skill.id))

        skill.status = SkillStatus.PUBLISHED

        return skill

    def reevaluate(
        self,
        skill: Capability,
    ) -> Capability:
        """
        Re-evaluate an existing skill.
        """

        self._logger.info(
            f"Re-evaluating skill '{skill.name}'."
        )

        return self.evaluate(skill)

    def _save_metrics(
        self,
        skill: Capability,
    ) -> None:
        """
        Persist evaluation metrics.
        """

        self._metrics_repository.create(
            metric_id=uuid4(),
            capability_id=skill.id,
            confidence_score=skill.confidence_score,
            quality_score=skill.quality_score,
            success_rate=skill.success_rate,
            avg_latency_ms=skill.avg_latency_ms,
            usage_count=skill.usage_count,
        )

    def _audit(
        self,
        capability_id: UUID,
        action: str,
        remarks: str = "",
        payload: dict[str, Any] | None = None,
    ) -> None:
        """
        Write an audit entry.
        """

        self._audit_repository.create(
            audit_id=uuid4(),
            capability_id=capability_id,
            action=action,
            performed_by="evaluator",
            remarks=remarks,
            payload=payload or {},
        )