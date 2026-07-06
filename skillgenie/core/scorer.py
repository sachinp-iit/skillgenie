# ============================================================================
# Project      : SkillGenie
# File         : scorer.py
# Description  : Computes confidence, quality, similarity and overall score
#                for learned skills.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from skillgenie.config import Config
from skillgenie.utils.logger import Logger


class SkillScorer:
    """
    Computes skill scores.
    """

    def __init__(self, config: Config):
        """
        Initialize Skill Scorer.

        Args:
            config: SkillGenie configuration.
        """

        # Store configuration
        self._config = config

        # Initialize logger
        self._logger = Logger(config).log

    def confidence_score(self, skill) -> float:
        """
        Calculate confidence score.

        Args:
            skill: Skill object.

        Returns:
            Confidence score.
        """

        self._logger.debug(
            f"Calculating confidence score for '{skill.name}'."
        )

        # TODO:
        # Consider:
        # - Successful executions
        # - Failure rate
        # - Number of observations
        # - Stability

        return 0.0

    def quality_score(self, skill) -> float:
        """
        Calculate quality score.

        Args:
            skill: Skill object.

        Returns:
            Quality score.
        """

        self._logger.debug(
            f"Calculating quality score for '{skill.name}'."
        )

        # TODO:
        # Consider:
        # - Output quality
        # - Human feedback
        # - Reusability
        # - Generalization

        return 0.0

    def similarity_score(
        self,
        source_embedding: list[float],
        target_embedding: list[float],
    ) -> float:
        """
        Calculate embedding similarity.

        Args:
            source_embedding: Query embedding.
            target_embedding: Stored embedding.

        Returns:
            Similarity score.
        """

        self._logger.debug(
            "Calculating similarity score."
        )

        # TODO:
        # Cosine similarity

        return 0.0

    def overall_score(self, skill) -> float:
        """
        Calculate overall score.

        Args:
            skill: Skill object.

        Returns:
            Overall score.
        """

        self._logger.debug(
            f"Calculating overall score for '{skill.name}'."
        )

        confidence = self.confidence_score(skill)

        quality = self.quality_score(skill)

        overall = (confidence + quality) / 2

        return overall