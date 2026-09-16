# ============================================================================
# Project      : SkillGenie
# File         : outcome.py
# Description  : Outcome model representing a recommendation outcome event
#                (whether a recommended skill succeeded or failed in use).
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class Outcome(BaseModel):
    """
    Records the real-world result of using a recommended skill.
    """

    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    id: UUID = Field(default_factory=uuid4)
    capability_id: UUID
    recommendation_id: UUID | None = None
    outcome: str = "SUCCESS"
    latency_ms: float = 0.0
    rating: float | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)