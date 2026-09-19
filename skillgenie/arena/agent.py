# ============================================================================
# Project      : SkillGenie
# File         : agent.py
# Description  : ArenaAgent — a lightweight simulated agent that executes a
#                learned skill's workflow step-by-step against a task, with
#                optional tool-failure injection to gauge skill resilience.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import random
from typing import Any


class ArenaAgent:
    """
    Executes a skill workflow in simulation and reports the outcome.
    """

    def __init__(
        self,
        skill: Any,
        seed: int = 0,
        failure_rate: float = 0.30,
    ):
        self._skill = skill
        self._rng = random.Random(seed)
        self._failure_rate = max(0.0, min(1.0, failure_rate))

    @property
    def skill(self) -> Any:
        return self._skill

    @property
    def name(self) -> str:
        return getattr(self._skill, "name", "Unknown")

    def run(self, task: str) -> dict[str, Any]:
        """
        Simulate executing the skill's workflow for a task.
        """

        steps = self._workflow_steps()

        if not steps:
            failed = True
        else:
            failed = False

        executed: list[dict[str, Any]] = []
        total_latency = 0.0

        for index, step in enumerate(steps):
            latency = self._rng.uniform(50.0, 400.0)
            total_latency += latency

            error = self._inject_failure(step.get("tool", ""))

            if error:
                fallback = self._has_fallback(step.get("tool", ""))
                status = "RECOVERED" if fallback else "FAILED"
                if status == "FAILED":
                    failed = True
            else:
                status = "OK"

            executed.append(
                {
                    "order": step.get("order", index + 1),
                    "step": step.get("name") or f"step-{index + 1}",
                    "tool": step.get("tool") or "",
                    "status": status,
                    "latency_ms": round(latency, 1),
                }
            )

        return {
            "agent": self.name,
            "task": task,
            "success": not failed,
            "steps": executed,
            "step_count": len(executed),
            "total_latency_ms": round(total_latency, 1),
        }

    def _workflow_steps(self) -> list[dict[str, Any]]:
        workflow = getattr(self._skill, "workflow", {}) or {}
        return list(workflow.get("steps") or [])

    def _inject_failure(self, tool: str) -> bool:
        """
        Decide whether the tool call fails under stress.
        """

        if not tool or self._failure_rate <= 0.0:
            return False

        return self._rng.random() < self._failure_rate

    def _has_fallback(self, tool: str) -> bool:
        """
        True when the skill declares a fallback tool with the same function.
        """

        if not tool:
            return False

        metadata = getattr(self._skill, "metadata", {}) or {}
        tools = metadata.get("tools") or []

        for entry in tools:
            if not isinstance(entry, dict):
                continue
            name = (entry.get("name") or "").strip().lower()
            is_fallback = bool(entry.get("fallback"))
            replaces = (entry.get("replaces") or "").strip().lower()

            if (is_fallback and name == tool.lower()) or (
                replaces == tool.lower()
            ):
                return True

        return False