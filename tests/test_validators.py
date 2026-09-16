"""
Tests for validation contracts.
"""

import pytest
from pydantic import ValidationError

from skillgenie.constants import SkillStatus
from skillgenie.validators import (
    RawTraceIn,
    SkillEvaluationIn,
    SkillStatusIn,
    TraceIngestResult,
    validate_trace_structure,
)


def test_raw_trace_normalization():
    raw = RawTraceIn(
        trace_name="Research",
        agent_framework="LangGraph",
        execution_status="success",
    )

    assert raw.agent_framework == "langgraph"
    assert raw.execution_status == "SUCCESS"
    assert raw.execution_time_ms == 0.0


def test_raw_trace_defaults():
    raw = RawTraceIn()

    assert raw.agent_framework == "custom"
    assert raw.execution_status == "SUCCESS"


def test_skill_status_in():
    payload = SkillStatusIn(status=SkillStatus.PUBLISHED)

    assert payload.status == SkillStatus.PUBLISHED
    assert payload.reason is None

    with pytest.raises(ValidationError):
        SkillStatusIn(status="NOT_A_STATUS")


def test_skill_evaluation_in():
    payload = SkillEvaluationIn(skill_id="abc-123")

    assert payload.auto_approve is None


def test_trace_ingest_result():
    result = TraceIngestResult(trace_id="t1", agent_framework="custom")

    assert result.valid is False
    assert result.errors == []

    result.add_error("boom")

    assert result.valid is False
    assert result.errors == ["boom"]


def test_validate_trace_structure():
    assert validate_trace_structure({"task": "x"}) == []

    errors = validate_trace_structure({"steps": "nope"})

    assert any("steps" in error for error in errors)

    missing = validate_trace_structure({})

    assert missing == ["Trace is missing a task/task_description."]