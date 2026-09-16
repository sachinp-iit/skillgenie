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
from skillgenie.constants import (
    RECOMMENDATION_CONFIDENCE_WEIGHT,
    RECOMMENDATION_QUALITY_WEIGHT,
    RECOMMENDATION_SIMILARITY_WEIGHT,
)
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
        Calculate confidence score based on artifact completeness.

        Weighted components:
            - Workflow with ordered steps (0.30)
            - Tools metadata (0.20)
            - Prompts metadata (0.20)
            - Input / output metadata (0.20)
            - Execution evidence via usage count (0.10)
        """

        self._logger.debug(
            "Calculating confidence score."
        )

        score = 0.0

        workflow = getattr(skill, "workflow", {}) or {}
        metadata = getattr(skill, "metadata", {}) or {}
        usage_count = getattr(skill, "usage_count", 0) or 0

        if workflow.get("steps"):
            score += 0.30

        if metadata.get("tools"):
            score += 0.20

        if metadata.get("prompts"):
            score += 0.20

        if metadata.get("input_output"):
            score += 0.20

        if usage_count > 0:
            score += 0.10

        return round(min(score, 1.0), 3)

    def quality_score(self, skill: Any) -> float:
        """
        Calculate quality score based on information depth and structure.

        Weighted components:
            - Documentation depth from description (0.25)
            - Category specificity (0.15)
            - Workflow structure (0.30)
            - Relationship graph connectivity (0.15)
            - Artifact coverage (0.15)
        """

        self._logger.debug(
            "Calculating quality score."
        )

        description = getattr(skill, "description", "") or ""
        category = getattr(skill, "category", "") or ""
        workflow = getattr(skill, "workflow", {}) or {}
        relationship_graph = (
            getattr(skill, "relationship_graph", {}) or {}
        )

        documentation = self._normalize(len(description.strip()), 50)
        category_score = (
            1.0
            if category and category.lower() != "general"
            else 0.4
            if category
            else 0.0
        )
        workflow_score = self._normalize(
            len(workflow.get("steps", [])),
            2,
        )
        graph_score = 0.0

        for edges in relationship_graph.values():
            if edges:
                graph_score = 1.0
                break

        artifact_coverage = 0.0

        if workflow.get("steps"):
            artifact_coverage += 0.33

        if workflow.get("metadata") or getattr(skill, "metadata", {}):
            artifact_coverage += 0.33

        description_keywords = {
            "step",
            "tool",
            "use",
            "generate",
            "extract",
        }

        if any(
            keyword in description.lower()
            for keyword in description_keywords
        ):
            artifact_coverage += 0.34

        score = (
            0.25 * documentation
            + 0.15 * category_score
            + 0.30 * workflow_score
            + 0.15 * graph_score
            + 0.15 * min(artifact_coverage, 1.0)
        )

        return round(min(score, 1.0), 3)

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

        return round(
            dot_product / (source_norm * target_norm),
            6,
        )

    def ranking_score(
        self,
        similarity: float,
        confidence: float,
        quality: float,
    ) -> float:
        """
        Combine similarity, confidence and quality into a single ranking score.

        Weights come from constants and sum to 1.0.
        """

        score = (
            RECOMMENDATION_SIMILARITY_WEIGHT * similarity
            + RECOMMENDATION_CONFIDENCE_WEIGHT * confidence
            + RECOMMENDATION_QUALITY_WEIGHT * quality
        )

        return round(min(max(score, 0.0), 1.0), 6)

    def overall_score(self, skill: Any) -> float:
        """
        Calculate overall score as a weighted blend of confidence, quality and
        success rate.
        """

        self._logger.debug(
            "Calculating overall score."
        )

        confidence = self.confidence_score(skill)
        quality = self.quality_score(skill)
        success_rate = min(
            float(getattr(skill, "success_rate", 0.0) or 0.0),
            1.0,
        )

        return round(
            0.40 * confidence
            + 0.40 * quality
            + 0.20 * success_rate,
            3,
        )

    def _normalize(self, value: float, ideal: float) -> float:
        """
        Normalize a value against an ideal target, capped at 1.0.
        """

        if ideal <= 0:
            return 0.0

        return min(value / ideal, 1.0)