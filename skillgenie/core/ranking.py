# ============================================================================
# Project      : SkillGenie
# File         : ranking.py
# Description  : Learned ranking layer for recommendations.  Combines the base
#                semantic fit with real-world outcome statistics (a Bayesian
#                Thompson-style success prior), recency and latency signals so
#                the recommender improves as the registry gathers outcomes.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import math
from datetime import datetime
from typing import Any
from uuid import UUID

from skillgenie.config import Config
from skillgenie.utils.logger import Logger


class LearnedRanker:
    """
    Re-ranks candidate recommendations using learned signals.

    Modes (``ranking.mode``):

    - ``classic`` : original store ordering (no learned signals).
    - ``fit``     : semantic fit only.
    - ``bandit``  : Thompson-style Beta posterior mean on outcomes only.
    - ``learned`` : weighted combination of fit, recency, latency.
    - ``hybrid``  : weighted combination of fit, bandit, recency, latency.
    """

    MODES = {"classic", "fit", "bandit", "learned", "hybrid"}

    def __init__(
        self,
        config: Config,
        outcome_repository: Any = None,
    ):
        self._config = config
        self._mode = str(config.get("ranking.mode", "hybrid")).lower()
        self._outcome_repository = outcome_repository
        self._logger = Logger(config).log

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def enabled(self) -> bool:
        return self._mode in {"fit", "bandit", "learned", "hybrid"}

    def reorder(
        self,
        candidates: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Augment candidates with learned scores and re-order by them.
        """

        if not self.enabled:
            return candidates

        scored: list[dict[str, Any]] = []

        for candidate in candidates:
            self._score(candidate)
            scored.append(candidate)

        scored.sort(key=lambda item: item["learned_score"], reverse=True)

        return scored

    def _score(self, candidate: dict[str, Any]) -> None:
        """
        Compute the learned score and attach context to a candidate.
        """

        skill = candidate["skill"]

        stats = self._stats(skill.id)

        total = stats.get("total", 0)
        successes = stats.get("successes", 0)

        bandit_mean = (
            (successes + 1) / (total + 2)
            if total > 0
            else 0.5
        )

        fit = float(candidate.get("ranking") or 0.0)
        recency = self._recency_score(skill)
        latency = self._latency_score(skill)

        if self._mode == "fit":
            learned = fit
            weights_used = 1.0
        elif self._mode == "bandit":
            learned = bandit_mean
            weights_used = 1.0
        elif self._mode == "learned":
            weights_used = sum(
                self._weight("fit" if key == "fit" else key)
                for key in ("fit", "recency", "latency")
            )
            learned = (
                self._weight("fit") * fit
                + self._weight("recency") * recency
                + self._weight("latency") * latency
            ) / weights_used
        else:
            weights_used = sum(
                self._weight(key)
                for key in ("fit", "bandit", "recency", "latency")
            )
            learned = (
                self._weight("fit") * fit
                + self._weight("bandit") * bandit_mean
                + self._weight("recency") * recency
                + self._weight("latency") * latency
            ) / weights_used

        candidate["learned_score"] = round(learned, 4)
        candidate["context"] = {
            "mode": self._mode,
            "bandit_mean": round(bandit_mean, 4),
            "recency_score": round(recency, 4),
            "latency_score": round(latency, 4),
            "outcome_sample_size": total,
            "outcome_successes": successes,
        }

    def _weight(self, key: str) -> float:
        return max(
            0.0,
            self._config.get_float(
                f"ranking.{key}_weight",
                0.50 if key == "fit" else 0.15,
            ),
        )

    def _stats(self, capability_id: UUID) -> dict[str, int]:
        """
        Outcome statistics for a skill, degrading gracefully when the outcome
        repository is unavailable.
        """

        if self._outcome_repository is None:
            return {"successes": 0, "total": 0}

        try:
            counts = self._outcome_repository.count_outcomes(
                capability_id
            )
            return {
                "successes": int(counts.get("successes") or 0),
                "total": int(counts.get("total") or 0),
            }
        except Exception as exc:
            self._logger.debug(
                f"Outcome stats unavailable for {capability_id}: {exc}"
            )
            return {"successes": 0, "total": 0}

    @staticmethod
    def _recency_score(skill: Any) -> float:
        """
        Exponential recency score: 1.0 when freshly updated, decaying with a
        30-day half-life.
        """

        updated_at = getattr(skill, "updated_at", None)

        if not updated_at:
            return 1.0

        try:
            days = (datetime.utcnow() - updated_at).total_seconds() / 86400.0
        except TypeError:
            return 1.0

        return math.exp(-max(0.0, days) / 30.0)

    @staticmethod
    def _latency_score(skill: Any) -> float:
        """
        Normalized latency score reusing the health engine scoring.
        """

        from skillgenie.core.health import SkillHealthEngine

        latency = float(getattr(skill, "avg_latency_ms", 0.0) or 0.0)

        return SkillHealthEngine._latency_score(latency)