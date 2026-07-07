# ============================================================================
# Project      : SkillGenie
# File         : evaluator.py
# Description  : Evaluates generated skills before they become available for
#                recommendation and execution.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from skillgenie.config import Config
from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.capability_repository import (
    CapabilityRepository,
)
from skillgenie.database.repositories.metrics_repository import (
    MetricsRepository,
)
from skillgenie.models.capability import Capability
from skillgenie.utils.logger import Logger


class SkillEvaluator:
    """
    Evaluates generated skills.
    """

    def __init__(
        self,
        config: Config,
        database: DatabaseManager,
    ):
        """
        Initialize Skill Evaluator.

        Args:
            config: SkillGenie configuration.
            database: Database manager.
        """

        # Store dependencies
        self._config = config
        self._database = database

        # Initialize logger
        self._logger = Logger(config).log

        # Initialize repositories
        self._skill_repository = CapabilityRepository(
            database
        )

        self._metrics_repository = MetricsRepository(
            database
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

        # Calculate confidence score
        skill.confidence_score = (
            self._calculate_confidence(skill)
        )

        # Calculate quality score
        skill.quality_score = (
            self._calculate_quality(skill)
        )

        # Calculate success rate
        skill.success_rate = (
            self._calculate_success_rate(skill)
        )

        # Determine lifecycle status
        skill.status = (
            self._determine_status(skill)
        )

        # Persist evaluation metrics
        self._save_metrics(skill)

        self._logger.info(
            f"Evaluation completed for '{skill.name}'."
        )

        return skill
    
    def _calculate_confidence(
        self,
        skill: Capability,
    ) -> float:
        """
        Calculate confidence score.
        """

        self._logger.debug(
            f"Calculating confidence score for '{skill.name}'."
        )

        score = 0.0

        if skill.workflow:
            score += 0.30

        if skill.metadata.get("tools"):
            score += 0.20

        if skill.metadata.get("prompts"):
            score += 0.20

        if skill.metadata.get("input_output"):
            score += 0.20

        if skill.metadata:
            score += 0.10

        return round(score, 3)

    def _calculate_quality(
        self,
        skill: Capability,
    ) -> float:
        """
        Calculate quality score.
        """

        self._logger.debug(
            f"Calculating quality score for '{skill.name}'."
        )

        score = 0.0

        if skill.description:
            score += 0.20

        if skill.category:
            score += 0.20

        if skill.workflow:
            score += 0.40

        if skill.relationship_graph:
            score += 0.20

        return round(score, 3)

    def _calculate_success_rate(
        self,
        skill: Capability,
    ) -> float:
        """
        Calculate initial success rate.
        """

        self._logger.debug(
            f"Calculating success rate for '{skill.name}'."
        )

        return 1.0

    def _determine_status(
        self,
        skill: Capability,
    ):
        """
        Determine skill lifecycle status.
        """

        self._logger.debug(
            f"Determining lifecycle state for '{skill.name}'."
        )

        return skill.status

    def _save_metrics(
        self,
        skill: Capability,
    ) -> None:
        """
        Persist evaluation metrics.
        """

        self._logger.debug(
            f"Persisting metrics for '{skill.name}'."
        )

        # Metrics repository implementation will be
        # integrated after the scoring engine is completed.
        
    def approve(
        self,
        skill: Capability,
    ) -> Capability:
        """
        Approve a skill.

        Args:
            skill: Skill to approve.

        Returns:
            Updated skill.
        """

        self._logger.info(
            f"Approving skill '{skill.name}'."
        )

        skill.status = self._determine_status(skill)

        self._skill_repository.update(
            capability_id=skill.id,
            status=skill.status.value,
        )

        return skill

    def reject(
        self,
        skill: Capability,
        reason: str,
    ) -> Capability:
        """
        Reject a generated skill.

        Args:
            skill: Skill to reject.
            reason: Rejection reason.

        Returns:
            Updated skill.
        """

        self._logger.warning(
            f"Rejecting skill '{skill.name}'."
        )

        skill.metadata["rejection_reason"] = reason

        self._skill_repository.update(
            capability_id=skill.id,
            metadata=skill.metadata,
        )

        return skill

    def publish(
        self,
        skill: Capability,
    ) -> Capability:
        """
        Publish a skill.

        Args:
            skill: Skill to publish.

        Returns:
            Published skill.
        """

        self._logger.info(
            f"Publishing skill '{skill.name}'."
        )

        self._skill_repository.update(
            capability_id=skill.id,
            status=skill.status.value,
        )

        return skill

    def reevaluate(
        self,
        skill: Capability,
    ) -> Capability:
        """
        Re-evaluate an existing skill.

        Args:
            skill: Existing skill.

        Returns:
            Updated skill.
        """

        self._logger.info(
            f"Re-evaluating skill '{skill.name}'."
        )

        return self.evaluate(skill)