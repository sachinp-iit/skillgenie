# ============================================================================
# Project      : SkillGenie
# File         : feedback.py
# Description  : Outcome feedback service.  Records recommendation outcomes,
#                refreshes skill metrics with real-world results, detects
#                performance drift, and provides explainable health breakdowns.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from skillgenie.config import Config
from skillgenie.constants import SkillHealth
from skillgenie.core.health import SkillHealthEngine
from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.audit_repository import AuditRepository
from skillgenie.database.repositories.capability_repository import (
    CapabilityRepository,
)
from skillgenie.database.repositories.outcome_repository import OutcomeRepository
from skillgenie.models.outcome import Outcome
from skillgenie.utils.logger import Logger


class SkillFeedbackService:
    """
    Records real-world outcomes for recommendations, refreshes skill metrics
    and health, detects performance drift, and provides explainable breakdowns.
    """

    def __init__(
        self,
        config: Config,
        database: DatabaseManager,
        skill_repository: CapabilityRepository | None = None,
        outcome_repository: OutcomeRepository | None = None,
        audit_repository: AuditRepository | None = None,
    ):
        self._config = config
        self._database = database
        self._logger = Logger(config).log
        self._skill_repository = skill_repository or CapabilityRepository(database)
        self._outcome_repository = outcome_repository or OutcomeRepository(database)
        self._audit_repository = audit_repository or AuditRepository(database)
        self._health_engine = SkillHealthEngine(config)
        self._drift_threshold = config.get_float("feedback.drift_threshold", 0.20)
        self._drift_window_hours = config.get_int("feedback.drift_window_hours", 168)

    def record_outcome(
        self,
        capability_id: UUID,
        outcome: str = "SUCCESS",
        recommendation_id: UUID | None = None,
        latency_ms: float = 0.0,
        rating: float | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Outcome:
        """
        Record a real-world outcome for a skill and refresh its metrics.
        """
        rec = Outcome(
            capability_id=capability_id,
            recommendation_id=recommendation_id,
            outcome=outcome,
            latency_ms=latency_ms,
            rating=rating,
            metadata=metadata or {},
        )

        self._outcome_repository.create(
            outcome_id=rec.id,
            capability_id=rec.capability_id,
            recommendation_id=rec.recommendation_id,
            outcome=rec.outcome,
            latency_ms=rec.latency_ms,
            rating=rec.rating,
            metadata=rec.metadata,
        )

        self._refresh_from_outcomes(capability_id)
        self._audit(
            capability_id=capability_id,
            action="OUTCOME_RECORDED",
            remarks=f"outcome={outcome}, latency={latency_ms:g}ms",
            payload={
                "outcome_id": str(rec.id),
                "outcome": outcome,
                "latency_ms": latency_ms,
                "rating": rating,
            },
        )

        return rec

    def recent_failures(
        self, capability_id: UUID, limit: int = 20
    ) -> list[dict[str, Any]]:
        """
        Return recent failed outcomes for a skill.
        """
        all_outcomes = self._outcome_repository.get_by_capability(capability_id)
        failures = [
            dict(row)
            for row in all_outcomes
            if dict(row).get("outcome") in {"FAILED", "CANCELLED", "PARTIAL"}
        ]
        return failures[:limit]

    def detect_drift(self, capability_id: UUID) -> dict[str, Any] | None:
        """
        Compare recent success rate to historical baseline.

        Returns a drift event dict when a significant deviation is detected,
        otherwise ``None``.
        """
        outcomes = self._outcome_repository.get_by_capability(capability_id)
        if not outcomes or len(outcomes) < 10:
            return None

        now = datetime.utcnow()
        cutoff = now - timedelta(hours=self._drift_window_hours)

        recent = [
            r
            for r in outcomes
            if dict(r).get("created_at", now) >= cutoff
        ]

        if len(recent) < 5:
            return None

        historical_successes = sum(
            1 for r in outcomes if dict(r).get("outcome") == "SUCCESS"
        )
        historical_total = len(outcomes)
        historical_rate = historical_successes / historical_total

        recent_successes = sum(
            1 for r in recent if dict(r).get("outcome") == "SUCCESS"
        )
        recent_rate = recent_successes / len(recent)

        delta = recent_rate - historical_rate

        if abs(delta) >= self._drift_threshold:
            direction = "DEGRADED" if delta < 0 else "IMPROVED"
            drift = {
                "capability_id": str(capability_id),
                "direction": direction,
                "historical_rate": round(historical_rate, 3),
                "recent_rate": round(recent_rate, 3),
                "delta": round(delta, 3),
                "window_hours": self._drift_window_hours,
                "sample_size": len(recent),
                "detected_at": now.isoformat(),
            }
            self._audit(
                capability_id=capability_id,
                action=f"DRIFT_{direction}",
                remarks=f"rate {historical_rate:.3f} -> {recent_rate:.3f} (delta={delta:+.3f})",
                payload=drift,
            )
            return drift

        return None

    def health_explanation(self, skill: Any) -> dict[str, Any]:
        """
        Provide a human-readable breakdown of a skill's health score.
        """
        confidence = float(getattr(skill, "confidence_score", 0.0) or 0.0)
        quality = float(getattr(skill, "quality_score", 0.0) or 0.0)
        success_rate = float(getattr(skill, "success_rate", 0.0) or 0.0)
        latency_ms = float(getattr(skill, "avg_latency_ms", 0.0) or 0.0)

        latency_score = self._health_engine._latency_score(latency_ms)
        health = self._health_engine.health(skill)
        score = self._health_engine.health_score(skill)

        components = {
            "confidence": {
                "value": round(confidence, 3),
                "weight": 0.30,
                "weighted": round(0.30 * min(confidence, 1.0), 3),
            },
            "quality": {
                "value": round(quality, 3),
                "weight": 0.30,
                "weighted": round(0.30 * min(quality, 1.0), 3),
            },
            "success_rate": {
                "value": round(success_rate, 3),
                "weight": 0.30,
                "weighted": round(0.30 * min(success_rate, 1.0), 3),
            },
            "latency": {
                "value": round(latency_ms, 1),
                "weight": 0.10,
                "score": round(latency_score, 3),
                "weighted": round(0.10 * latency_score, 3),
            },
        }

        return {
            "health": health.value,
            "score": score,
            "components": components,
        }

    def _refresh_from_outcomes(self, capability_id: UUID) -> None:
        """
        Recalculate success_rate and health from outcome records.
        """
        skill = self._skill_repository.get_by_id(capability_id)
        if skill is None:
            return

        counts = self._outcome_repository.count_outcomes(capability_id)
        total = counts["total"]
        successes = counts["successes"]

        if total == 0:
            return

        outcome_success_rate = successes / total

        existing = dict(skill)
        existing_usage = int(existing.get("usage_count") or 0)
        existing_success_rate = float(existing.get("success_rate") or 0.0)

        blended_success_rate = (
            (existing_success_rate * existing_usage + outcome_success_rate)
            / (existing_usage + 1)
            if existing_usage
            else outcome_success_rate
        )

        metrics = SimpleNamespace(
            confidence_score=existing.get("confidence_score"),
            quality_score=existing.get("quality_score"),
            success_rate=blended_success_rate,
            avg_latency_ms=existing.get("avg_latency_ms", 0.0),
        )

        health = self._health_engine.health(metrics)

        self._skill_repository.update(
            capability_id=capability_id,
            success_rate=round(blended_success_rate, 3),
            health=health.value,
        )

    def _audit(
        self,
        capability_id: UUID,
        action: str,
        remarks: str = "",
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._audit_repository.create(
            audit_id=uuid4(),
            capability_id=capability_id,
            action=action,
            performed_by="feedback",
            remarks=remarks,
            payload=payload or {},
        )