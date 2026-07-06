# ============================================================================
# Project      : SkillGenie
# File         : trace.py
# Description  : Execution trace model.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from skillgenie.constants import ExecutionStatus


class Trace(BaseModel):
    """
    Represents an execution trace captured from an AI agent.
    """

    # Pydantic configuration
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    # Identity
    id: UUID = Field(default_factory=uuid4)

    # Trace Information
    trace_name: str
    agent_framework: str
    task_description: str

    # Execution Details
    execution_status: ExecutionStatus
    execution_time_ms: float

    # Complete execution trace
    trace: dict[str, Any] = Field(default_factory=dict)

    # Additional metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Audit
    created_at: datetime = Field(default_factory=datetime.utcnow)