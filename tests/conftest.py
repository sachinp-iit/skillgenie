"""
Shared fixtures: in-memory fake repositories so the full pipeline can be
tested without a running PostgreSQL instance.
"""

from __future__ import annotations

import copy
from datetime import datetime
from typing import Any
from uuid import uuid4

import pytest

from skillgenie.config import Config


class FakeCapabilityRepository:
    """In-memory stand-in for CapabilityRepository."""

    def __init__(self) -> None:
        self._skills: dict[str, dict[str, Any]] = {}
        self.calls: list[str] = []

    def create(
        self,
        capability_id,
        name,
        description,
        category,
        version,
        status,
    ) -> None:
        self.calls.append("create")
        self._skills[str(capability_id)] = {
            "id": str(capability_id),
            "name": name,
            "description": description,
            "category": category,
            "version": version,
            "status": status,
            "confidence_score": 0.0,
            "quality_score": 0.0,
            "success_rate": 0.0,
            "usage_count": 0,
            "avg_latency_ms": 0.0,
            "health": "GOOD",
            "embedding": [],
            "relationship_graph": {},
            "workflow": {},
            "metadata": {},
            "created_from": [],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_used_at": None,
        }

    def get_by_id(self, capability_id):
        self.calls.append("get_by_id")
        row = self._skills.get(str(capability_id))
        return copy.deepcopy(row) if row is not None else None

    def get_by_name(self, name: str):
        self.calls.append("get_by_name")
        for row in self._skills.values():
            if row["name"] == name:
                return copy.deepcopy(row)
        return None

    def update(self, capability_id, **fields) -> None:
        self.calls.append("update")
        key = str(capability_id)
        if key not in self._skills:
            return
        self._skills[key].update(fields)
        self._skills[key]["updated_at"] = datetime.utcnow()

    def list(self, status=None, category=None):
        self.calls.append("list")
        rows = list(self._skills.values())
        if status is not None:
            rows = [row for row in rows if row["status"] == status]
        if category is not None:
            rows = [row for row in rows if row["category"] == category]
        rows.sort(key=lambda row: row["created_at"], reverse=True)
        return [copy.deepcopy(row) for row in rows]

    def search_similar(self, embedding, limit=10, threshold=0.0, status=None):
        return []

    def delete(self, capability_id) -> None:
        key = str(capability_id)
        if key in self._skills:
            del self._skills[key]


class FakeTraceRepository:
    """In-memory stand-in for TraceRepository."""

    def __init__(self) -> None:
        self._traces: dict[str, dict[str, Any]] = {}

    def create(
        self,
        trace_id,
        trace_name,
        agent_framework,
        task_description,
        execution_status,
        execution_time_ms,
        trace,
        metadata,
    ) -> None:
        self._traces[str(trace_id)] = {
            "id": str(trace_id),
            "trace_name": trace_name,
            "agent_framework": agent_framework,
            "task_description": task_description,
            "execution_status": execution_status,
            "execution_time_ms": execution_time_ms,
            "trace": copy.deepcopy(trace),
            "metadata": copy.deepcopy(metadata),
            "created_at": datetime.utcnow(),
        }

    def get_by_id(self, trace_id):
        row = self._traces.get(str(trace_id))
        return copy.deepcopy(row) if row else None

    def list(self):
        rows = list(self._traces.values())
        rows.sort(key=lambda row: row["created_at"], reverse=True)
        return [copy.deepcopy(row) for row in rows]

    def update(self, trace_id, **fields) -> None:
        key = str(trace_id)
        if key in self._traces:
            self._traces[key].update(fields)

    def delete(self, trace_id) -> None:
        key = str(trace_id)
        if key in self._traces:
            del self._traces[key]


class FakeMetricsRepository:
    """In-memory stand-in for MetricsRepository."""

    def __init__(self) -> None:
        self._metrics: list[dict[str, Any]] = []

    def create(
        self,
        metric_id,
        capability_id,
        confidence_score,
        quality_score,
        success_rate,
        avg_latency_ms,
        usage_count,
    ) -> None:
        self._metrics.append(
            {
                "id": str(metric_id),
                "capability_id": str(capability_id),
                "confidence_score": confidence_score,
                "quality_score": quality_score,
                "success_rate": success_rate,
                "avg_latency_ms": avg_latency_ms,
                "usage_count": usage_count,
                "recorded_at": datetime.utcnow(),
            }
        )

    def get_by_capability(self, capability_id):
        return [
            copy.deepcopy(row)
            for row in self._metrics
            if row["capability_id"] == str(capability_id)
        ]

    def delete(self, metric_id) -> None:
        self._metrics = [
            row for row in self._metrics if row["id"] != str(metric_id)
        ]


