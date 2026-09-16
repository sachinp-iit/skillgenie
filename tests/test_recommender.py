"""
Tests for the skill recommender.
"""

from uuid import uuid4

from skillgenie.core.recommender import SkillRecommender
from tests.conftest import make_skill


def _build(
    config,
    capability_repository,
    recommendation_repository,
    trace_repository,
    dummy_database,
):
    from skillgenie.storage.skill_store import SkillStore

    store = SkillStore(
        config=config,
        repository=capability_repository,
        embedding_provider=None,
    )

    return SkillRecommender(
        config=config,
        database=dummy_database,
        store=store,
        recommendation_repository=recommendation_repository,
        trace_repository=trace_repository,
    )


def _seed_skill(repo, *, status="PUBLISHED", name=None, description=None, embedding=None):
    row = make_skill(
        status=status,
        name=name or "Web Research",
        description=description or "Generic task handling skill.",
    )
    if embedding is not None:
        row["embedding"] = embedding

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


def test_recommend_lexical(
    config,
    capability_repository,
    recommendation_repository,
    trace_repository,
    dummy_database,
):
    skill_id = _seed_skill(
        capability_repository,
        name="Web Researcher",
        description="search the web and summarize results",
    )

    recommender = _build(
        config,
        capability_repository,
        recommendation_repository,
        trace_repository,
        dummy_database,
    )

    recommendations = recommender.recommend(
        "search the web",
        top_k=5,
        status="PUBLISHED",
    )

    assert recommendations

    assert str(recommendations[0].capability_id) == str(skill_id)

    persisted = recommendation_repository.get_by_capability(skill_id)

    assert len(persisted) >= 1


def test_recommend_respects_status(
    config,
    capability_repository,
    recommendation_repository,
    trace_repository,
    dummy_database,
):
    _seed_skill(capability_repository, status="CANDIDATE", name="Candidate Skill")

    recommender = _build(
        config,
        capability_repository,
        recommendation_repository,
        trace_repository,
        dummy_database,
    )

    recommendations = recommender.recommend("some query words here", top_k=5)

    assert recommendations == []


def test_recommend_by_trace(
    config,
    capability_repository,
    recommendation_repository,
    trace_repository,
    dummy_database,
):
    _seed_skill(
        capability_repository,
        name="Flight Booker",
        description="book flights and check fares",
    )

    from uuid import uuid4

    trace_id = uuid4()

    trace_repository.create(
        trace_id=trace_id,
        trace_name="Book a flight",
        agent_framework="custom",
        task_description="book flights and check fares",
        execution_status="SUCCESS",
        execution_time_ms=100.0,
        trace={},
        metadata={},
    )

    recommender = _build(
        config,
        capability_repository,
        recommendation_repository,
        trace_repository,
        dummy_database,
    )

    recommendations = recommender.recommend_by_trace(str(trace_id), top_k=5)

    assert recommendations


def test_recommend_by_missing_trace_raises(
    config,
    capability_repository,
    recommendation_repository,
    trace_repository,
    dummy_database,
):
    recommender = _build(
        config,
        capability_repository,
        recommendation_repository,
        trace_repository,
        dummy_database,
    )

    try:
        recommender.recommend_by_trace(str(uuid4()))
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError for a missing trace.")


def test_recommend_similar_excludes_self(
    config,
    capability_repository,
    recommendation_repository,
    trace_repository,
    dummy_database,
):
    same = [1.0, 0.0, 0.0]

    a = _seed_skill(capability_repository, name="Alpha", embedding=same)
    _seed_skill(capability_repository, name="Beta", embedding=[0.9, 0.1, 0.0])

    recommender = _build(
        config,
        capability_repository,
        recommendation_repository,
        trace_repository,
        dummy_database,
    )

    recommendations = recommender.recommend_similar(str(a), top_k=5)

    assert recommendations

    assert all(item.capability_id != a for item in recommendations)


def test_recent(
    config,
    capability_repository,
    recommendation_repository,
    trace_repository,
    dummy_database,
):
    skill_id = _seed_skill(capability_repository, name="Recent Skill", description="x y z words appear here")

    recommender = _build(
        config,
        capability_repository,
        recommendation_repository,
        trace_repository,
        dummy_database,
    )

    recommender.recommend("x y z words appear here", top_k=5)

    recent = recommender.recent()

    assert len(recent) >= 1