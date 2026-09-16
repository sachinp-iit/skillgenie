# ============================================================================
# Project      : SkillGenie
# File         : langgraph.py
# Description  : Recording hook for LangGraph agents.
#
# Usage:
#     recorder = LangGraphRecorder(config, trace_repository)
#     # attach to your LangGraph app via recorder.wrap(app)
#     # or call recorder.after_run(state, metadata) manually
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any

from skillgenie.config import Config
from skillgenie.integrations.base import BaseRecorder


class LangGraphRecorder(BaseRecorder):
    """
    Records execution traces from LangGraph runs.

    Supports:
        - ``after_run(state, metadata)`` : extract nodes from LangGraph state
        - ``wrap(graph)``                : decorate a compiled LangGraph graph
    """

    def __init__(self, config: Config, trace_repository: Any):
        super().__init__(config, trace_repository, framework="langgraph")

    def after_run(
        self,
        state: dict[str, Any] | Any,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Extract trace data from a LangGraph state dict and persist it.
        """
        state_dict = _to_dict(state)
        metadata = metadata or {}
        task = (
            metadata.get("task")
            or state_dict.get("task")
            or state_dict.get("input", {}).get("task", "")
            or "langgraph-run"
        )
        steps = self._extract_steps(state_dict)
        tools = self._extract_tools(state_dict)
        execution_status = state_dict.get("execution_status", "SUCCESS")

        return self.record(
            task=task,
            steps=steps,
            tools=tools,
            metadata=metadata,
            execution_status=execution_status,
        )

    def wrap(self, graph: Any) -> Any:
        """
        Wrap a compiled LangGraph graph to automatically record traces
        after each invocation.
        """
        original_invoke = graph.invoke

        def wrapped_invoke(input_data: Any, **kwargs: Any) -> Any:
            result = original_invoke(input_data, **kwargs)
            self.after_run(result, metadata={"input": _to_dict(input_data)})
            return result

        graph.invoke = wrapped_invoke
        return graph

    @staticmethod
    def _extract_steps(state: dict[str, Any]) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        nodes = state.get("nodes") or state.get("node_outputs") or []
        if isinstance(nodes, dict):
            nodes = [
                {"name": k, **v} if isinstance(v, dict) else {"name": k, "output": v}
                for k, v in nodes.items()
            ]
        for i, node in enumerate(nodes):
            if isinstance(node, dict):
                steps.append(
                    {
                        "order": i + 1,
                        "name": node.get("name", f"node-{i}"),
                        "type": node.get("type", "task"),
                        "tool": node.get("tool", ""),
                        "output": node.get("output", node.get("outputs", {})),
                    }
                )
        return steps

    @staticmethod
    def _extract_tools(state: dict[str, Any]) -> list[dict[str, Any]]:
        tools: list[dict[str, Any]] = []
        for node in state.get("nodes", []):
            if isinstance(node, dict) and node.get("tool"):
                tool_name = node["tool"]
                if isinstance(tool_name, str):
                    tools.append({"name": tool_name, "type": "tool"})
                elif isinstance(tool_name, dict):
                    tools.append(
                        {"name": tool_name.get("type", "unknown"), "type": "tool"}
                    )
        return tools


def _to_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "dict"):
        return obj.dict()
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return {}