class FakeAuditRepository:
    """In-memory stand-in for AuditRepository."""

    def __init__(self) -> None:
        self._logs: list[dict[str, Any]] = []

    @property
    def logs(self) -> list[dict[str, Any]]:
        return list(self._logs)

    def create(
        self,
        audit_id,
        capability_id,
        action,
        performed_by,
        remarks,
        payload,
    ) -> None:
        self._logs.append(
            {
                "id": str(audit_id),
                "capability_id": str(capability_id),
                "action": action,
                "performed_by": performed_by,
                "remarks": remarks,
                "payload": copy.deepcopy(payload),
                "created_at": datetime.utcnow(),
            }
        )

    def get_by_capability(self, capability_id):
        return [
            copy.deepcopy(row)
            for row in self._logs
            if row["capability_id"] == str(capability_id)
        ]

    def delete(self, audit_id) -> None:
        self._logs = [row for row in self._logs if row["id"] != str(audit_id)]


class FakeExecutionRepository:
    """In-memory stand-in for ExecutionRepository."""

    def __init__(self) -> None:
        self._executions: list[dict[str, Any]] = []

    def create(
        self,
        execution_id,
        capability_id,
        trace_id,
        task_name,
        execution_status,
        started_at,
        completed_at,
        execution_time_ms,
        input_data,
        output_data,
        error_message,
        metadata,
    ) -> None:
        self._executions.append(
            {
                "id": str(execution_id),
                "capability_id": str(capability_id),
                "trace_id": str(trace_id) if trace_id else None,
                "task_name": task_name,
                "execution_status": execution_status,
                "started_at": started_at,
                "completed_at": completed_at,
                "execution_time_ms": execution_time_ms,
                "input_data": copy.deepcopy(input_data),
                "output_data": copy.deepcopy(output_data),
                "error_message": error_message,
                "metadata": copy.deepcopy(metadata),
            }
        )

    def get_by_id(self, execution_id):
        for row in self._executions:
            if row["id"] == str(execution_id):
                return copy.deepcopy(row)
        return None

    def get_by_capability(self, capability_id):
        rows = [
            copy.deepcopy(row)
            for row in self._executions
            if row["capability_id"] == str(capability_id)
        ]
        rows.sort(key=lambda row: row["started_at"], reverse=True)
        return rows

    def list(self):
        return [copy.deepcopy(row) for row in self._executions]

    def delete(self, execution_id) -> None:
        self._executions = [
            row for row in self._executions if row["id"] != str(execution_id)
        ]


class FakeRecommendationRepository:
    """In-memory stand-in for RecommendationRepository."""

    def __init__(self) -> None:
        self._recommendations: list[dict[str, Any]] = []

    def create(
        self,
        recommendation_id,
        capability_id,
        recommendation_type,
        confidence_score,
        similarity_score,
        ranking_score,
        reason,
        metadata,
    ) -> None:
        self._recommendations.append(
            {
                "id": str(recommendation_id),
                "capability_id": str(capability_id),
                "recommendation_type": recommendation_type,
                "confidence_score": confidence_score,
                "similarity_score": similarity_score,
                "ranking_score": ranking_score,
                "reason": reason,
                "metadata": copy.deepcopy(metadata),
            }
        )

    def get_by_capability(self, capability_id):
        return [copy.deepcopy(row) for row in self._recommendations]

    def list(self, limit=50):
        return [copy.deepcopy(row) for row in self._recommendations[:limit]]

    def delete(self, recommendation_id) -> None:
        self._recommendations = [
            row for row in self._recommendations
            if row["id"] != str(recommendation_id)
        ]


class FakeOutcomeRepository:
    """In-memory stand-in for OutcomeRepository."""

    def __init__(self) -> None:
        self._outcomes: list[dict[str, Any]] = []

    def create(
        self,
        outcome_id,
        capability_id,
        recommendation_id,
        outcome,
        latency_ms,
        rating,
        metadata,
        created_at=None,
    ) -> None:
        self._outcomes.append(
            {
                "id": str(outcome_id),
                "capability_id": str(capability_id),
                "recommendation_id": (
                    str(recommendation_id) if recommendation_id else None
                ),
                "outcome": outcome,
                "latency_ms": latency_ms,
                "rating": rating,
                "metadata": copy.deepcopy(metadata),
                "created_at": created_at or datetime.utcnow(),
            }
        )

    def get_by_capability(self, capability_id):
        return [
            copy.deepcopy(row)
            for row in self._outcomes
            if row["capability_id"] == str(capability_id)
        ]

    def get_by_recommendation(self, recommendation_id):
        return [
            copy.deepcopy(row)
            for row in self._outcomes
            if row["recommendation_id"] == str(recommendation_id)
        ]

    def list(self, limit=50):
        return [copy.deepcopy(row) for row in self._outcomes[:limit]]

    def count_outcomes(self, capability_id, window_start=None):
        rows = [
            row
            for row in self._outcomes
            if row["capability_id"] == str(capability_id)
        ]
        if window_start:
            rows = [row for row in rows if row["created_at"] >= window_start]
        successes = sum(1 for row in rows if row["outcome"] == "SUCCESS")
        return {"successes": successes, "total": len(rows)}

    def delete(self, outcome_id) -> None:
        self._outcomes = [
            row for row in self._outcomes if row["id"] != str(outcome_id)
        ]


@pytest.fixture
def config(tmp_path):
    """Configuration backed by a temporary config.json."""

    path = tmp_path / "config.json"

    cfg = Config(str(path))

    return cfg


