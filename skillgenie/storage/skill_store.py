# ============================================================================
# Project      : SkillGenie
# File         : skill_store.py
# Description  : High-level skill registry. Wraps the capability repository
#                with model conversion and semantic search helpers used by
#                the learner, recommender, CLI and REST API layers.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from skillgenie.config import Config
from skillgenie.constants import RecommendationType, SkillHealth, SkillStatus
from skillgenie.core.scorer import SkillScorer
from skillgenie.database.repositories.capability_repository import (
    CapabilityRepository,
)
from skillgenie.embeddings.base import EmbeddingProvider
from skillgenie.exceptions import CapabilityNotFoundError
from skillgenie.models.capability import Capability


def capability_to_dict(skill: Capability) -> dict[str, Any]:
    """
    Serialize a Capability model into a JSON-safe dictionary.
    """

    return {
        "id": str(skill.id),
        "name": skill.name,
        "description": skill.description,
        "category": skill.category,
        "version": skill.version,
        "status": skill.status.value,
        "confidence_score": skill.confidence_score,
        "quality_score": skill.quality_score,
        "success_rate": skill.success_rate,
        "usage_count": skill.usage_count,
        "avg_latency_ms": skill.avg_latency_ms,
        "health": skill.health.value,
        "workflow": skill.workflow,
        "metadata": skill.metadata,
        "created_from": skill.created_from,
        "relationship_graph": skill.relationship_graph,
        "created_at": skill.created_at.isoformat() if skill.created_at else None,
        "updated_at": skill.updated_at.isoformat() if skill.updated_at else None,
        "last_used_at": (
            skill.last_used_at.isoformat()
            if skill.last_used_at
            else None
        ),
    }


