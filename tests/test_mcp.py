"""
Tests for the MCP server and skill export.
"""

from unittest.mock import Mock

from skillgenie.mcp.server import SkillGenieMCPServer
from tests.conftest import FakeRecommendationRepository, make_capability, make_skill


def _mock_engine(config):
    engine = Mock()

    store = Mock()
    skill = make_capability(status="PUBLISHED", name="Web Fetcher")
    store.get.return_value = skill
    store.search.return_value = [
        {
            "skill": skill,
            "similarity": 0.95,
            "type": "EXACT",
            "ranking": 0.91,
            "reason": "matches",
        }
    ]
    store.list.return_value = [skill]
    engine.store = store

    recommendation = Mock()
    recommendation.capability_id = "abc-123"
    recommendation.metadata = {"skill_name": "Web Fetcher"}
    recommendation.recommendation_type.value = "EXACT"
    recommendation.confidence_score = 0.9
    recommendation.similarity_score = 0.95
    recommendation.ranking_score = 0.91
    recommendation.reason = "matches"
    engine.recommend.return_value = [recommendation]

    engine.config = config
    engine.learn.return_value = skill

    return engine


def _server(config, engine=None):
    return SkillGenieMCPServer(engine=engine or _mock_engine(config))


def test_tools_registered(config):
    server = _server(config)

    names = {tool["name"] for tool in server.tools}

    assert {
        "skillgenie_search",
        "skillgenie_list",
        "skillgenie_recommend",
        "skillgenie_learn",
        "skillgenie_export",
        "skillgenie_health",
    }.issubset(names)


def test_handle_search(config):
    server = _server(config)

    response = server.handle(
        "skillgenie_search",
        {"query": "fetch web pages"},
    )

    assert "result" in response
    assert response["result"][0]["skill_id"] == str(server._engine.store.get("any").id)


def test_handle_recommend(config):
    server = _server(config)

    response = server.handle(
        "skillgenie_recommend",
        {"query": "fetch web pages", "top_k": 3},
    )

    assert "result" in response
    assert response["result"][0]["name"] == "Web Fetcher"


def test_handle_export(config):
    server = _server(config)
    skill = server._engine.store.get.return_value

    response = server.handle("skillgenie_export", {"skill_id": str(skill.id)})

    tool = response["result"]
    assert tool["name"] == "web_fetcher"
    assert tool["skillgenie"]["version"] == "1.0.0"


def test_handle_unknown_method(config):
    server = _server(config)

    response = server.handle("skillgenie_unknown", {})

    assert "error" in response
    assert response["error"]["code"] == -32601


def test_handle_error_returns_error_payload(config):
    engine = _mock_engine(config)
    engine.store.search.side_effect = RuntimeError("db down")
    server = _server(config, engine)

    response = server.handle("skillgenie_search", {"query": "x"})

    assert "error" in response
    assert "db down" in str(response["error"]["message"])