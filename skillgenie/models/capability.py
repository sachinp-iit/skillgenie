# ============================================================================
# Project      : SkillGenie
# File         : capability.py
# Description  : Capability model used throughout the SkillGenie library.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from skillgenie.constants import SkillHealth, SkillStatus


class Capability(BaseModel):
    """
    Represents a learned capability.
    """

    # Pydantic configuration
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid",
    )

    # Identity
    id: UUID = Field(default_factory=uuid4)

    # Basic Information
    name: str
    description: str
    category: str

    # Lifecycle
    version: str = "1.0.0"
    status: SkillStatus = SkillStatus.DRAFT

    # Quality Metrics
    confidence_score: float = 0.0
    quality_score: float = 0.0
    success_rate: float = 0.0

    # Runtime Metrics
    usage_count: int = 0
    avg_latency_ms: float = 0.0

    # Overall Health
    health: SkillHealth = SkillHealth.GOOD

    # Embedding Vector
    embedding: list[float] = Field(default_factory=list)

    # Capability Relationship Graph
    relationship_graph: dict[str, Any] = Field(default_factory=dict)

    # Generated Workflow
    workflow: dict[str, Any] = Field(default_factory=dict)

    # Additional Metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    # Source Execution Trace IDs
    created_from: list[str] = Field(default_factory=list)

    # Audit Fields
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: datetime | None = None