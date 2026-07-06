# ============================================================================
# Project      : SkillGenie
# File         : metrics.py
# Description  : Capability metrics model.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Metrics(BaseModel):
    """
    Represents capability performance metrics.
    """

    # Pydantic configuration
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    # Identity
    id: UUID = Field(default_factory=uuid4)

    # Capability Reference
    capability_id: UUID

    # Scores
    confidence_score: float = 0.0
    quality_score: float = 0.0
    success_rate: float = 0.0

    # Runtime
    avg_latency_ms: float = 0.0
    usage_count: int = 0

    # Audit
    recorded_at: datetime = Field(default_factory=datetime.utcnow)