def make_skill(
    name: str = "Web Research",
    category: str = "research",
    description: str = (
        "Skills for searching the web, extracting facts and generating "
        "structured summaries."
    ),
    embedding: list[float] | None = None,
    status: str = "DRAFT",
    **overrides: Any,
) -> dict[str, Any]:
    """
    Build a fully-populated skill row for use with fake repositories and to
    convert into a Capability model.
    """

    row: dict[str, Any] = {
        "id": str(uuid4()),
        "name": name,
        "description": description,
        "category": category,
        "version": "1.0.0",
        "status": status,
        "confidence_score": 0.9,
        "quality_score": 0.8,
        "success_rate": 1.0,
        "usage_count": 3,
        "avg_latency_ms": 120.0,
        "health": "GOOD",
        "embedding": embedding or [0.1, 0.2, 0.3, 0.4, 0.5],
        "relationship_graph": {"related": [{"skill_id": "other"}]},
        "workflow": {
            "name": name,
            "framework": "custom",
            "steps": [
                {
                    "order": 1,
                    "name": "search",
                    "tool": "web_search",
                    "output": {"result": "found"},
                },
                {
                    "order": 2,
                    "name": "summarize",
                    "tool": "summarize",
                    "output": {"result": "done"},
                },
            ],
            "metadata": {"category": category},
        },
        "metadata": {
            "tools": [
                {"name": "web_search", "type": "web"},
                {"name": "summarize", "type": "llm"},
            ],
            "prompts": [
                {"role": "user", "content": "Please do research"},
            ],
            "input_output": {"input": {"query": "x"}, "output": {"result": "y"}},
            "search_profile": {"tokens": f"{name} {description}"},
        },
        "created_from": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_used_at": datetime.utcnow(),
    }

    row.update(overrides)

    return row


def make_capability(**overrides: Any) -> "Capability":
    """Build a Capability model from a make_skill row."""

    from skillgenie.models.capability import Capability

    row = make_skill(**overrides)

    kwargs: dict[str, Any] = dict(row)

    kwargs.pop("id", None)

    return Capability(id=row["id"], **kwargs)


@pytest.fixture
def dummy_database():
    """Placeholder database object (unused when fake repos are injected)."""

    return object()


@pytest.fixture
def capability_repository():
    return FakeCapabilityRepository()


@pytest.fixture
def trace_repository():
    return FakeTraceRepository()


@pytest.fixture
def metrics_repository():
    return FakeMetricsRepository()


@pytest.fixture
def audit_repository():
    return FakeAuditRepository()


@pytest.fixture
def execution_repository():
    return FakeExecutionRepository()


@pytest.fixture
def recommendation_repository():
    return FakeRecommendationRepository()


@pytest.fixture
def outcome_repository():
    return FakeOutcomeRepository()


@pytest.fixture
def store(config, capability_repository):
    """SkillStore backed by the in-memory fake capability repository."""

    from skillgenie.storage.skill_store import SkillStore

    return SkillStore(
        config=config,
        repository=capability_repository,
        embedding_provider=None,
    )


def make_raw_trace(
    task: str,
    *,
    trace_id: str | None = None,
    framework: str = "custom",
    goal: str = "",
    tools: list[dict[str, Any]] | None = None,
    steps: list[dict[str, Any]] | None = None,
    category: str = "general",
    execution_status: str = "SUCCESS",
) -> dict[str, Any]:
    """
    Build a raw trace in the canonical shape used by TraceParser.
    """

    return {
        "id": trace_id or str(uuid4()),
        "trace_name": task,
        "task": task,
        "task_description": task,
        "goal": goal or task,
        "agent_framework": framework,
        "execution_status": execution_status,
        "execution_time_ms": 250.0,
        "trace": {
            "task": task,
            "goal": goal or task,
            "steps": steps
            or [
                {
                    "name": "step-1",
                    "type": "task",
                    "tool": "web_search",
                    "output": {"result": "ok"},
                },
                {
                    "name": "step-2",
                    "type": "task",
                    "tool": "summarize",
                    "output": {"result": "done"},
                },
            ],
            "tools": tools
            or [
                {"name": "web_search", "type": "web"},
                {"name": "summarize", "type": "llm"},
            ],
            "prompts": [
                {"role": "user", "content": f"Please {task.lower()}"},
            ],
            "metadata": {"category": category},
            "input": {"query": task},
            "output": {"result": "ok"},
        },
        "metadata": {
            "category": category,
        },
    }


def add_trace(repo, raw: dict[str, Any]) -> str:
    """
    Persist a raw trace into a fake trace repository.

    Returns the generated trace id.
    """

    from uuid import uuid4

    trace_id = str(uuid4())

    repo.create(
        trace_id=trace_id,
        trace_name=raw.get("trace_name", raw.get("task", "trace")),
        agent_framework=raw.get("agent_framework", "custom"),
        task_description=raw.get("task_description", raw.get("task", "")),
        execution_status=raw.get("execution_status", "SUCCESS"),
        execution_time_ms=raw.get("execution_time_ms", 0.0),
        trace=raw.get("trace", {}),
        metadata=raw.get("metadata", {}),
    )

    return trace_id