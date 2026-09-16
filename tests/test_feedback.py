"""
Tests for the outcome feedback service and drift detection.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from skillgenie.core.feedback import SkillFeedbackService
from tests.conftest import make_capability, make_skill


def _build_feedback(
    config,
    capability_repository,
    outcome_repository,
    audit_repository,
    dummy_database,
):
    return SkillFeedbackService(
        config=config,
        database=dummy_database,
        skill_repository=capability_repository,
        outcome_repository=outcome_repository,
        audit_repository=audit_repository,
    )


def _seed_skill(capability_repository):
    skill = make_capability(status="PUBLISHED")
    capability_repository.create(
        capability_id=skill.id,
        name=skill.name,
        description=skill.description,
        category=skill.category,
        version=skill.version,
        status=skill.status.value,
    )
    return skill


def test_record_outcome(
    config,
    capability_repository,
    outcome_repository,
    audit_repository,
    dummy_database,
):
    skill = _seed_skill(capability_repository)
    feedback = _build_feedback(
        config,
        capability_repository,
        outcome_repository,
        audit_repository,
        dummy_database,
    )

    outcome = feedback.record_outcome(
        capability_id=skill.id,
        outcome="SUCCESS",
        latency_ms=200.0,
        rating=4.5,
    )

    assert outcome.outcome == "SUCCESS"
    assert outcome.latency_ms == 200.0

    records = outcome_repository.get_by_capability(skill.id)
    assert len(records) == 1
    assert records[0]["outcome"] == "SUCCESS"

    audit_entries = audit_repository.get_by_capability(skill.id)
    actions = [entry["action"] for entry in audit_entries]
    assert "OUTCOME_RECORDED" in actions


def test_record_outcome_updates_success_rate_and_health(
    config,
    capability_repository,
    outcome_repository,
    audit_repository,
    dummy_database,
):
    skill = _seed_skill(capability_repository)
    feedback = _build_feedback(
        config,
        capability_repository,
        outcome_repository,
        audit_repository,
        dummy_database,
    )

    feedback.record_outcome(capability_id=skill.id, outcome="FAILED")

    updated = dict(capability_repository.get_by_id(skill.id))
    assert updated["success_rate"] < skill.success_rate


def test_recent_failures(
    config,
    capability_repository,
    outcome_repository,
    audit_repository,
    dummy_database,
):
    skill = _seed_skill(capability_repository)
    feedback = _build_feedback(
        config,
        capability_repository,
        outcome_repository,
        audit_repository,
        dummy_database,
    )

    feedback.record_outcome(capability_id=skill.id, outcome="SUCCESS")
    feedback.record_outcome(capability_id=skill.id, outcome="FAILED")
    feedback.record_outcome(capability_id=skill.id, outcome="FAILED")

    failures = feedback.recent_failures(skill.id)

    assert len(failures) == 2
    assert all(row["outcome"] == "FAILED" for row in failures)


def test_detect_drift_detects_degradation(
    config,
    capability_repository,
    outcome_repository,
    audit_repository,
    dummy_database,
):
    skill = _seed_skill(capability_repository)
    feedback = _build_feedback(
        config,
        capability_repository,
        outcome_repository,
        audit_repository,
        dummy_database,
    )

    old = datetime.utcnow() - timedelta(days=10)
    for _ in range(12):
        outcome_repository.create(
            outcome_id=uuid4(),
            capability_id=skill.id,
            recommendation_id=None,
            outcome="SUCCESS",
            latency_ms=100.0,
            rating=None,
            metadata={},
            created_at=old,
        )
    for _ in range(6):
        outcome_repository.create(
            outcome_id=uuid4(),
            capability_id=skill.id,
            recommendation_id=None,
            outcome="FAILED",
            latency_ms=500.0,
            rating=None,
            metadata={},
        )

    drift = feedback.detect_drift(skill.id)

    assert drift is not None
    assert drift["direction"] == "DEGRADED"
    assert drift["recent_rate"] < drift["historical_rate"]


def test_detect_drift_returns_none_when_small_sample(
    config,
    capability_repository,
    outcome_repository,
    audit_repository,
    dummy_database,
):
    skill = _seed_skill(capability_repository)
    feedback = _build_feedback(
        config,
        capability_repository,
        outcome_repository,
        audit_repository,
        dummy_database,
    )

    feedback.record_outcome(capability_id=skill.id, outcome="FAILED")

    assert feedback.detect_drift(skill.id) is None


def test_health_explanation(
    config,
    capability_repository,
    outcome_repository,
    audit_repository,
    dummy_database,
):
    skill = make_capability(
        status="PUBLISHED",
        confidence_score=0.9,
        quality_score=0.8,
        success_rate=1.0,
        avg_latency_ms=120.0,
    )
    feedback = _build_feedback(
        config,
        capability_repository,
        outcome_repository,
        audit_repository,
        dummy_database,
    )

    explanation = feedback.health_explanation(skill)

    assert explanation["health"] == "EXCELLENT"
    assert "components" in explanation
    assert set(explanation["components"]).issuperset(
        {"confidence", "quality", "success_rate", "latency"}
    )
    assert "weight" in explanation["components"]["confidence"]