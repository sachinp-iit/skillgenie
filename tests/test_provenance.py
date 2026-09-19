"""
Tests for the provenance & explainability service.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from skillgenie.core.provenance import SkillProvenance
from tests.conftest import make_capability


@pytest.fixture
def engine(tmp_path):
    from unittest.mock import Mock

    from skillgenie.core.engine import SkillGenie

    from tests.conftest import FakeCapabilityRepository

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


def test_provenance_links_traces_audit_and_outcomes(
    config,
    store,
    trace_repository,
    audit_repository,
    outcome_repository,
):
    trace_id = uuid4()

    skill = make_capability(
        name="Web Researcher",
        description="search the web and summarize results",
        category="research",
        status="PUBLISHED",
        created_from=[str(trace_id)],
    )
    store.create(skill)

    trace_repository.create(
        trace_id=trace_id,
        trace_name="Research task",
        agent_framework="custom",
        task_description="search the web and summarize results",
        execution_status="SUCCESS",
        execution_time_ms=250.0,
        trace={},
        metadata={},
    )

    audit_repository.create(
        audit_id=uuid4(),
        capability_id=skill.id,
        action="APPROVED",
        performed_by="alice",
        remarks="looks good",
        payload={},
    )

    outcome_repository.create(
        outcome_id=uuid4(),
        capability_id=skill.id,
        recommendation_id=None,
        outcome="SUCCESS",
        latency_ms=100.0,
        rating=None,
        metadata={},
        created_at=datetime.utcnow(),
    )

    provenance = SkillProvenance(
        config=config,
        store=store,
        audit_repository=audit_repository,
        outcome_repository=outcome_repository,
        trace_repository=trace_repository,
    )

    dossier = provenance.provenance(skill.id)

    assert dossier["skill_id"] == str(skill.id)
    assert dossier["origin"]["source_traces"][0]["trace_name"] == "Research task"
    assert any(
        event["action"] == "APPROVED"
        for event in dossier["attribution"]["audit_events"]
    )
    assert dossier["attribution"]["outcomes"]["total"] == 1
    assert dossier["attribution"]["outcomes"]["success_rate"] == 1.0
    assert "learned from 1 observed trace(s)" in dossier[
        "explainability"
    ]["narrative"]
    assert dossier["explainability"]["confidence_reason"]
    assert dossier["explainability"]["quality_reason"]


def test_provenance_unknown_skill_raises_value_error(
    config,
    store,
):
    provenance = SkillProvenance(
        config=config,
        store=store,
    )

    with pytest.raises(ValueError):
        provenance.provenance(uuid4())


def test_engine_provenance_wiring(
    engine,
    trace_repository,
    audit_repository,
    outcome_repository,
):
    skill = make_capability(
        name="Lineage Skill",
        description="A skill created to verify provenance wiring.",
        category="research",
        status="PUBLISHED",
        created_from=[str(uuid4())],
    )
    engine.store.create(skill)

    engine.provenance._trace_repository = trace_repository
    engine.provenance._audit_repository = audit_repository
    engine.provenance._outcome_repository = outcome_repository

    dossier = engine.skill_provenance(skill.id)

    assert dossier["skill_name"] == "Lineage Skill"
    assert "narrative" in dossier["explainability"]


def test_engine_provenance_missing_skill_raises(engine):
    from skillgenie.exceptions import CapabilityNotFoundError

    with pytest.raises(CapabilityNotFoundError):
        engine.skill_provenance(uuid4())