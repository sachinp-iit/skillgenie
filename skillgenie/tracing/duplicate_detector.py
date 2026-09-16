# ============================================================================
# Project      : SkillGenie
# File         : duplicate_detector.py
# Description  : Detects duplicate and similar skills before inserting them
#                into the SkillGenie registry.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any
from uuid import UUID

from skillgenie.config import Config
from skillgenie.core.scorer import SkillScorer
from skillgenie.database.repositories.capability_repository import (
    CapabilityRepository,
)
from skillgenie.models.capability import Capability
from skillgenie.storage.skill_store import SkillStore


class DuplicateDetector:
    """
    Detect duplicate skills.
    """

    def __init__(
        self,
        repository: CapabilityRepository,
        config: Config | None = None,
        scorer: SkillScorer | None = None,
        store: SkillStore | None = None,
    ):
        """
        Initialize duplicate detector.

        Args:
            repository: Capability repository.
            config: Optional configuration for similarity thresholds.
            scorer: Optional scoring engine.
            store: Optional skill store for model conversion.
        """

        self._repository = repository

        self._config = config

        self._store = store or (
            SkillStore(config, repository=repository)
            if config is not None
            else None
        )

        self._scorer = scorer or (
            SkillScorer(config)
            if config is not None
            else None
        )

    def exists(
        self,
        skill: Capability,
    ) -> bool:
        """
        Check whether a skill already exists by exact name.
        """

        return self._repository.get_by_name(skill.name) is not None

    def find_duplicate(
        self,
        skill: Capability,
        threshold: float = 0.85,
    ) -> dict[str, Any] | Capability | None:
        """
        Find an existing duplicate skill.

        1. Exact name match takes precedence.
        2. Semantic similarity above the threshold is treated as a duplicate.

        Args:
            skill: Candidate skill.
            threshold: Minimum embedding similarity.

        Returns:
            Existing skill row/model when a duplicate is found.
        """

        by_name = self._repository.get_by_name(skill.name)

        if by_name is not None:
            return self._to_model(by_name)

        if not skill.embedding or self._scorer is None:
            return None

        best_match = None
        best_score = threshold

        for row in self._repository.list():
            existing_embedding = row.get("embedding") or []

            if not existing_embedding:
                continue

            similarity = self._scorer.similarity_score(
                skill.embedding,
                existing_embedding,
            )

            if similarity >= best_score:
                best_score = similarity
                best_match = row

        if best_match is None:
            return None

        return self._to_model(best_match)

    def similarity_score(
        self,
        source_embedding: list[float],
        target_embedding: list[float],
    ) -> float:
        """
        Calculate cosine similarity.
        """

        if self._scorer is None:
            return 0.0

        return self._scorer.similarity_score(
            source_embedding,
            target_embedding,
        )

    def is_similar(
        self,
        score: float,
        threshold: float = 0.90,
    ) -> bool:
        """
        Determine whether two skills are similar.
        """

        return score >= threshold

    def _to_model(self, row: dict[str, Any]) -> Capability:
        """
        Convert a repository row into a Capability model.
        """

        if self._store is not None:
            return self._store.to_model(row)

        return Capability(
            id=UUID(str(row["id"])),
            name=row["name"],
            description=row.get("description") or "",
            category=row.get("category") or "general",
        )