"""
Smoke tests for the SkillGenie engine composition.
"""

from unittest.mock import Mock


def test_engine_constructs_with_dummy_database(tmp_path):
    from skillgenie.core.engine import SkillGenie

    database = Mock()

    engine = SkillGenie(
        config_file=str(tmp_path / "config.json"),
        database=database,
        embeddings_enabled=False,
    )

    assert engine.capabilities is not None
    assert engine.traces is not None
    assert engine.metrics is not None
    assert engine.audit is not None
    assert engine.executions is not None
    assert engine.recommendations is not None
    assert engine.store is not None
    assert engine.learner is not None
    assert engine.evaluator is not None
    assert engine.lifecycle is not None
    assert engine.recommender is not None
    assert engine.evolution is not None
    assert engine.execution_service is not None
    assert engine.graph_builder is not None
    assert engine.outcomes is not None
    assert engine.feedback is not None
    assert engine.governance is not None

    engine.shutdown()

    database.close.assert_called_once()


def test_engine_health_overview_empty(tmp_path):
    from skillgenie.core.engine import SkillGenie
    from tests.conftest import FakeCapabilityRepository

    database = Mock()

    engine = SkillGenie(
        config_file=str(tmp_path / "config.json"),
        database=database,
        embeddings_enabled=False,
    )

    # Swap the real repository for an in-memory one so list() works.
    fake = FakeCapabilityRepository()

    database.get_session.side_effect = AssertionError(
        "Should not hit the database."
    )

    engine.capabilities = fake
    engine.store = engine.store
    engine.store._repository = fake

    overview = engine.health_overview()

    assert overview["total_skills"] == 0
    assert overview["statuses"] == {}
    assert overview["health"]["GOOD"] == 0


def test_engine_governance_report(tmp_path):
    from skillgenie.core.engine import SkillGenie

    engine = SkillGenie(
        config_file=str(tmp_path / "config.json"),
        database=Mock(),
        embeddings_enabled=False,
    )

    report = engine.governance_report()

    assert "telemetry_enabled" in report
    assert "data_residency" in report
    assert "vault_secrets" in report

    engine.shutdown()


def test_engine_redact(tmp_path):
    from skillgenie.core.engine import SkillGenie

    engine = SkillGenie(
        config_file=str(tmp_path / "config.json"),
        database=Mock(),
        embeddings_enabled=False,
    )

    redacted = engine.redact("email me at user@example.com")

    assert "user@example.com" not in redacted
    assert "EMAIL_REDACTED" in redacted

    engine.shutdown()