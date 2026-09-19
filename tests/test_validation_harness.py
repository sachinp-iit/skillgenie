"""
Tests for the skill validation harness.
"""

from unittest.mock import MagicMock

import pytest

from skillgenie.core.validator import SkillValidator
from skillgenie.exceptions import CapabilityNotFoundError
from tests.conftest import FakeCapabilityRepository, make_capability


@pytest.fixture
def engine(tmp_path):
    from unittest.mock import Mock

    from skillgenie.core.engine import SkillGenie

    database = Mock()

    skillgenie = SkillGenie(
        config_file=str(tmp_path / "config.json"),
        database=database,
        embeddings_enabled=False,
    )

    fake = FakeCapabilityRepository()

    database.get_session.side_effect = AssertionError(
        "Should not hit the database."
    )

    skillgenie.capabilities = fake
    skillgenie.store._repository = fake

    yield skillgenie

    skillgenie.shutdown()


def test_complete_skill_is_ready(config):
    skill = make_capability(
        name="Web Researcher",
        status="PUBLISHED",
        usage_count=5,
        success_rate=1.0,
        avg_latency_ms=150.0,
    )

    report = SkillValidator(config).validate(skill)

    assert report["verdict"] == "READY"
    assert report["readiness_score"] >= 0.8
    assert report["skill_name"] == "Web Researcher"


def test_incomplete_skill_is_invalid(config):
    skill = make_capability(
        name="Broken",
        description="",
        workflow={},
        metadata={},
    )

    report = SkillValidator(config).validate(skill)

    assert report["verdict"] == "INVALID"
    check_ids = [check["id"] for check in report["checks"]]
    assert "workflow_steps" in check_ids
    assert report["actionable"]


def test_partial_skill_needs_work(config):
    skill = make_capability(
        name="Draft",
        description="A short description for a draft skill.",
        workflow={
            "name": "Draft",
            "steps": [{"order": 1, "name": "do", "tool": "run", "output": {}}],
        },
        metadata={
            "tools": [],
            "search_profile": {},
        },
    )

    report = SkillValidator(config).validate(skill)

    assert report["verdict"] == "NEEDS_WORK"
    assert 0.5 <= report["readiness_score"] < 0.9


def test_unknown_tool_triggers_warning(config):
    skill = make_capability(
        name="Tool Mismatch",
        description="A skill whose workflow references an undeclared tool.",
        workflow={
            "name": "Tool Mismatch",
            "framework": "custom",
            "steps": [
                {"order": 1, "name": "run", "tool": "ghost_tool", "output": {}},
            ],
        },
    )

    report = SkillValidator(config).validate(skill)

    checks = {
        check["id"]: check["status"] for check in report["checks"]
    }
    assert checks.get("workflow_tools_known") == "WARN"


def test_engine_validate_skill_raises_for_missing(engine):
    from uuid import uuid4

    try:
        engine.validate_skill(uuid4())
    except CapabilityNotFoundError:
        return

    raise AssertionError("Expected CapabilityNotFoundError")


def test_engine_validate_skill_returns_report(engine):
    skill = make_capability(
        name="Engine Check",
        description="A fully formed skill for engine-level validation.",
        status="PUBLISHED",
        usage_count=3,
        success_rate=1.0,
        avg_latency_ms=200.0,
    )
    engine.store.create(skill)

    report = engine.validate_skill(skill.id)

    assert report["skill_id"] == str(skill.id)
    assert "checks" in report
    assert report["readiness_score"] >= 0.8


def test_cli_validate_prints_verdict(capsys):
    skill = make_capability()
    engine = MagicMock()
    engine.validate_skill.return_value = {
        "skill_name": "Web Research",
        "verdict": "READY",
        "readiness_score": 0.9,
        "checks": [],
        "actionable": [],
    }

    from skillgenie.cli.main import cmd_validate

    cmd_validate(
        type("A", (), {"skill_id": str(skill.id)})(),
        engine,
    )

    output = capsys.readouterr().out

    assert "READY" in output