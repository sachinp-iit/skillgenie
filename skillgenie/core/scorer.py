# ============================================================================
# Project      : SkillGenie
# File         : scorer.py
# Description  : Computes confidence, quality, similarity and overall score
#                for learned skills.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from math import sqrt
from typing import Any

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

        self._config = config
        self._logger = Logger(config).log

    def confidence_score(self, skill: Any) -> float:
        """
        Calculate confidence score.
        """

        self._logger.debug(
            "Calculating confidence score."
        )

        return 0.0

    def quality_score(self, skill: Any) -> float:
        """
        Calculate quality score.
        """

        self._logger.debug(
            "Calculating quality score."
        )

        return 0.0

    def similarity_score(
        self,
        source_embedding: list[float],
        target_embedding: list[float],
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        """

        self._logger.debug(
            "Calculating similarity score."
        )

        if not source_embedding or not target_embedding:
            return 0.0

        if len(source_embedding) != len(target_embedding):
            raise ValueError(
                "Embedding dimensions must match."
            )

        dot_product = sum(
            x * y
            for x, y in zip(
                source_embedding,
                target_embedding,
            )
        )

        source_norm = sqrt(
            sum(x * x for x in source_embedding)
        )

        target_norm = sqrt(
            sum(y * y for y in target_embedding)
        )

        if source_norm == 0.0 or target_norm == 0.0:
            return 0.0

        return dot_product / (source_norm * target_norm)

    def overall_score(self, skill: Any) -> float:
        """
        Calculate overall score.
        """

        self._logger.debug(
            "Calculating overall score."
        )

        confidence = self.confidence_score(skill)
        quality = self.quality_score(skill)

        return (confidence + quality) / 2.0