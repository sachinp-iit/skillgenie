# ============================================================================
# Project      : SkillGenie
# File         : health.py
# Description  : Skill health engine. Computes the overall health of a
#                capability from its performance signals.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any

from skillgenie.config import Config
from skillgenie.constants import (
    HEALTH_EXCELLENT_THRESHOLD,
    HEALTH_FAIR_THRESHOLD,
    HEALTH_GOOD_THRESHOLD,
    HEALTH_POOR_THRESHOLD,
    SkillHealth,
)
from skillgenie.utils.logger import Logger


class SkillHealthEngine:
    """
    Evaluates skill health and detects degradation.
    """

    def __init__(self, config: Config):
        """
        Initialize health engine.

        Args:
            config: SkillGenie configuration.
        """

        self._config = config
        self._logger = Logger(config).log

    def health(self, skill: Any) -> SkillHealth:
        """
        Compute overall health for a skill.

        Args:
            skill: A skill object or row mapping.

        Returns:
            Health classification.
        """

        overall = self.health_score(skill)

        if overall >= HEALTH_EXCELLENT_THRESHOLD:
            return SkillHealth.EXCELLENT

        if overall >= HEALTH_GOOD_THRESHOLD:
            return SkillHealth.GOOD

        if overall >= HEALTH_FAIR_THRESHOLD:
            return SkillHealth.FAIR

        if overall >= HEALTH_POOR_THRESHOLD:
            return SkillHealth.POOR

        return SkillHealth.CRITICAL

    def health_score(self, skill: Any) -> float:
        """
        Numeric health score between 0 and 1.

        Combines confidence, quality, success rate and latency normalised.
        """

        confidence = self._float_value(getattr(skill, "confidence_score", 0.0))
        quality = self._float_value(getattr(skill, "quality_score", 0.0))
        success_rate = self._float_value(
            getattr(skill, "success_rate", 0.0)
        )
        avg_latency_ms = self._float_value(
            getattr(skill, "avg_latency_ms", 0.0)
        )

        latency_score = self._latency_score(avg_latency_ms)

        score = (
            0.30 * min(confidence, 1.0)
            + 0.30 * min(quality, 1.0)
            + 0.30 * min(success_rate, 1.0)
            + 0.10 * latency_score
        )

        return round(min(max(score, 0.0), 1.0), 3)

    def degraded(self, skill: Any) -> bool:
        """
        Report whether a skill has degraded to POOR or CRITICAL.
        """

        return self.health(skill) in {
            SkillHealth.POOR,
            SkillHealth.CRITICAL,
        }

    @staticmethod
    def _latency_score(avg_latency_ms: float) -> float:
        """
        Convert average latency into a 0-1 score. Lower is better.
        """

        if avg_latency_ms <= 0:
            return 0.8

        if avg_latency_ms <= 500:
            return 1.0

        if avg_latency_ms <= 2000:
            return 0.7

        if avg_latency_ms <= 10000:
            return 0.4

        return 0.1

    def _float_value(self, value: Any) -> float:
        """
        Safely convert to float.
        """

        try:
            return float(value or 0.0)
        except (TypeError, ValueError):
            return 0.0