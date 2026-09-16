# ============================================================================
# Project      : SkillGenie
# File         : crewai.py
# Description  : Recording hook for CrewAI agents.
#
# Usage:
#     recorder = CrewAIRecorder(config, trace_repository)
#     recorder.after_crew_run(crew_output, crew_meta)
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any

from skillgenie.config import Config
from skillgenie.integrations.base import BaseRecorder


class CrewAIRecorder(BaseRecorder):
    """
    Records execution traces from CrewAI runs.
    """

    def __init__(self, config: Config, trace_repository: Any):
        super().__init__(config, trace_repository, framework="crewai")

    def after_crew_run(
        self,
        crew_output: dict[str, Any] | Any,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Extract trace data from a CrewAI output and persist it.
        """
        output_dict = _to_dict(crew_output)
        metadata = metadata or {}
        task = (
            metadata.get("task")
            or output_dict.get("task")
            or output_dict.get("description", "")
            or "crewai-run"
        )
        steps = self._extract_steps(output_dict)
        tools = self._extract_tools(output_dict)
        execution_status = output_dict.get("execution_status", "SUCCESS")

        return self.record(
            task=task,
            steps=steps,
            tools=tools,
            metadata=metadata,
            execution_status=execution_status,
        )

    @staticmethod
    def _extract_steps(output: dict[str, Any]) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        agents = output.get("agents") or output.get("agent_outputs") or []
        for i, agent in enumerate(agents):
            if isinstance(agent, dict):
                steps.append(
                    {
                        "order": i + 1,
                        "name": agent.get("role", f"agent-{i}"),
                        "type": "agent",
                        "tool": agent.get("tool", ""),
                        "output": agent.get("output", {}),
                    }
                )
        if not steps:
            raw_output = output.get("raw") or output.get("output", "")
            if raw_output:
                steps.append(
                    {
                        "order": 1,
                        "name": "crew-output",
                        "type": "task",
                        "output": {"raw": str(raw_output)[:1000]},
                    }
                )
        return steps

    @staticmethod
    def _extract_tools(output: dict[str, Any]) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        for agent in output.get("agents", []):
            if isinstance(agent, dict) and agent.get("tool"):
                tools.append({"name": str(agent["tool"]), "type": "tool"})
        return tools


def _to_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return {}