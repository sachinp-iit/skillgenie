"""
Tests for the skill health engine.
"""

import pytest

from skillgenie.constants import SkillHealth
from skillgenie.core.health import SkillHealthEngine
from tests.conftest import make_capability


@pytest.fixture
def health(config):
    return SkillHealthEngine(config)


def test_excellent_health(health):
    skill = make_capability(
        success_rate=1.0,
        avg_latency_ms=50.0,
        usage_count=100,
    )

    assert health.health(skill) == SkillHealth.EXCELLENT


def test_good_health(health):
    skill = make_capability(success_rate=0.9, avg_latency_ms=200.0)

    assert health.health(skill) in {SkillHealth.EXCELLENT, SkillHealth.GOOD}


def test_fair_health(health):
    skill = make_capability(
        success_rate=0.3,
        avg_latency_ms=900.0,
    )

    assert health.health(skill) == SkillHealth.FAIR


def test_poor_health(health):
    skill = make_capability(
        confidence_score=0.4,
        quality_score=0.4,
        success_rate=0.1,
        avg_latency_ms=2000.0,
    )

    assert health.health(skill) == SkillHealth.POOR


def test_health_score_bounds(health):
    skill = make_capability(success_rate=0.5, avg_latency_ms=500.0)

    score = health.health_score(skill)

    assert 0.0 <= score <= 1.0


def test_degraded(health):
    good = make_capability(
        success_rate=0.99,
        avg_latency_ms=10.0,
    )

    bad = make_capability(
        confidence_score=0.4,
        quality_score=0.4,
        success_rate=0.1,
        avg_latency_ms=5000.0,
    )

    assert health.degraded(good) is False
    assert health.degraded(bad) is True


def test_latency_score(health):
    assert health._latency_score(0) == 0.8
    assert health._latency_score(200) > health._latency_score(2000)


def test_float_value_coercion(health):
    assert health._float_value(None) == 0.0
    assert health._float_value("12.5") == 12.5
    assert health._float_value("") == 0.0