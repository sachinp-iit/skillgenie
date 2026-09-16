# ============================================================================
# Project      : SkillGenie
# File         : routers.py
# Description  : REST API endpoints for SkillGenie.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException

from skillgenie.api.dependencies import get_engine
from skillgenie.api.schemas import (
    ExecutionCreate,
    LearnRequest,
    RecommendRequest,
    RejectRequest,
    SkillUpdate,
    TraceCreate,
)
from skillgenie.constants import SkillStatus
from skillgenie.core.engine import SkillGenie
from skillgenie.exceptions import (
    CapabilityNotFoundError,
    LifecycleError,
    SkillGenieError,
)
from skillgenie.storage.skill_store import capability_to_dict

router = APIRouter()


def _error(exc: SkillGenieError) -> HTTPException:
    """
    Convert a domain exception into an HTTP exception.
    """

    if isinstance(exc, CapabilityNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))

    if isinstance(exc, LifecycleError):
        return HTTPException(status_code=409, detail=str(exc))

    return HTTPException(status_code=400, detail=str(exc))


@router.get("/health")
def health(engine: SkillGenie = Depends(get_engine)):
    """
    Service health check.
    """

    return {
        "status": "ok",
        "service": "skillgenie",
        "version": "0.1.0",
        "database": "connected",
        "skills": engine.store.repository is not None,
    }


# ---------------------------------------------------------------------------
# Traces
# ---------------------------------------------------------------------------


@router.post("/traces", status_code=201)
def create_trace(
    payload: TraceCreate,
    engine: SkillGenie = Depends(get_engine),
):
    """
    Ingest a raw execution trace.
    """

    trace_id = uuid4()

    raw = payload.trace or {}

    task = (
        payload.task_description
        or raw.get("task")
        or raw.get("task_description")
        or ""
    )

    engine.traces.create(
        trace_id=trace_id,
        trace_name=payload.trace_name or task[:100],
        agent_framework=payload.agent_framework,
        task_description=task,
        execution_status=payload.execution_status,
        execution_time_ms=payload.execution_time_ms,
        trace=raw,
        metadata=payload.metadata,
    )

    return {"trace_id": str(trace_id)}


@router.get("/traces")
def list_traces(engine: SkillGenie = Depends(get_engine)):
    """
    List ingested traces.
    """

    return [dict(row) for row in engine.traces.list()]


