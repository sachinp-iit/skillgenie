"""
Tests for the full learning pipeline.
"""

from skillgenie.constants import SkillStatus
from skillgenie.core.learner import SkillLearner
from skillgenie.embeddings.hash import HashEmbeddingProvider
from tests.conftest import add_trace, make_raw_trace


_UNSET = object()


def _build_learner(
    config,
    trace_repository,
    capability_repository,
    metrics_repository,
    audit_repository,
    execution_repository,
    dummy_database,
    provider=_UNSET,
):
    if provider is _UNSET:
        provider = HashEmbeddingProvider(dimensions=64)

    return SkillLearner(
        config=config,
        database=dummy_database,
        trace_repository=trace_repository,
        skill_repository=capability_repository,
        metrics_repository=metrics_repository,
        audit_repository=audit_repository,
        execution_repository=execution_repository,
        embedding_provider=provider,
    )


def test_learn_creates_evaluated_skill(
    config,
    trace_repository,
    capability_repository,
    metrics_repository,
    audit_repository,
    execution_repository,
    dummy_database,
):
    trace_id = add_trace(
        trace_repository,
        make_raw_trace(task="Research web trends"),
    )

    learner = _build_learner(
        config,
        trace_repository,
        capability_repository,
        metrics_repository,
        audit_repository,
        execution_repository,
        dummy_database,
    )

    skill = learner.learn(trace_id)

    assert skill.name
    assert skill.embedding
    assert skill.workflow["steps"]
    assert skill.metadata["tools"]
    assert skill.metadata["search_profile"]["tokens"]
    assert skill.status == SkillStatus.CANDIDATE
    assert trace_id in skill.created_from

    assert capability_repository.get_by_id(skill.id)["status"] == "CANDIDATE"

    assert len(metrics_repository.get_by_capability(skill.id)) == 1


def test_learn_same_trace_returns_duplicate(
    config,
    trace_repository,
    capability_repository,
    metrics_repository,
    audit_repository,
    execution_repository,
    dummy_database,
):
    trace_id = add_trace(
        trace_repository,
        make_raw_trace(task="Resume summarizer"),
    )

    learner = _build_learner(
        config,
        trace_repository,
        capability_repository,
        metrics_repository,
        audit_repository,
        execution_repository,
        dummy_database,
    )

    first = learner.learn(trace_id)
    second = learner.learn(trace_id)

    assert first.id == second.id

    # No second metric snapshot because the duplicate is not re-evaluated.
    assert len(metrics_repository.get_by_capability(first.id)) == 1


def test_learn_missing_trace_raises(
    config,
    trace_repository,
    capability_repository,
    metrics_repository,
    audit_repository,
    execution_repository,
    dummy_database,
):
    from uuid import uuid4

    learner = _build_learner(
        config,
        trace_repository,
        capability_repository,
        metrics_repository,
        audit_repository,
        execution_repository,
        dummy_database,
    )

    try:
        learner.learn(str(uuid4()))
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for missing trace.")


def test_learn_all(
    config,
    trace_repository,
    capability_repository,
    metrics_repository,
    audit_repository,
    execution_repository,
    dummy_database,
):
    add_trace(trace_repository, make_raw_trace(task="Research web trends"))
    add_trace(trace_repository, make_raw_trace(task="Extract product prices"))

    learner = _build_learner(
        config,
        trace_repository,
        capability_repository,
        metrics_repository,
        audit_repository,
        execution_repository,
        dummy_database,
    )

    skills = learner.learn_all()

    assert len(skills) == 2

    assert len(capability_repository.list()) == 2


def test_relearn_reprocesses_source_traces(
    config,
    trace_repository,
    capability_repository,
    metrics_repository,
    audit_repository,
    execution_repository,
    dummy_database,
):
    trace_id = add_trace(
        trace_repository,
        make_raw_trace(task="Research web trends"),
    )

    learner = _build_learner(
        config,
        trace_repository,
        capability_repository,
        metrics_repository,
        audit_repository,
        execution_repository,
        dummy_database,
    )

    skill = learner.learn(trace_id)

    relearned = learner.relearn(str(skill.id))

    assert relearned.id == skill.id
    assert relearned.workflow["steps"]

    assert any(log["action"] == "RELEARNED" for log in audit_repository.logs)


def test_learner_without_embeddings_still_learns(
    config,
    trace_repository,
    capability_repository,
    metrics_repository,
    audit_repository,
    execution_repository,
    dummy_database,
):
    trace_id = add_trace(trace_repository, make_raw_trace(task="Data cleanup"))

    learner = _build_learner(
        config,
        trace_repository,
        capability_repository,
        metrics_repository,
        audit_repository,
        execution_repository,
        dummy_database,
        provider=None,
    )

    skill = learner.learn(trace_id)

    assert skill.status == SkillStatus.CANDIDATE
    assert skill.embedding == []