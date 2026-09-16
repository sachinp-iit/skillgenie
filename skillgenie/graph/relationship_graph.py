# ============================================================================
# Project      : SkillGenie
# File         : relationship_graph.py
# Description  : Builds and maintains relationships between skills based on
#                semantic similarity, shared tools and categories.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any
from uuid import UUID

from skillgenie.config import Config
from skillgenie.core.scorer import SkillScorer
from skillgenie.models.capability import Capability
from skillgenie.storage.skill_store import SkillStore


class SkillGraphBuilder:
    """
    Constructs parent / child / related edges for skills.
    """

    def __init__(
        self,
        config: Config,
        store: SkillStore | None = None,
        scorer: SkillScorer | None = None,
    ):
        """
        Initialize graph builder.

        Args:
            config: SkillGenie configuration.
            store: Optional skill store for persistence.
            scorer: Optional scoring engine.
        """

        self._config = config
        self._store = store
        self._scorer = scorer or SkillScorer(config)

    def build(
        self,
        skill: Capability,
        all_skills: list[Capability],
        similarity_threshold: float | None = None,
        tool_overlap_threshold: int = 1,
    ) -> dict[str, Any]:
        """
        Build a relationship graph entry for a single skill.

        Args:
            skill: Target skill.
            all_skills: All skills to consider.
            similarity_threshold: Minimum embedding similarity for a related
                edge (defaults to `similarity.threshold`).
            tool_overlap_threshold: Minimum shared tools for a related edge.

        Returns:
            Graph dict with `parents`, `children` and `related` lists.
        """

        threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else self._config.get_float("similarity.threshold", 0.85)
        )

        related: list[dict[str, Any]] = []
        tool_overlap: list[dict[str, Any]] = []

        own_tools = self._skill_tools(skill)

        for candidate in all_skills:

            if candidate.id == skill.id:
                continue

            similarity = self._scorer.similarity_score(
                skill.embedding,
                candidate.embedding,
            ) if skill.embedding and candidate.embedding else 0.0

            edge = {
                "capability_id": str(candidate.id),
                "name": candidate.name,
                "category": candidate.category,
                "similarity": round(similarity, 6),
            }

            if similarity >= threshold:
                related.append(edge)

            shared_tools = own_tools & self._skill_tools(candidate)

            if len(shared_tools) >= tool_overlap_threshold:
                edge["shared_tools"] = sorted(shared_tools)
                tool_overlap.append(edge)

        existing = skill.relationship_graph or {}

        return {
            "parents": list(existing.get("parents", [])),
            "children": list(existing.get("children", [])),
            "related": related,
            "tool_overlap": tool_overlap,
        }

    def refresh(
        self,
        skills: list[Capability],
    ) -> dict[UUID, dict[str, Any]]:
        """
        Rebuild and persist relationship graphs for a set of skills.

        Returns a mapping from skill id to its new graph.
        """

        graphs: dict[UUID, dict[str, Any]] = {}

        for skill in skills:
            graph = self.build(skill, skills)
            graphs[skill.id] = graph

            if self._store is not None:
                self._store.update(
                    skill.id,
                    relationship_graph=graph,
                )

        return graphs

    def _skill_tools(self, skill: Capability) -> set[str]:
        """
        Extract unique tool names used by a skill.
        """

        metadata = skill.metadata or {}
        tools = metadata.get("tools") or []

        names: set[str] = set()

        for tool in tools:
            if isinstance(tool, dict):
                name = tool.get("name")
            else:
                name = tool

            if name:
                names.add(str(name))

        return names