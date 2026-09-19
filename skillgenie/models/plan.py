# ============================================================================
# Project      : SkillGenie
# File         : plan.py
# Description  : Plan models for the compositional planner.  A plan chains
#                multiple skills toward a composite task, and a plan result
#                captures the execution outcome of each step.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class PlanStep(BaseModel):
    """
    A single step in a skill plan.
    """

    model_config = ConfigDict(extra="ignore")

    order: int
    task: str
    skill_id: UUID | None = None
    skill_name: str = ""
    likeness: float = 0.0
    matched: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "order": self.order,
            "task": self.task,
            "skill_id": str(self.skill_id) if self.skill_id else None,
            "skill_name": self.skill_name,
            "likeness": round(self.likeness, 4),
            "matched": self.matched,
        }


class SkillPlan(BaseModel):
    """
    A chained plan of skills for a composite task.
    """

    model_config = ConfigDict(extra="ignore")

    id: UUID = Field(default_factory=uuid4)
    task: str
    steps: list[PlanStep] = Field(default_factory=list)
    status: str = "PLANNED"
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "task": self.task,
            "steps": [step.to_dict() for step in self.steps],
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class StepResult(BaseModel):
    """
    Execution result for a single plan step.
    """

    model_config = ConfigDict(extra="ignore")

    order: int
    task: str
    skill_id: UUID | None = None
    skill_name: str = ""
    success: bool
    latency_ms: float = 0.0
    output: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "order": self.order,
            "task": self.task,
            "skill_id": str(self.skill_id) if self.skill_id else None,
            "skill_name": self.skill_name,
            "success": self.success,
            "latency_ms": round(self.latency_ms, 3),
            "output": self.output,
        }


class PlanResult(BaseModel):
    """
    Result of executing a skill plan.
    """

    model_config = ConfigDict(extra="ignore")

    id: UUID = Field(default_factory=uuid4)
    plan_id: UUID
    task: str
    steps: list[StepResult] = Field(default_factory=list)
    success: bool = False
    total_latency_ms: float = 0.0
    executed_at: datetime = Field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "plan_id": str(self.plan_id),
            "task": self.task,
            "steps": [step.to_dict() for step in self.steps],
            "success": self.success,
            "total_latency_ms": round(self.total_latency_ms, 3),
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
        }