# ============================================================================
# Project      : SkillGenie
# File         : base.py
# Description  : Base recording hook that persists execution traces to the
#                SkillGenie trace repository.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from skillgenie.config import Config
from skillgenie.utils.logger import Logger


class BaseRecorder:
    """
    Base class for framework-specific trace recorders.

    Subclasses implement framework-specific hooks; this class handles the
    common persist-to-repository logic.
    """

    def __init__(
        self,
        config: Config,
        trace_repository: Any,
        framework: str = "custom",
    ):
        self._config = config
        self._trace_repository = trace_repository
        self._framework = framework
        self._logger = Logger(config).log
        self._enabled = config.get_bool("integrations.enabled", True)

    def record(
        self,
        task: str,
        steps: list[dict[str, Any]] | None = None,
        tools: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None,
        execution_status: str = "SUCCESS",
        execution_time_ms: float = 0.0,
        goal: str = "",
    ) -> str:
        """
        Persist a trace and return the generated trace_id.
        """
        if not self._enabled:
            return ""

        trace_id = str(uuid4())

        trace_payload: dict[str, Any] = {
            "task": task,
            "goal": goal or task,
            "steps": steps or [],
            "tools": tools or [],
            "prompts": metadata.get("prompts", []) if metadata else [],
            "metadata": metadata or {},
            "input": metadata.get("input", {}) if metadata else {},
            "output": metadata.get("output", {}) if metadata else {},
        }

        self._trace_repository.create(
            trace_id=trace_id,
            trace_name=task,
            agent_framework=self._framework,
            task_description=task,
            execution_status=execution_status,
            execution_time_ms=execution_time_ms,
            trace=trace_payload,
            metadata=metadata or {},
        )

        self._logger.info(
            f"[{self._framework}] Recorded trace '{task}' ({trace_id})"
        )

        return trace_id


def record_trace(
    config: Config,
    trace_repository: Any,
    task: str,
    framework: str = "custom",
    **kwargs: Any,
) -> str:
    """
    Convenience function to record a trace using the base recorder.
    """
    recorder = BaseRecorder(config, trace_repository, framework=framework)
    return recorder.record(task, **kwargs)