# ============================================================================
# Project      : SkillGenie
# File         : recommendation.py
# Description  : Capability recommendation model.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from datetime import datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from skillgenie.constants import RecommendationType


class Recommendation(BaseModel):
    """
    Represents a recommended capability for a given task.
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

    # Recommendation Details
    recommendation_type: RecommendationType
    confidence_score: float = 0.0
    similarity_score: float = 0.0
    ranking_score: float = 0.0

    # Reason for recommendation
    reason: str = ""

    # Recommendation metadata
    metadata: dict = Field(default_factory=dict)

    # Audit
    recommended_at: datetime = Field(default_factory=datetime.utcnow)