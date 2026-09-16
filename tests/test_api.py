"""
Tests for the FastAPI layer using an injected mock engine.
"""

from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from skillgenie.api.app import create_app
from skillgenie.api.dependencies import clear_engine
from tests.conftest import make_capability


@pytest.fixture
def mock_engine():
    from uuid import uuid4

    from skillgenie.config import Config
    from skillgenie.models.outcome import Outcome

    engine = Mock()

    engine.store = Mock()
    engine.traces = Mock()
    engine.metrics = Mock()
    engine.audit = Mock()
    engine.executions = Mock()
    engine.capabilities = Mock()
    engine.learner = Mock()
    engine.evaluator = Mock()
    engine.lifecycle = Mock()
    engine.recommender = Mock()
    engine.outcomes = Mock()
    engine.outcomes.list.return_value = []
    engine.config = Config("config/config.json")
    engine.governance = Mock()
    engine.governance.vault = Mock()
    engine.governance.vault.list_names.return_value = []
    engine.detect_drift.return_value = None
    engine.recent_failures.return_value = []
    engine.health_explanation.return_value = {}
    engine.record_outcome.return_value = Outcome(
        id=uuid4(),
        capability_id=uuid4(),
        recommendation_id=None,
        outcome="SUCCESS",
        latency_ms=120.0,
        rating=5,
        metadata={},
    )

    return engine


@pytest.fixture
def client(mock_engine):
    app = create_app(engine=mock_engine)

    with TestClient(app) as test_client:
        yield test_client

    clear_engine()


def test_health_endpoint(client):
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_landing_page(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "SkillGenie" in response.text


def test_admin_dashboard(client):
    response = client.get("/admin")

    assert response.status_code == 200
    assert "SkillGenie" in response.text


def test_monitor_dashboard(client):
    response = client.get("/monitor")

    assert response.status_code == 200
    assert "SkillGenie" in response.text


def test_list_skills(client, mock_engine):
    mock_engine.store.list.return_value = [make_capability()]

    response = client.get("/api/v1/skills")

    assert response.status_code == 200

    payload = response.json()

    assert len(payload) == 1
    assert payload[0]["name"] == "Web Research"


def test_get_skill_not_found(client, mock_engine):
    mock_engine.store.get.return_value = None

    response = client.get("/api/v1/skills/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_learn_endpoint(client, mock_engine):
    mock_engine.learn.return_value = make_capability()

    response = client.post(
        "/api/v1/learn",
        json={"trace_id": "00000000-0000-0000-0000-000000000001"},
    )

    assert response.status_code == 201

    assert response.json()["name"] == "Web Research"


def test_create_trace(client, mock_engine):
    response = client.post(
        "/api/v1/traces",
        json={
            "trace_name": "Research",
            "agent_framework": "custom",
            "task_description": "Research a topic",
            "execution_status": "SUCCESS",
            "execution_time_ms": 10.0,
            "metadata": {},
        },
    )

    assert response.status_code == 201

    assert "trace_id" in response.json()

    mock_engine.traces.create.assert_called_once()


def test_recommend_endpoint(client, mock_engine):
    from skillgenie.constants import RecommendationType
    from skillgenie.models.recommendation import Recommendation
    from uuid import uuid4

    mock_engine.recommend.return_value = [
        Recommendation(
            capability_id=uuid4(),
            recommendation_type=RecommendationType.SIMILAR,
            similarity_score=0.9,
            ranking_score=0.85,
            reason="matches",
        )
    ]

    response = client.post(
        "/api/v1/recommend",
        json={"query": "search the web", "top_k": 5},
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload[0]["recommendation_type"] == "SIMILAR"


def test_monitor_overview(client, mock_engine):
    mock_engine.health_overview.return_value = {
        "total_skills": 3,
        "statuses": {"PUBLISHED": 2},
        "health": {"GOOD": 3},
    }

    response = client.get("/api/v1/monitor/overview")

    assert response.status_code == 200
    assert response.json()["total_skills"] == 3


def test_lifecycle_action(client, mock_engine):
    skill = make_capability()

    mock_engine.store.get.return_value = skill

    response = client.post(f"/api/v1/skills/{skill.id}/approve")

    assert response.status_code == 200

    mock_engine.lifecycle.approve.assert_called_once_with(str(skill.id))


def test_metrics_history(client, mock_engine):
    mock_engine.metrics.get_by_capability.return_value = []

    response = client.get(
        "/api/v1/metrics/skills/00000000-0000-0000-0000-000000000001"
    )

    assert response.status_code == 200
    assert response.json() == []


def test_record_outcome(client, mock_engine):
    response = client.post(
        "/api/v1/outcomes",
        json={
            "capability_id": "00000000-0000-0000-0000-000000000001",
            "outcome": "SUCCESS",
            "latency_ms": 120.0,
        },
    )

    assert response.status_code == 201


def test_list_outcomes(client, mock_engine):
    response = client.get("/api/v1/outcomes")

    assert response.status_code == 200
    assert response.json() == []


def test_skill_drift(client, mock_engine):
    response = client.get(
        "/api/v1/skills/00000000-0000-0000-0000-000000000001/drift"
    )

    assert response.status_code == 200
    assert response.json()["drift_detected"] is False


def test_skill_failures(client, mock_engine):
    response = client.get(
        "/api/v1/skills/00000000-0000-0000-0000-000000000001/failures"
    )

    assert response.status_code == 200
    assert response.json() == []


def test_skill_health_explanation(client, mock_engine):
    mock_engine.health_explanation.return_value = {"score": 0.91}

    response = client.get(
        "/api/v1/skills/00000000-0000-0000-0000-000000000001/health/explain"
    )

    assert response.status_code == 200
    assert response.json()["score"] == 0.91


def test_export_skill(client, mock_engine):
    skill = make_capability()

    mock_engine.store.get.return_value = skill

    response = client.get(f"/api/v1/export/{skill.id}")

    assert response.status_code == 200

    payload = response.json()

    assert "skillgenie" in payload
    assert payload["name"] == skill.name.lower().replace(" ", "_")


def test_set_secret(client, mock_engine):
    response = client.post(
        "/api/v1/governance/secrets",
        json={"name": "api_key", "value": "sk-123"},
    )

    assert response.status_code == 201
    assert response.json()["stored"] is True

    mock_engine.governance.vault.set.assert_called_once_with(
        "api_key", "sk-123"
    )


def test_list_secrets(client, mock_engine):
    mock_engine.governance.vault.list_names.return_value = ["api_key"]

    response = client.get("/api/v1/governance/secrets")

    assert response.status_code == 200
    assert response.json()["names"] == ["api_key"]


def test_monitor_governance(client, mock_engine):
    mock_engine.governance_report.return_value = {
        "telemetry_enabled": True,
        "data_residency": "self-hosted",
        "vault_secrets": [],
    }

    response = client.get("/api/v1/monitor/governance")

    assert response.status_code == 200
    assert response.json()["data_residency"] == "self-hosted"