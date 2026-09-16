"""
Tests for the skill lifecycle engine.
"""

from uuid import uuid4

import pytest

from skillgenie.constants import SkillStatus
from skillgenie.core.lifecycle import (
    SkillLifecycle,
    _TRANSITIONS,
)
from skillgenie.exceptions import LifecycleError


def _create_skill(repo, status: SkillStatus) -> str:
    skill_id = uuid4()

    repo.create(
        capability_id=skill_id,
        name="Test Skill",
        description="A test skill.",
        category="general",
        version="1.0.0",
        status=status.value,
    )

    return str(skill_id)


def _build(config, capability_repository, audit_repository, dummy_database):
    return SkillLifecycle(
        config=config,
        database=dummy_database,
        skill_repository=capability_repository,
        audit_repository=audit_repository,
    )


def test_draft_to_candidate(config, capability_repository, audit_repository, dummy_database):
    lifecycle = _build(config, capability_repository, audit_repository, dummy_database)
    skill_id = _create_skill(capability_repository, SkillStatus.DRAFT)

    lifecycle.candidate(skill_id)

    row = capability_repository.get_by_id(skill_id)

    assert row["status"] == SkillStatus.CANDIDATE.value

    assert audit_repository.logs[-1]["action"] == "STATUS_CHANGED"


def test_full_forward_path(config, capability_repository, audit_repository, dummy_database):
    lifecycle = _build(config, capability_repository, audit_repository, dummy_database)
    skill_id = _create_skill(capability_repository, SkillStatus.DRAFT)

    lifecycle.candidate(skill_id)
    lifecycle.approve(skill_id)
    lifecycle.publish(skill_id)

    assert capability_repository.get_by_id(skill_id)["status"] == "PUBLISHED"


def test_invalid_transition_raises(config, capability_repository, audit_repository, dummy_database):
    lifecycle = _build(config, capability_repository, audit_repository, dummy_database)
    skill_id = _create_skill(capability_repository, SkillStatus.DRAFT)

    with pytest.raises(LifecycleError):
        lifecycle.publish(skill_id)  # DRAFT -> PUBLISHED is not allowed

    assert capability_repository.get_by_id(skill_id)["status"] == "DRAFT"


def test_unknown_status_raises(config, capability_repository, audit_repository, dummy_database):
    lifecycle = _build(config, capability_repository, audit_repository, dummy_database)
    skill_id = _create_skill(capability_repository, SkillStatus.APPROVED)

    capability_repository.update(capability_id=skill_id, status="WEIRD")

    with pytest.raises(LifecycleError):
        lifecycle.deprecate(skill_id)


def test_missing_skill_raises(config, capability_repository, audit_repository, dummy_database):
    lifecycle = _build(config, capability_repository, audit_repository, dummy_database)

    from skillgenie.exceptions import CapabilityNotFoundError

    with pytest.raises(CapabilityNotFoundError):
        lifecycle.approve(str(uuid4()))


def test_empty_skill_id_raises(config, capability_repository, audit_repository, dummy_database):
    from skillgenie.exceptions import CapabilityNotFoundError
    from skillgenie.exceptions import SkillGenieError

    lifecycle = _build(config, capability_repository, audit_repository, dummy_database)

    with pytest.raises((ValueError, CapabilityNotFoundError, SkillGenieError)):
        lifecycle.approve("")


def test_reject_moves_to_draft_and_records_reason(
    config, capability_repository, audit_repository, dummy_database
):
    lifecycle = _build(config, capability_repository, audit_repository, dummy_database)
    skill_id = _create_skill(capability_repository, SkillStatus.CANDIDATE)

    lifecycle.reject(skill_id, "not enough evidence")

    row = capability_repository.get_by_id(skill_id)

    assert row["status"] == SkillStatus.DRAFT.value
    assert row["metadata"]["rejection_reason"] == "not enough evidence"

    assert any(log["action"] == "REJECT" for log in audit_repository.logs)


def test_reopen_for_review_from_published(
    config, capability_repository, audit_repository, dummy_database
):
    lifecycle = _build(config, capability_repository, audit_repository, dummy_database)
    skill_id = _create_skill(capability_repository, SkillStatus.PUBLISHED)

    lifecycle.reopen_for_review(skill_id)

    assert capability_repository.get_by_id(skill_id)["status"] == "CANDIDATE"


def test_reopen_for_review_noop_when_candidate(
    config, capability_repository, audit_repository, dummy_database
):
    lifecycle = _build(config, capability_repository, audit_repository, dummy_database)
    skill_id = _create_skill(capability_repository, SkillStatus.CANDIDATE)

    lifecycle.reopen_for_review(skill_id)

    assert capability_repository.get_by_id(skill_id)["status"] == "CANDIDATE"


def test_transition_links(config):
    links = SkillLifecycle(config, object()).transition_links(SkillStatus.DRAFT)

    assert set(links) == {"APPROVED", "CANDIDATE"}


def test_transition_map_is_consistent():
    for current, targets in _TRANSITIONS.items():
        assert current not in targets

        for target in targets:
            # Every target must either be terminal or have valid onward
            # transitions defined.
            assert target in _TRANSITIONS