@router.get("/traces/{trace_id}")
def get_trace(
    trace_id: str,
    engine: SkillGenie = Depends(get_engine),
):
    """
    Fetch a single trace.
    """

    try:
        row = engine.traces.get_by_id(UUID(trace_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid trace id.")

    if row is None:
        raise HTTPException(status_code=404, detail="Trace not found.")

    return dict(row)


@router.delete("/traces/{trace_id}", status_code=204)
def delete_trace(
    trace_id: str,
    engine: SkillGenie = Depends(get_engine),
):
    """
    Delete a trace.
    """

    engine.traces.delete(UUID(trace_id))

    return None


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


@router.get("/skills")
def list_skills(
    status: str | None = None,
    category: str | None = None,
    engine: SkillGenie = Depends(get_engine),
):
    """
    List skills, optionally filtered by status/category.
    """

    skills = engine.store.list(status=status, category=category)

    return [capability_to_dict(skill) for skill in skills]


@router.get("/skills/{skill_id}")
def get_skill(
    skill_id: str,
    engine: SkillGenie = Depends(get_engine),
):
    """
    Fetch a single skill.
    """

    skill = engine.store.get(UUID(skill_id))

    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found.")

    return capability_to_dict(skill)


@router.patch("/skills/{skill_id}")
def update_skill(
    skill_id: str,
    payload: SkillUpdate,
    engine: SkillGenie = Depends(get_engine),
):
    """
    Update editable fields of a skill.
    """

    fields = payload.model_dump(exclude_none=True)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields provided.")

    updated = engine.store.update(UUID(skill_id), **fields)

    if updated is None:
        raise HTTPException(status_code=404, detail="Skill not found.")

    return capability_to_dict(updated)


@router.delete("/skills/{skill_id}", status_code=204)
def delete_skill(
    skill_id: str,
    engine: SkillGenie = Depends(get_engine),
):
    """
    Delete a skill.
    """

    engine.store.delete(UUID(skill_id))

    return None


# ---------------------------------------------------------------------------
# Learning
# ---------------------------------------------------------------------------


@router.post("/learn", status_code=201)
def learn(
    payload: LearnRequest,
    engine: SkillGenie = Depends(get_engine),
):
    """
    Learn a skill from a trace.
    """

    try:
        skill = engine.learn(payload.trace_id)
    except SkillGenieError as exc:
        raise _error(exc)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return capability_to_dict(skill)


@router.post("/learn/all", status_code=201)
def learn_all(engine: SkillGenie = Depends(get_engine)):
    """
    Learn skills from all traces.
    """

    skills = engine.learn_all()

    return [capability_to_dict(skill) for skill in skills]


@router.post("/skills/{skill_id}/relearn")
def relearn(
    skill_id: str,
    engine: SkillGenie = Depends(get_engine),
):
    """
    Relearn a skill from its source traces.
    """

    try:
        skill = engine.learner.relearn(skill_id)
    except SkillGenieError as exc:
        raise _error(exc)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return capability_to_dict(skill)


# ---------------------------------------------------------------------------
# Evaluation & Lifecycle
# ---------------------------------------------------------------------------


@router.post("/skills/{skill_id}/evaluate")
def evaluate_skill(
    skill_id: str,
    engine: SkillGenie = Depends(get_engine),
):
    """
    Evaluate (score) a skill.
    """

    skill = engine.store.get(UUID(skill_id))

    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found.")

    skill = engine.evaluator.evaluate(skill)

    return capability_to_dict(skill)


@router.post("/skills/{skill_id}/approve")
def approve_skill(skill_id: str, engine: SkillGenie = Depends(get_engine)):
    """
    Approve a skill.
    """

    return _lifecycle_action(engine, "approve", skill_id)


@router.post("/skills/{skill_id}/publish")
def publish_skill(skill_id: str, engine: SkillGenie = Depends(get_engine)):
    """
    Publish a skill.
    """

    return _lifecycle_action(engine, "publish", skill_id)


@router.post("/skills/{skill_id}/deprecate")
def deprecate_skill(skill_id: str, engine: SkillGenie = Depends(get_engine)):
    """
    Deprecate a skill.
    """

    return _lifecycle_action(engine, "deprecate", skill_id)


@router.post("/skills/{skill_id}/archive")
def archive_skill(skill_id: str, engine: SkillGenie = Depends(get_engine)):
    """
    Archive a skill.
    """

    return _lifecycle_action(engine, "archive", skill_id)


@router.post("/skills/{skill_id}/restore")
def restore_skill(skill_id: str, engine: SkillGenie = Depends(get_engine)):
    """
    Restore an archived skill.
    """

    return _lifecycle_action(engine, "restore", skill_id)


@router.post("/skills/{skill_id}/reject")
def reject_skill(
    skill_id: str,
    payload: RejectRequest | None = None,
    engine: SkillGenie = Depends(get_engine),
):
    """
    Reject a candidate skill.
    """

    payload = payload or RejectRequest()

    skill = engine.store.get(UUID(skill_id))

    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found.")

    skill = engine.evaluator.reject(skill, payload.reason)

    return capability_to_dict(skill)


def _lifecycle_action(
    engine: SkillGenie,
    action: str,
    skill_id: str,
):
    """
    Dispatch a lifecycle action and return the refreshed skill.
    """

    try:
        getattr(engine.lifecycle, action)(skill_id)
        skill = engine.store.get(UUID(skill_id))
    except SkillGenieError as exc:
        raise _error(exc)

    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found.")

    return capability_to_dict(skill)


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


@router.post("/recommend")
def recommend(
    payload: RecommendRequest,
    engine: SkillGenie = Depends(get_engine),
):
    """
    Recommend skills for a task query.
    """

    recommendations = engine.recommend(
        query=payload.query,
        top_k=payload.top_k,
        status=payload.status,
    )

    return [
        {
            "capability_id": str(item.capability_id),
            "recommendation_type": item.recommendation_type.value,
            "confidence_score": item.confidence_score,
            "similarity_score": item.similarity_score,
            "ranking_score": item.ranking_score,
            "reason": item.reason,
            "metadata": item.metadata,
        }
        for item in recommendations
    ]


@router.post("/recommend/trace/{trace_id}")
def recommend_by_trace(
    trace_id: str,
    engine: SkillGenie = Depends(get_engine),
):
    """
    Recommend skills based on an execution trace.
    """

    try:
        recommendations = engine.recommender.recommend_by_trace(trace_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return [
        {
            "capability_id": str(item.capability_id),
            "recommendation_type": item.recommendation_type.value,
            "similarity_score": item.similarity_score,
            "ranking_score": item.ranking_score,
        }
        for item in recommendations
    ]


@router.get("/recommend/similar/{skill_id}")
def recommend_similar(
    skill_id: str,
    top_k: int = 5,
    engine: SkillGenie = Depends(get_engine),
):
    """
    Recommend skills similar to an existing skill.
    """

    try:
        recommendations = engine.recommender.recommend_similar(
            skill_id,
            top_k=top_k,
        )
    except SkillGenieError as exc:
        raise _error(exc)

    return [
        {
            "capability_id": str(item.capability_id),
            "recommendation_type": item.recommendation_type.value,
            "similarity_score": item.similarity_score,
            "ranking_score": item.ranking_score,
        }
        for item in recommendations
    ]


# ---------------------------------------------------------------------------
# Executions & Observability
# ---------------------------------------------------------------------------


@router.post("/executions", status_code=201)
def record_execution(
    payload: ExecutionCreate,
    engine: SkillGenie = Depends(get_engine),
):
    """
    Record a capability execution.
    """

    try:
        execution = engine.record_execution(
            capability_id=UUID(payload.capability_id),
            task_name=payload.task_name,
            execution_status=payload.execution_status,
            execution_time_ms=payload.execution_time_ms,
            input_data=payload.input_data,
            output_data=payload.output_data,
            error_message=payload.error_message,
            trace_id=UUID(payload.trace_id) if payload.trace_id else None,
            metadata=payload.metadata,
        )
    except (SkillGenieError, ValueError) as exc:
        raise _error(exc) if isinstance(exc, SkillGenieError) else HTTPException(
            status_code=400,
            detail=str(exc),
        )

    return {
        "id": str(execution.id),
        "capability_id": str(execution.capability_id),
        "execution_status": execution.execution_status.value,
        "execution_time_ms": execution.execution_time_ms,
    }


@router.get("/executions")
def list_executions(engine: SkillGenie = Depends(get_engine)):
    """
    List recorded executions.
    """

    return [dict(row) for row in engine.executions.list()]


@router.get("/metrics/skills/{skill_id}")
def skill_metrics(skill_id: str, engine: SkillGenie = Depends(get_engine)):
    """
    Metrics history for a skill.
    """

    return [dict(row) for row in engine.metrics.get_by_capability(UUID(skill_id))]


@router.get("/audit/skills/{skill_id}")
def skill_audit(skill_id: str, engine: SkillGenie = Depends(get_engine)):
    """
    Audit history for a skill.
    """

    return [dict(row) for row in engine.audit.get_by_capability(UUID(skill_id))]


@router.get("/monitor/overview")
def monitor_overview(engine: SkillGenie = Depends(get_engine)):
    """
    Health and status overview for the monitoring dashboard.
    """

    return engine.health_overview()


@router.get("/admin/overview")
def admin_overview(engine: SkillGenie = Depends(get_engine)):
    """
    Registry overview for the admin dashboard.
    """

    skills = engine.store.list()

    recent_skills = [
        capability_to_dict(skill)
        for skill in sorted(
            skills,
            key=lambda item: item.created_at,
            reverse=True,
        )[:10]
    ]

    skill_ids = [str(skill.id) for skill in skills]

    return {
        "total_skills": len(skills),
        "recent_skills": recent_skills,
        "skill_ids": skill_ids,
        "pending_approval": len(
            [
                skill
                for skill in skills
                if skill.status == SkillStatus.CANDIDATE
            ]
        ),
        "published": len(
            [
                skill
                for skill in skills
                if skill.status == SkillStatus.PUBLISHED
            ]
        ),
    }