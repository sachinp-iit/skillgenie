# ============================================================================
# Project      : SkillGenie
# File         : trace_validator.py
# Description  : Validation contracts for raw execution traces and skill
#                inputs.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from skillgenie.constants import SkillStatus


class RawTraceIn(BaseModel):
    """
    Minimal validation for a raw inbound execution trace.
    """

    model_config = ConfigDict(extra="allow")

    trace_name: str | None = None
    agent_framework: str = "custom"
    task_description: str | None = None
    execution_status: str = "SUCCESS"
    execution_time_ms: float = 0.0

    @field_validator("agent_framework")
    @classmethod
    def normalize_framework(cls, value: str) -> str:
        return value.lower()

    @field_validator("execution_status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        return value.upper()


class SkillStatusIn(BaseModel):
    """
    Payload for lifecycle transitions.
    """

    status: SkillStatus
    reason: str | None = None


class SkillEvaluationIn(BaseModel):
    """
    Payload for evaluation requests.
    """

    skill_id: str
    auto_approve: bool | None = None


class TraceIngestResult(BaseModel):
    """
    Result of ingesting a raw trace.
    """

    trace_id: str
    trace_name: str | None = None
    agent_framework: str
    valid: bool = False
    errors: list[str] = Field(default_factory=list)

    def add_error(self, message: str) -> None:
        self.errors.append(message)
        self.valid = False


def validate_trace_structure(trace: dict[str, Any]) -> list[str]:
    """
    Structural validation of a raw trace dictionary.

    Returns a list of error messages (empty when valid).
    """

    errors: list[str] = []

    if "task" not in trace and "task_description" not in trace:
        errors.append("Trace is missing a task/task_description.")

    steps = trace.get("steps")

    if steps is not None and not isinstance(steps, list):
        errors.append("Trace 'steps' must be a list.")

    tools = trace.get("tools")

    if tools is not None and not isinstance(tools, list):
        errors.append("Trace 'tools' must be a list.")

    prompts = trace.get("prompts")

    if prompts is not None and not isinstance(prompts, list):
        errors.append("Trace 'prompts' must be a list.")

    return errors