class SkillStore:
    """
    Skill registry abstraction over the capabilities repository.
    """

    def __init__(
        self,
        config: Config,
        repository: CapabilityRepository | None = None,
        embedding_provider: EmbeddingProvider | None = None,
        scorer: SkillScorer | None = None,
    ):
        """
        Initialize skill store.

        Args:
            config: SkillGenie configuration.
            repository: Capability repository override.
            embedding_provider: Embedding provider for semantic search.
            scorer: Scoring engine override.
        """

        self._config = config

        self._repository = repository

        self._provider = embedding_provider

        self._scorer = scorer or SkillScorer(config)

    @property
    def repository(self) -> CapabilityRepository:
        """
        Underlying capability repository.
        """

        return self._repository

    def create(self, skill: Capability) -> Capability:
        """
        Persist a new skill.
        """

        self._repository.create(
            capability_id=skill.id,
            name=skill.name,
            description=skill.description,
            category=skill.category,
            version=skill.version,
            status=skill.status.value,
        )

        self._update_extended(skill)

        return skill

    def get(self, capability_id: UUID) -> Capability | None:
        """
        Retrieve a skill by id.
        """

        row = self._repository.get_by_id(capability_id)

        return self.to_model(row) if row else None

    def get_by_name(self, name: str) -> Capability | None:
        """
        Retrieve a skill by name.
        """

        row = self._repository.get_by_name(name)

        return self.to_model(row) if row else None

    def list(
        self,
        status: str | None = None,
        category: str | None = None,
    ) -> list[Capability]:
        """
        List skills, optionally filtered.
        """

        rows = self._repository.list(status=status, category=category)

        return [self.to_model(row) for row in rows]

    def update(
        self,
        capability_id: UUID,
        **fields: Any,
    ) -> Capability | None:
        """
        Update skill columns and return the refreshed skill.
        """

        self._require_exists(capability_id)

        normalized = self._normalize_fields(fields)

        self._repository.update(
            capability_id=capability_id,
            **normalized,
        )

        return self.get(capability_id)

    def delete(self, capability_id: UUID) -> None:
        """
        Delete a skill.
        """

        self._repository.delete(capability_id)

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float | None = None,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Semantic search for skills.

        Args:
            query: Task description or user query.
            top_k: Maximum number of results.
            threshold: Minimum similarity (defaults to configuration).
            status: Restrict results to a lifecycle status.

        Returns:
            Ranked candidates, each containing `skill`, `similarity`,
            `ranking`, `confidence_score`, `quality_score` and `type`.
        """

        candidates: list[dict[str, Any]] = []

        thresholds = (
            threshold
            if threshold is not None
            else self._config.get_float(
                "similarity.recommendation_threshold",
                0.80,
            )
        )

        skills = self.list(status=status)

        query_embedding = self._embed(query)

        for skill in skills:
            similarity = self._similarity(
                query_text=query,
                query_embedding=query_embedding,
                skill=skill,
            )

            if similarity < thresholds:
                continue

            ranking = self._scorer.ranking_score(
                similarity=similarity,
                confidence=skill.confidence_score,
                quality=skill.quality_score,
            )

            candidates.append(
                {
                    "skill": skill,
                    "similarity": round(similarity, 6),
                    "ranking": ranking,
                    "confidence_score": skill.confidence_score,
                    "quality_score": skill.quality_score,
                    "type": self._recommendation_type(similarity),
                    "reason": self._reason(skill, similarity),
                }
            )

        candidates.sort(key=lambda item: item["ranking"], reverse=True)

        return candidates[:top_k]

    def find_similar(
        self,
        embedding: list[float],
        top_k: int = 5,
        threshold: float | None = None,
        exclude: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """
        Find skills similar to a given embedding vector.
        """

        candidates: list[dict[str, Any]] = []

        thresholds = (
            threshold
            if threshold is not None
            else self._config.get_float(
                "similarity.threshold",
                0.85,
            )
        )

        for skill in self.list():

            if exclude is not None and skill.id == exclude:
                continue

            similarity = self._similarity(
                query_text=None,
                query_embedding=embedding,
                skill=skill,
            )

            if similarity < thresholds:
                continue

            ranking = self._scorer.ranking_score(
                similarity=similarity,
                confidence=skill.confidence_score,
                quality=skill.quality_score,
            )

            candidates.append(
                {
                    "skill": skill,
                    "similarity": round(similarity, 6),
                    "ranking": ranking,
                    "confidence_score": skill.confidence_score,
                    "quality_score": skill.quality_score,
                    "type": self._recommendation_type(similarity),
                    "reason": self._reason(skill, similarity),
                }
            )

        candidates.sort(key=lambda item: item["ranking"], reverse=True)

        return candidates[:top_k]

    def to_model(self, row: dict[str, Any]) -> Capability:
        """
        Convert a repository row mapping into a Capability model.
        """

        def as_str_list(value: Any) -> list[str]:
            if value is None:
                return []

            if isinstance(value, list):
                return [str(item) for item in value]

            return []

        embedding = row.get("embedding") or []

        if not isinstance(embedding, list):
            embedding = []

        return Capability(
            id=UUID(str(row["id"])),
            name=row["name"],
            description=row.get("description") or "",
            category=row.get("category") or "general",
            version=row.get("version") or "1.0.0",
            status=self._enum_value(row.get("status"), SkillStatus, SkillStatus.DRAFT),
            confidence_score=float(row.get("confidence_score") or 0.0),
            quality_score=float(row.get("quality_score") or 0.0),
            success_rate=float(row.get("success_rate") or 0.0),
            usage_count=int(row.get("usage_count") or 0),
            avg_latency_ms=float(row.get("avg_latency_ms") or 0.0),
            health=self._enum_value(row.get("health"), SkillHealth, SkillHealth.GOOD),
            embedding=[float(v) for v in embedding],
            relationship_graph=dict(row.get("relationship_graph") or {}),
            workflow=dict(row.get("workflow") or {}),
            metadata=dict(row.get("metadata") or {}),
            created_from=as_str_list(row.get("created_from")),
            created_at=row.get("created_at") or datetime.utcnow(),
            updated_at=row.get("updated_at") or datetime.utcnow(),
            last_used_at=row.get("last_used_at"),
        )

    def _embed(self, text: str) -> list[float] | None:
        """
        Embed query text when a provider is available.
        """

        if self._provider is None:
            return None

        return self._provider.embed_text(text)

    def _similarity(
        self,
        query_text: str | None,
        query_embedding: list[float] | None,
        skill: Capability,
    ) -> float:
        """
        Compute similarity between a query and a stored skill.

        Falls back to lexical token overlap when no embedding is available.
        """

        if query_embedding:
            return self._scorer.similarity_score(
                query_embedding,
                skill.embedding,
            )

        query_tokens = set(
            str(query_text or "").lower().split()
        )

        stored_tokens = set(
            str(
                (skill.metadata or {}).get(
                    "search_profile",
                    {},
                ).get("tokens", "")
            ).lower().split()
        )

        if not query_tokens or not stored_tokens:
            return 0.0

        return min(
            len(query_tokens & stored_tokens) / len(query_tokens),
            1.0,
        )

    def _recommendation_type(self, similarity: float) -> str:
        """
        Classify a candidate recommendation.
        """

        if similarity >= 0.975:
            return RecommendationType.EXACT.value

        if similarity >= self._config.get_float(
            "similarity.threshold",
            0.85,
        ):
            return RecommendationType.SIMILAR.value

        return RecommendationType.RELATED.value

    def _reason(self, skill: Capability, similarity: float) -> str:
        """
        Human-readable recommendation reason.
        """

        return (
            f"'{skill.name}' matches the task with "
            f"{similarity * 100:.1f}% semantic similarity."
        )

    def _update_extended(self, skill: Capability) -> None:
        """
        Persist the extended skill columns.
        """

        self._repository.update(
            capability_id=skill.id,
            embedding=skill.embedding,
            workflow=skill.workflow,
            metadata=skill.metadata,
            relationship_graph=skill.relationship_graph,
            created_from=skill.created_from,
            confidence_score=skill.confidence_score,
            quality_score=skill.quality_score,
            success_rate=skill.success_rate,
            health=skill.health.value,
        )

    def _normalize_fields(
        self,
        fields: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize typed fields before persisting.
        """

        supported_fields = {
            "name",
            "description",
            "category",
            "version",
            "status",
            "confidence_score",
            "quality_score",
            "success_rate",
            "usage_count",
            "avg_latency_ms",
            "health",
            "embedding",
            "relationship_graph",
            "workflow",
            "metadata",
            "created_from",
            "created_at",
            "updated_at",
            "last_used_at",
        }

        unsupported = set(fields) - supported_fields

        if unsupported:
            raise ValueError(
                f"Unsupported columns: {sorted(unsupported)}"
            )

        normalized = dict(fields)

        for field in ("status",):
            if field in normalized and isinstance(normalized[field], SkillStatus):
                normalized[field] = normalized[field].value

        return normalized

    def _require_exists(self, capability_id: UUID) -> None:
        """
        Raise when a skill does not exist.
        """

        if self._repository.get_by_id(capability_id) is None:
            raise CapabilityNotFoundError(
                f"Skill '{capability_id}' does not exist."
            )

    @staticmethod
    def _enum_value(
        value: Any,
        enum_cls: type,
        default: Any,
    ) -> Any:
        """
        Safe enum parsing.
        """

        if value is None:
            return default

        try:
            return enum_cls(value)
        except ValueError:
            return default