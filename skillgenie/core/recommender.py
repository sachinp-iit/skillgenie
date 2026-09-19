# ============================================================================
# Project      : SkillGenie
# File         : recommender.py
# Description  : Recommends the most relevant skills for a given task.
#
#                Performs semantic search, ranking, filtering and persistence
#                of recommendation records.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from skillgenie.config import Config
from skillgenie.constants import RecommendationType, SkillStatus
from skillgenie.core.ranking import LearnedRanker
from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.capability_repository import (
    CapabilityRepository,
)
from skillgenie.database.repositories.outcome_repository import (
    OutcomeRepository,
)
from skillgenie.database.repositories.recommendation_repository import (
    RecommendationRepository,
)
from skillgenie.database.repositories.trace_repository import TraceRepository
from skillgenie.exceptions import CapabilityNotFoundError
from skillgenie.models.recommendation import Recommendation
from skillgenie.storage.skill_store import SkillStore
from skillgenie.utils.logger import Logger


class SkillRecommender:
    """
    Recommends relevant skills.
    """

    def __init__(
        self,
        config: Config,
        database: DatabaseManager,
        store: SkillStore | None = None,
        recommendation_repository: RecommendationRepository | None = None,
        trace_repository: TraceRepository | None = None,
        outcome_repository: OutcomeRepository | None = None,
    ):
        """
        Initialize Skill Recommender.

        Args:
            config: SkillGenie configuration.
            database: Database manager.
            store: Optional skill store override.
            recommendation_repository: Optional repository override.
            trace_repository: Optional trace repository override.
            outcome_repository: Optional outcome repository for learned ranking.
        """

        self._config = config
        self._database = database

        self._logger = Logger(config).log

        self._store = (
            store
            or SkillStore(
                config,
                repository=CapabilityRepository(database),
            )
        )

        self._recommendation_repository = (
            recommendation_repository or RecommendationRepository(database)
        )

        self._trace_repository = (
            trace_repository or TraceRepository(database)
        )

        self._ranker = LearnedRanker(
            config,
            outcome_repository=(
                outcome_repository or OutcomeRepository(database)
            ),
        )

    def recommend(
        self,
        query: str,
        top_k: int = 5,
        status: str | None = None,
    ) -> list[Recommendation]:
        """
        Recommend the best matching skills for a task query.

        Args:
            query: User query or task description.
            top_k: Number of skills to return.
            status: Restrict to a lifecycle status (defaults to PUBLISHED).

        Returns:
            List of recommendations.
        """

        self._logger.info(
            f"Searching skills for: {query}"
        )

        candidate_status = status or SkillStatus.PUBLISHED.value

        candidates = self._store.search(
            query=query,
            top_k=top_k,
            status=candidate_status,
        )

        recommendations: list[Recommendation] = []

        for candidate in self._ranker.reorder(candidates):
            recommendation = self._persist(candidate, query=query)
            recommendations.append(recommendation)

        return recommendations

    def recommend_by_trace(
        self,
        trace_id: str,
        top_k: int = 5,
    ) -> list[Recommendation]:
        """
        Recommend skills from an execution trace.

        Args:
            trace_id: Execution trace identifier.
            top_k: Number of skills to return.
        """

        self._logger.info(
            f"Recommending skills for trace: {trace_id}"
        )

        trace = self._trace_repository.get_by_id(UUID(str(trace_id)))

        if trace is None:
            raise ValueError(f"Trace '{trace_id}' does not exist.")

        query = (
            trace.get("task_description")
            or trace.get("trace_name")
            or ""
        )

        return self.recommend(query=query, top_k=top_k)

    def recommend_similar(
        self,
        skill_id: str,
        top_k: int = 5,
    ) -> list[Recommendation]:
        """
        Recommend skills similar to an existing skill.

        Args:
            skill_id: Skill identifier.
            top_k: Number of skills to return.
        """

        self._logger.info(
            f"Finding similar skills for: {skill_id}"
        )

        try:
            capability_id = UUID(str(skill_id))
        except ValueError:
            raise ValueError(
                f"Invalid skill id: {skill_id}"
            ) from None

        skill = self._store.get(capability_id)

        if skill is None:
            raise CapabilityNotFoundError(
                f"Skill '{skill_id}' does not exist."
            )

        candidates = self._store.find_similar(
            embedding=skill.embedding,
            top_k=top_k,
            exclude=capability_id,
        )

        recommendations: list[Recommendation] = []

        for candidate in self._ranker.reorder(candidates):
            recommendation = self._persist(
                candidate,
                query=f"similar to:{skill.name}",
            )
            recommendations.append(recommendation)

        return recommendations

    def _persist(
        self,
        candidate: dict[str, Any],
        query: str,
    ) -> Recommendation:
        """
        Build and persist a recommendation record.
        """

        skill = candidate["skill"]

        ranking_score = float(candidate.get("learned_score", 0.0))
        has_learned = "learned_score" in candidate

        if not has_learned:
            ranking_score = candidate["ranking"]

        reason = candidate["reason"]

        if has_learned and (candidate.get("context") or {}).get("mode"):
            reason = (
                f"ranked {ranking_score:.3f} "
                f"({candidate['context']['mode']}): {reason}"
            )

        recommendation = Recommendation(
            id=uuid4(),
            capability_id=skill.id,
            recommendation_type=RecommendationType(
                candidate["type"]
            ),
            confidence_score=candidate["confidence_score"],
            similarity_score=candidate["similarity"],
            ranking_score=ranking_score,
            reason=reason,
            metadata={
                "query": query,
                "skill_name": skill.name,
                "learned": candidate.get("context", {}),
            },
        )

        self._recommendation_repository.create(
            recommendation_id=recommendation.id,
            capability_id=recommendation.capability_id,
            recommendation_type=recommendation.recommendation_type.value,
            confidence_score=recommendation.confidence_score,
            similarity_score=recommendation.similarity_score,
            ranking_score=recommendation.ranking_score,
            reason=recommendation.reason,
            metadata=recommendation.metadata,
        )

        return recommendation

    def recent(
        self,
        limit: int = 20,
    ):
        """
        Return recent recommendation records.
        """

        return self._recommendation_repository.list(limit=limit)