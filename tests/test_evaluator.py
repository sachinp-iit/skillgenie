"""
Tests for the skill evaluator.
"""

from uuid import uuid4

from skillgenie.constants import SkillStatus
from skillgenie.core.evaluator import SkillEvaluator
from tests.conftest import make_capability, make_skill


def _build(
    config,
    capability_repository,
    metrics_repository,
    audit_repository,
    execution_repository,
    dummy_database,
):
    return SkillEvaluator(
        config=config,
        database=dummy_database,
        skill_repository=capability_repository,
        metrics_repository=metrics_repository,
        audit_repository=audit_repository,
        execution_repository=execution_repository,
    )


def _seed(repo):
    row = make_skill()

    repo.create(
        capability_id=row["id"],
        name=row["name"],
        description=row["description"],
        category=row["category"],
        version=row["version"],
        status=row["status"],
    )

    repo.update(capability_id=row["id"], **{k: v for k, v in row.items() if k != "id"})

    return row["id"]


def test_evaluate_persists_scores_and_promotes(
    config,
    capability_repository,
    metrics_repository,
    audit_repository,
    execution_repository,
    dummy_database,
):
    evaluator = _build(
        config,
        capability_repository,
        metrics_repository,
        audit_repository,
        execution_repository,
        dummy_database,
    )

    skill = make_capability()

    capability_repository.create(
        capability_id=skill.id,
        name=skill.name,
        description=skill.description,
        category=skill.category,
        version=skill.version,
        status=skill.status.value,
    )

    result = evaluator.evaluate(skill)

    row = capability_repository.get_by_id(skill.id)

    assert row["confidence_score"] == skill.confidence_score
    assert row["quality_score"] == skill.quality_score
    assert row["success_rate"] == 1.0
    assert result.status == SkillStatus.CANDIDATE

    metrics = metrics_repository.get_by_capability(skill.id)

    assert len(metrics) == 1

    assert any(log["action"] == "EVALUATED" for log in audit_repository.logs)


def test_evaluate_auto_approval(
    monkeypatch,
    config,
    capability_repository,
    metrics_repository,
    audit_repository,
    execution_repository,
    dummy_database,
):
    monkeypatch.setenv("LEARNING_AUTO_APPROVAL", "true")
    monkeypatch.setenv("SIMILARITY_AUTO_APPROVAL_THRESHOLD", "0.85")

    evaluator = _build(
        config,
        capability_repository,
        metrics_repository,
        audit_repository,
        execution_repository,
        dummy_database,
    )

    skill = make_capability(confidence_score=0.9)

    capability_repository.create(
        capability_id=skill.id,
        name=skill.name,
        description=skill.description,
        category=skill.category,
        version=skill.version,
        status=skill.status.value,
    )

    result = evaluator.evaluate(skill)

    assert result.status == SkillStatus.APPROVED

    assert capability_repository.get_by_id(skill.id)["status"] == "APPROVED"


def test_approve_publish_flow(
    config,
    capability_repository,
    metrics_repository,
    audit_repository,
    execution_repository,
    dummy_database,
):
    evaluator = _build(
        config,
        capability_repository,
        metrics_repository,
        audit_repository,
        execution_repository,
        dummy_database,
    )

    skill_id = _seed(capability_repository)

    skill = evaluator._skill_repository.get_by_id(skill_id)

    from skillgenie.storage.skill_store import SkillStore
    from skillgenie.core.scorer import SkillScorer

    store = SkillStore(config, repository=capability_repository)

    model = store.to_model(skill)

    evaluator.approve(model)

    assert capability_repository.get_by_id(skill_id)["status"] == "APPROVED"

    evaluator.publish(model)

    assert capability_repository.get_by_id(skill_id)["status"] == "PUBLISHED"


def test_reject_records_reason(
    config,
    capability_repository,
    metrics_repository,
    audit_repository,
    execution_repository,
    dummy_database,
):
    evaluator = _build(
        config,
        capability_repository,
        metrics_repository,
        audit_repository,
        execution_repository,
        dummy_database,
    )

    skill = make_capability(status=SkillStatus.CANDIDATE.value)

    capability_repository.create(
        capability_id=skill.id,
        name=skill.name,
        description=skill.description,
        category=skill.category,
        version=skill.version,
        status=skill.status.value,
    )

    result = evaluator.reject(skill, "insufficient evidence")

    assert result.status == SkillStatus.DRAFT
    assert result.metadata["rejection_reason"] == "insufficient evidence"

    assert capability_repository.get_by_id(skill.id)["metadata"]["rejection_reason"] == (
        "insufficient evidence"
    )