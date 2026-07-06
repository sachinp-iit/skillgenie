# ============================================================================
# Project      : SkillGenie
# File         : execution.py
# Description  : Execution model representing a capability execution event.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from skillgenie.constants import ExecutionStatus


class Execution(BaseModel):
    """
    Represents a single capability execution.
    """

    # Pydantic configuration
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    # Identity
    id: UUID = Field(default_factory=uuid4)

    # References
    capability_id: UUID
    trace_id: UUID | None = None

    # Execution Details
    task_name: str
    execution_status: ExecutionStatus

    # Runtime Metrics
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    execution_time_ms: float = 0.0

    # Inputs & Outputs
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)

    # Error Information
    error_message: str | None = None

    # Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)