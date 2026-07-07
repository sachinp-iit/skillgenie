# ============================================================================
# Project      : SkillGenie
# File         : duplicate_detector.py
# Description  : Detects duplicate and similar skills before inserting them
#                into the SkillGenie registry.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from typing import Any

from skillgenie.database.repositories.capability_repository import (
    CapabilityRepository,
)
from skillgenie.models.capability import Capability


class DuplicateDetector:
    """
    Detect duplicate skills.
    """

    def __init__(
        self,
        repository: CapabilityRepository,
    ):
        """
        Initialize duplicate detector.

        Args:
            repository: Capability repository.
        """

        self._repository = repository

    def exists(
        self,
        skill: Capability,
    ) -> bool:
        """
        Check whether a skill already exists.

        Args:
            skill: Candidate skill.

        Returns:
            True if duplicate exists.
        """

        existing = self._repository.get_by_name(
            skill.name
        )

        return existing is not None

    def find_duplicate(
        self,
        skill: Capability,
    ) -> dict[str, Any] | None:
        """
        Find an existing duplicate skill.

        Args:
            skill: Candidate skill.

        Returns:
            Existing skill if found.
        """

        return self._repository.get_by_name(
            skill.name
        )

    def similarity_score(
        self,
        source_embedding: list[float],
        target_embedding: list[float],
    ) -> float:
        """
        Calculate cosine similarity.

        Args:
            source_embedding: Candidate embedding.
            target_embedding: Existing embedding.

        Returns:
            Similarity score.

        Note:
            Placeholder until embedding engine is implemented.
        """

        # TODO:
        # Replace with pgvector cosine similarity
        # or local embedding similarity.

        return 0.0

    def is_similar(
        self,
        score: float,
        threshold: float = 0.90,
    ) -> bool:
        """
        Determine whether two skills are similar.

        Args:
            score: Similarity score.
            threshold: Minimum similarity threshold.

        Returns:
            True if similar.
        """

        return score >= threshold