"""
Tests for skill scoring (confidence, quality, similarity, ranking, overall).
"""

from math import isclose

import pytest

from skillgenie.core.scorer import SkillScorer
from tests.conftest import make_capability


@pytest.fixture
def scorer(config):
    return SkillScorer(config)


def test_confidence_full_artifacts(scorer):
    skill = make_capability(usage_count=0)

    score = scorer.confidence_score(skill)

    assert score == 0.9  # workflow + tools + prompts + input_output


def test_confidence_minimal(scorer):
    skill = make_capability(workflow={}, metadata={}, usage_count=0)

    assert scorer.confidence_score(skill) == 0.0


def test_confidence_usage_boost(scorer):
    skill = make_capability(usage_count=5)

    assert scorer.confidence_score(skill) == 1.0


def test_quality_score(scorer):
    skill = make_capability()

    assert scorer.quality_score(skill) > 0.9


def test_quality_low_information(scorer):
    skill = make_capability(
        description="x",
        category="",
        workflow={"steps": []},
        relationship_graph={},
        metadata={},
        usage_count=0,
    )

    score = scorer.quality_score(skill)

    assert 0.0 <= score < 0.5


def test_similarity_identical(scorer):
    embedding = [1.0, 0.0, 0.0]
    same = [1.0, 0.0, 0.0]

    assert scorer.similarity_score(embedding, same) == 1.0

    orthogonal = [0.0, 1.0, 0.0]

    assert scorer.similarity_score(embedding, orthogonal) == 0.0


def test_similarity_dimension_mismatch(scorer):
    with pytest.raises(ValueError):
        scorer.similarity_score([1.0], [1.0, 2.0])


def test_similarity_empty(scorer):
    assert scorer.similarity_score([], [1.0]) == 0.0


def test_ranking_score_bounds(scorer):
    assert scorer.ranking_score(1.0, 1.0, 1.0) == 1.0
    assert scorer.ranking_score(0.0, 0.0, 0.0) == 0.0

    mid = scorer.ranking_score(0.5, 0.5, 0.5)

    assert isclose(mid, 0.5, rel_tol=1e-3)


def test_overall_score(scorer):
    skill = make_capability()

    score = scorer.overall_score(skill)

    expected = (
        0.4 * scorer.confidence_score(skill)
        + 0.4 * scorer.quality_score(skill)
        + 0.2 * min(skill.success_rate, 1.0)
    )

    assert isclose(score, round(expected, 3), rel_tol=1e-3)