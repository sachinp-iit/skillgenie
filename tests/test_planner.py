"""
Tests for the compositional planner.
"""

from skillgenie.core.recommender import SkillRecommender
from skillgenie.planning.composer import (
    SimulatedRunner,
    SkillComposer,
    TaskDecomposer,
)
from tests.conftest import make_capability


def _seed_skills(store):
    searcher = make_capability(
        name="Web Searcher",
        status="PUBLISHED",
        category="research",
        description="search the web for facts and pages",
        metadata={
            "search_profile": {
                "tokens": "Web Searcher search the web for facts and pages",
            }
        },
    )
    summarizer = make_capability(
        name="Summarizer",
        status="PUBLISHED",
        category="research",
        description="summarize the results into a report",
        metadata={
            "search_profile": {
                "tokens": "Summarizer summarize the results into a report",
            }
        },
    )
    store.create(searcher)
    store.create(summarizer)
    return searcher, summarizer


def _recommender(config, store, recommendation_repository):
    return SkillRecommender(
        config=config,
        database=object(),
        store=store,
        recommendation_repository=recommendation_repository,
        trace_repository=None,
    )


def _composer(store, config, recommendation_repository):
    return SkillComposer(
        config=config,
        store=store,
        recommender=_recommender(
            config, store, recommendation_repository
        ),
    )


def test_decomposer_splits_on_then():
    subtasks = TaskDecomposer().split(
        "search the web then summarize the results"
    )

    assert subtasks == ["search the web", "summarize the results"]


def test_decomposer_splits_on_and_when_substantial():
    subtasks = TaskDecomposer().split(
        "fetch product data and write a report"
    )

    assert subtasks == ["fetch product data", "write a report"]


def test_decomposer_keeps_short_noun_phrases_together():
    subtasks = TaskDecomposer().split("research and development")

    assert len(subtasks) == 1
    assert subtasks[0] == "research and development"


def test_compose_chains_skills(
    store, config, recommendation_repository
):
    searcher, summarizer = _seed_skills(store)

    composer = _composer(store, config, recommendation_repository)

    plan = composer.compose(
        "search the web then summarize the results",
        top_k=3,
    )

    assert len(plan.steps) == 2
    assert all(step.matched for step in plan.steps)
    assert set(step.skill_name for step in plan.steps) == {
        "Web Searcher",
        "Summarizer",
    }
    assert plan.status == "READY"

    assert searcher.id in [step.skill_id for step in plan.steps]
    assert summarizer.id in [step.skill_id for step in plan.steps]


def test_compose_marks_unmatched_steps(
    store, config, recommendation_repository
):
    _seed_skills(store)

    composer = _composer(store, config, recommendation_repository)

    plan = composer.compose("search the web then paint a fence", top_k=3)

    assert len(plan.steps) == 2
    assert any(not step.matched for step in plan.steps)
    assert plan.status == "PARTIAL"


def test_execute_uses_runner(
    store, config, recommendation_repository
):
    searcher, _ = _seed_skills(store)

    composer = _composer(store, config, recommendation_repository)

    plan = composer.compose("search the web", top_k=3)

    result = composer.execute(plan)

    assert result.success is True
    assert len(result.steps) == 1
    assert result.steps[0].skill_id == searcher.id


def test_learn_creates_composite(
    store, config, recommendation_repository
):
    searcher, summarizer = _seed_skills(store)

    composer = _composer(store, config, recommendation_repository)

    plan = composer.compose(
        "search the web then summarize the results",
        top_k=3,
    )
    result = composer.execute(plan)
    composite = composer.learn(result)

    assert composite is not None
    assert composite.metadata.get("composite") is True

    children = composite.relationship_graph.get("children", [])
    assert str(searcher.id) in children
    assert str(summarizer.id) in children

    stored = store.get(composite.id)
    assert stored is not None
    assert stored.name == "Search The Web Then Summarize"


def test_learn_skips_failed_plan(
    store, config, recommendation_repository
):
    _seed_skills(store)

    composer = _composer(store, config, recommendation_repository)

    plan = composer.compose("search the web then paint a fence", top_k=3)
    result = composer.execute(plan)

    assert composer.learn(result) is None


def test_simulated_runner_success(store):
    skill = make_capability(
        name="Web Searcher",
        metadata={
            "search_profile": {
                "tokens": "Web Searcher search the web for facts",
            }
        },
    )

    runner = SimulatedRunner(store)

    outcome = runner.run(skill, "search the web")

    assert outcome["success"] is True
    assert outcome["latency_ms"] > 0


def test_simulated_runner_mismatch(store):
    skill = make_capability(
        name="Web Searcher",
        metadata={
            "search_profile": {"tokens": "search the web"},
        }
    )

    runner = SimulatedRunner(store)

    outcome = runner.run(skill, "cook a five course meal")

    assert outcome["success"] is False