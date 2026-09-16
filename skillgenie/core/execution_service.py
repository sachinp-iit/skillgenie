# ============================================================================
# Project      : SkillGenie
# File         : execution_service.py
# Description  : Records capability executions and updates runtime metrics so
#                the system can learn from real-world usage.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

from skillgenie.config import Config
from skillgenie.constants import SkillHealth
from skillgenie.core.health import SkillHealthEngine
from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.audit_repository import AuditRepository
from skillgenie.database.repositories.capability_repository import (
    CapabilityRepository,
)
from skillgenie.database.repositories.execution_repository import (
    ExecutionRepository,
)
from skillgenie.exceptions import CapabilityNotFoundError
from skillgenie.models.execution import Execution
from skillgenie.utils.logger import Logger


class ExecutionService:
    """
    Handles capability execution recording and metric updates.
    """

    def __init__(
        self,
        config: Config,
        database: DatabaseManager,
        skill_repository: CapabilityRepository | None = None,
        execution_repository: ExecutionRepository | None = None,
        audit_repository: AuditRepository | None = None,
    ):
        """
        Initialize execution service.

        Args:
            config: SkillGenie configuration.
            database: Database manager.
            skill_repository: Optional repository override.
            execution_repository: Optional repository override.
            audit_repository: Optional repository override.
        """

        self._config = config
        self._database = database

        self._logger = Logger(config).log

        self._skill_repository = (
            skill_repository or CapabilityRepository(database)
        )

        self._execution_repository = (
            execution_repository or ExecutionRepository(database)
        )

        self._audit_repository = (
            audit_repository or AuditRepository(database)
        )

        self._health_engine = SkillHealthEngine(config)

    def record(
        self,
        capability_id: UUID,
        task_name: str,
        execution_status: str,
        execution_time_ms: float = 0.0,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        error_message: str | None = None,
        trace_id: UUID | None = None,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Execution:
        """
        Persist an execution and refresh the parent skill's runtime metrics.

        Args:
            capability_id: Skill identifier.
            task_name: Executed task name.
            execution_status: One of SUCCESS/FAILED/PARTIAL/CANCELLED.
            execution_time_ms: Execution duration.
            input_data: Execution inputs.
            output_data: Execution outputs.
            error_message: Optional error details.
            trace_id: Optional originating trace.
            started_at: Start timestamp.
            completed_at: Completion timestamp.
            metadata: Additional metadata.

        Returns:
            Recorded execution model.

        Raises:
            CapabilityNotFoundError: When the skill does not exist.
        """

        skill = self._skill_repository.get_by_id(capability_id)

        if skill is None:
            raise CapabilityNotFoundError(
                f"Skill '{capability_id}' does not exist."
            )

        now = datetime.utcnow()

        execution = Execution(
            id=uuid4(),
            capability_id=capability_id,
            trace_id=trace_id,
            task_name=task_name,
            execution_status=execution_status,
            started_at=started_at or now,
            completed_at=completed_at,
            execution_time_ms=execution_time_ms,
            input_data=input_data or {},
            output_data=output_data or {},
            error_message=error_message,
            metadata=metadata or {},
        )

        self._execution_repository.create(
            execution_id=execution.id,
            capability_id=execution.capability_id,
            trace_id=execution.trace_id,
            task_name=execution.task_name,
            execution_status=execution.execution_status.value,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
            execution_time_ms=execution.execution_time_ms,
            input_data=execution.input_data,
            output_data=execution.output_data,
            error_message=execution.error_message,
            metadata=execution.metadata,
        )

        self._refresh_runtime_metrics(capability_id, execution)

        return execution

    def _refresh_runtime_metrics(
        self,
        capability_id: UUID,
        execution: Execution,
    ) -> None:
        """
        Update skill usage, latency, success rate and health.
        """

        executions = self._execution_repository.get_by_capability(
            capability_id
        )

        all_executions = [dict(row) for row in (executions or [])]

        total = len(all_executions)

        successful = sum(
            1
            for row in all_executions
            if row.get("execution_status") == "SUCCESS"
        )

        usage_count = total

        latencies = [
            float(row.get("execution_time_ms") or 0.0)
            for row in all_executions
        ]

        avg_latency = (
            sum(latencies) / len(latencies)
            if latencies
            else 0.0
        )

        success_rate = successful / total if total else 0.0

        skill = dict(self._skill_repository.get_by_id(capability_id))

        metrics = SimpleNamespace(
            confidence_score=skill.get("confidence_score"),
            quality_score=skill.get("quality_score"),
            success_rate=success_rate,
            avg_latency_ms=avg_latency,
        )

        health = self._health_engine.health(metrics)

        self._skill_repository.update(
            capability_id=capability_id,
            usage_count=usage_count,
            avg_latency_ms=round(avg_latency, 3),
            success_rate=round(success_rate, 3),
            health=health.value,
            last_used_at=execution.completed_at or execution.started_at,
        )

        self._audit(
            capability_id=capability_id,
            action="EXECUTED",
            remarks=f"{execution.execution_status.value} in "
            f"{execution.execution_time_ms:g} ms.",
            payload={
                "task": execution.task_name,
                "status": execution.execution_status.value,
                "success_rate": round(success_rate, 3),
                "usage_count": usage_count,
            },
        )

    def _audit(
        self,
        capability_id: UUID,
        action: str,
        remarks: str = "",
        payload: dict[str, Any] | None = None,
    ) -> None:
        """
        Write an audit entry.
        """

        self._audit_repository.create(
            audit_id=uuid4(),
            capability_id=capability_id,
            action=action,
            performed_by="executions",
            remarks=remarks,
            payload=payload or {},
        )