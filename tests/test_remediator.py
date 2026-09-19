"""
Tests for the autonomous drift remediation service.
"""

from datetime import datetime, timedelta

import pytest

from skillgenie.core.feedback import SkillFeedbackService
from skillgenie.core.validator import SkillValidator
from skillgenie.core.remediator import SkillRemediator
from tests.conftest import make_capability


def _feedback(config, capability_repository, outcome_repository):
    from tests.conftest import FakeAuditRepository

    return SkillFeedbackService(
        config=config,
        database=object(),
        skill_repository=capability_repository,
        outcome_repository=outcome_repository,
        audit_repository=FakeAuditRepository(),
    )


def _seed_drift(outcome_repository, skill_id):
    old = datetime.utcnow() - timedelta(days=10)
    recent = datetime.utcnow()

    for _ in range(8):
        outcome_repository.create(
            outcome_id=None,
            capability_id=skill_id,
            recommendation_id=None,
            outcome="SUCCESS",
            latency_ms=100.0,
            rating=None,
            metadata={},
            created_at=old,
        )

    for _ in range(8):
        outcome_repository.create(
            outcome_id=None,
            capability_id=skill_id,
            recommendation_id=None,
            outcome="FAILED",
            latency_ms=900.0,
            rating=None,
            metadata={},
            created_at=recent,
        )


@pytest.fixture
def engine(tmp_path):
    from unittest.mock import Mock

    from skillgenie.core.engine import SkillGenie

    from tests.conftest import FakeCapabilityRepository

    database = Mock()

    skillgenie = SkillGenie(
        config_file=str(tmp_path / "config.json"),
        database=database,
        embeddings_enabled=False,
    )

    fake = FakeCapabilityRepository()

    database.get_session.side_effect = AssertionError(
        "Should not hit the database."
    )

    skillgenie.capabilities = fake
    skillgenie.store._repository = fake

    yield skillgenie

    skillgenie.shutdown()


def test_healthy_skill_requires_no_action(
    config,
    store,
    capability_repository,
    outcome_repository,
):
    skill = make_capability(
        name="Healthy",
        description="A healthy skill that performs well.",
        status="PUBLISHED",
    )
    store.create(skill)

    remediator = SkillRemediator(
        config=config,
        store=store,
        feedback=_feedback(
            config, capability_repository, outcome_repository
        ),
        validator=SkillValidator(config),
    )

    report = remediator.remediate(skill.id)

    assert report["state"] == "HEALTHY"
    assert report["drift"] is None
    assert report["applied"] == []


def test_drifted_skill_gets_suppressed_in_auto_mode(
    config,
    store,
    capability_repository,
    outcome_repository,
):
    skill = make_capability(
        name="Drifting",
        description="A skill whose recent performance degraded badly.",
        status="PUBLISHED",
    )
    store.create(skill)

    _seed_drift(outcome_repository, skill.id)

    remediator = SkillRemediator(
        config=config,
        store=store,
        feedback=_feedback(
            config, capability_repository, outcome_repository
        ),
        validator=SkillValidator(config),
    )

    report = remediator.remediate(skill.id)

    assert report["state"] == "AT_RISK"
    assert report["drift"]["direction"] == "DEGRADED"
    assert "suppress_recommendations" in report["applied"]
    assert "flag_review" in report["applied"]

    refreshed = store.get(skill.id)
    assert refreshed.metadata.get("suppress") is True


def test_review_mode_does_not_apply_actions(
    config,
    store,
    capability_repository,
    outcome_repository,
):
    skill = make_capability(
        name="Review",
        description="A skill under review before any remediation lands.",
        status="PUBLISHED",
    )
    store.create(skill)

    _seed_drift(outcome_repository, skill.id)

    remediator = SkillRemediator(
        config=config,
        store=store,
        feedback=_feedback(
            config, capability_repository, outcome_repository
        ),
        validator=SkillValidator(config),
    )

    report = remediator.remediate(skill.id, mode="review")

    assert report["applied"] == []
    assert any(
        action["action"] == "suppress_recommendations"
        for action in report["actions"]
    )

    refreshed = store.get(skill.id)
    assert refreshed.metadata.get("suppress") is None


def test_invalid_skill_proposes_deprecate_with_force(
    config,
    store,
    capability_repository,
    outcome_repository,
):
    skill = make_capability(
        name="Broken",
        description="",
        status="DRAFT",
        workflow={},
        metadata={},
    )
    store.create(skill)

    remediator = SkillRemediator(
        config=config,
        store=store,
        feedback=_feedback(
            config, capability_repository, outcome_repository
        ),
        validator=SkillValidator(config),
    )

    report = remediator.remediate(skill.id, force=True)

    assert report["state"] == "FAILING"
    actions = {
        action["action"] for action in report["actions"]
    }
    assert "deprecate" in actions
    assert "deprecate" in report["applied"]


def test_engine_remediate_suppresses_drifted_skill(
    engine,
    outcome_repository,
    audit_repository,
):
    skill = make_capability(
        name="EngineDrift",
        description="A skill used to verify engine-level remediation wiring.",
        status="PUBLISHED",
    )
    engine.store.create(skill)

    engine.audit = audit_repository
    engine.remediator._audit_repository = audit_repository
    engine.feedback._audit_repository = audit_repository
    engine.feedback._outcome_repository = outcome_repository
    engine.remediator._feedback = engine.feedback

    _seed_drift(outcome_repository, skill.id)

    report = engine.remediate(skill.id)

    assert report["state"] == "AT_RISK"
    assert "suppress_recommendations" in report["applied"]

    refreshed = engine.store.get(skill.id)
    assert refreshed.metadata.get("suppress") is True

    assert any(
        audit["action"] == "REMEDIATE"
        for audit in audit_repository.logs
    )