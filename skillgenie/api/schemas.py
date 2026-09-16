# ============================================================================
# Project      : SkillGenie
# File         : schemas.py
# Description  : Request / response schemas for the SkillGenie REST API.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TraceCreate(BaseModel):
    """
    Raw trace ingestion payload.
    """

    trace_name: str | None = None
    agent_framework: str = "custom"
    task_description: str | None = None
    execution_status: str = "SUCCESS"
    execution_time_ms: float = 0.0
    trace: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class LearnRequest(BaseModel):
    """
    Trigger learning for a single trace.
    """

    trace_id: str


class RecommendRequest(BaseModel):
    """
    Semantic recommendation request.
    """

    query: str
    top_k: int = 5
    status: str | None = None


class SkillUpdate(BaseModel):
    """
    Partial skill update payload.
    """

    name: str | None = None
    description: str | None = None
    category: str | None = None
    workflow: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class LifecycleRequest(BaseModel):
    """
    Lifecycle transition payload.
    """

    reason: str | None = None


class ExecutionCreate(BaseModel):
    """
    Execution recording payload.
    """

    capability_id: str
    task_name: str
    execution_status: str = "SUCCESS"
    execution_time_ms: float = 0.0
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    trace_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RejectRequest(BaseModel):
    """
    Rejection payload.
    """

    reason: str = ""


class OutcomeCreate(BaseModel):
    """
    Recommendation outcome feedback payload.
    """

    capability_id: str
    outcome: str = "SUCCESS"
    recommendation_id: str | None = None
    latency_ms: float = 0.0
    rating: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SecretSet(BaseModel):
    """
    Vault secret payload.
    """

    name: str
    value: str


class ExportRequest(BaseModel):
    """
    Skill export payload.
    """

    skill_id: str
    format: str = "mcp"