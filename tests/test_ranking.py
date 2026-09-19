"""
Tests for the learned ranking layer.
"""

from datetime import datetime, timedelta

from skillgenie.core.ranking import LearnedRanker
from skillgenie.core.recommender import SkillRecommender
from skillgenie.storage.skill_store import SkillStore
from tests.conftest import make_capability


def _candidate(skill, ranking=0.8):
    return {
        "skill": skill,
        "similarity": 0.9,
        "ranking": ranking,
        "confidence_score": skill.confidence_score,
        "quality_score": skill.quality_score,
        "type": "SIMILAR",
        "reason": "matches",
    }


def _skills():
    alpha = make_capability(
        name="Alpha",
        confidence_score=0.9,
        avg_latency_ms=120.0,
        updated_at=datetime.utcnow(),
    )
    beta = make_capability(
        name="Beta",
        confidence_score=0.5,
        avg_latency_ms=400.0,
        updated_at=datetime.utcnow() - timedelta(days=30),
    )
    return alpha, beta


def test_classic_mode_keeps_order(config):
    alpha, beta = _skills()
    ranker = LearnedRanker(config)
    ranker._mode = "classic"

    candidates = ranker.reorder([_candidate(alpha, 0.9), _candidate(beta, 0.6)])

    assert candidates[0]["skill"].name == "Alpha"
    assert "learned_score" not in candidates[0]


def test_bandit_ranks_good_outcomes_first(config, outcome_repository):
    alpha, beta = _skills()

    for _ in range(10):
        outcome_repository.create(
            outcome_id=alpha.id,
            capability_id=beta.id,
            recommendation_id=None,
            outcome="SUCCESS",
            latency_ms=100.0,
            rating=None,
            metadata={},
        )

    config.set("ranking.mode", "bandit")
    ranker = LearnedRanker(config, outcome_repository=outcome_repository)

    candidates = ranker.reorder([_candidate(alpha, 0.9), _candidate(beta, 0.6)])

    assert candidates[0]["skill"].name == "Beta"
    assert round(candidates[0]["learned_score"], 4) == round(11 / 12, 4)


def test_bandit_neutral_without_outcomes(config):
    alpha, beta = _skills()
    config.set("ranking.mode", "bandit")
    ranker = LearnedRanker(config, outcome_repository=None)

    candidates = ranker.reorder([_candidate(alpha, 0.9), _candidate(beta, 0.6)])

    assert candidates[0]["skill"].name == "Alpha"
    assert candidates[0]["learned_score"] == 0.5


def test_hybrid_adds_context(config, outcome_repository):
    alpha, beta = _skills()
    ranker = LearnedRanker(config, outcome_repository=outcome_repository)

    candidates = ranker.reorder([_candidate(alpha, 0.9), _candidate(beta, 0.6)])

    assert "context" in candidates[0]
    assert candidates[0]["context"]["mode"] == "hybrid"
    assert "bandit_mean" in candidates[0]["context"]
    assert "recency_score" in candidates[0]["context"]
    assert 0.0 <= candidates[0]["learned_score"] <= 1.0


def test_recency_decays(config):
    alpha, beta = _skills()
    ranker = LearnedRanker(config, outcome_repository=None)

    assert ranker._recency_score(alpha) >= ranker._recency_score(beta)


def test_recommendation_defaults_to_hybrid_ranking(config, outcome_repository):
    ranker = LearnedRanker(config, outcome_repository=outcome_repository)

    assert ranker.mode == "hybrid"
    assert ranker.enabled is True


def test_recommend_uses_learned_order(
    config,
    capability_repository,
    recommendation_repository,
    outcome_repository,
    trace_repository,
    dummy_database,
):
    alpha = make_capability(
        name="Alpha Skill",
        confidence_score=0.9,
        status="PUBLISHED",
        metadata={
            "search_profile": {"tokens": "Alpha Skill find facts gather data"},
        },
    )
    beta = make_capability(
        name="Beta Skill",
        confidence_score=0.5,
        status="PUBLISHED",
        metadata={
            "search_profile": {"tokens": "Beta Skill find facts gather data"},
        },
    )

    store = SkillStore(
        config=config,
        repository=capability_repository,
        embedding_provider=None,
    )
    store.create(alpha)
    store.create(beta)

    for _ in range(10):
        outcome_repository.create(
            outcome_id=alpha.id,
            capability_id=beta.id,
            recommendation_id=None,
            outcome="SUCCESS",
            latency_ms=100.0,
            rating=None,
            metadata={},
        )

    config.set("ranking.mode", "bandit")

    recommender = SkillRecommender(
        config=config,
        database=dummy_database,
        store=store,
        recommendation_repository=recommendation_repository,
        trace_repository=trace_repository,
        outcome_repository=outcome_repository,
    )

    recommendations = recommender.recommend("find facts", top_k=5)

    assert len(recommendations) == 2
    assert str(recommendations[0].capability_id) == str(beta.id)
    assert recommendations[0].ranking_score > 0.8