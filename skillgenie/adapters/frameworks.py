# ============================================================================
# Project      : SkillGenie
# File         : frameworks.py
# Description  : Framework-specific adapters that normalize execution traces
#                from popular agentic AI frameworks.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any

from skillgenie.adapters.base import FrameworkAdapter, register_adapter


def _as_steps(value: Any, name_key: str = "name") -> list[dict[str, Any]]:
    """
    Coerce a value into a list of step-like dicts.
    """

    if not isinstance(value, list):
        return []

    steps: list[dict[str, Any]] = []

    for index, item in enumerate(value):
        if isinstance(item, str):
            steps.append({name_key: item, "type": "task"})
        elif isinstance(item, dict):
            steps.append(
                {
                    "name": item.get(name_key) or f"step_{index}",
                    "type": item.get("type", "task"),
                    "description": item.get("description", ""),
                    "tool": item.get("tool"),
                    "input": item.get("input", {}),
                    "output": item.get("output", {}),
                    "status": item.get("status", "SUCCESS"),
                    "duration_ms": item.get("duration_ms", 0),
                    "metadata": item.get("metadata", {}),
                }
            )

    return steps


def _collect_tools(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Collect tool references from steps.
    """

    tools: list[dict[str, Any]] = []

    for step in steps:
        tool = step.get("tool")

        if isinstance(tool, str):
            tools.append({"name": tool, "type": "unknown"})
        elif isinstance(tool, dict):
            tools.append(tool)

    return tools


@register_adapter
class LangGraphAdapter(FrameworkAdapter):
    """LangGraph trace adapter."""

    framework = "langgraph"

    def normalize(self, trace: dict[str, Any], **ctx: Any) -> dict[str, Any]:
        nodes = trace.get("nodes") or trace.get("events") or trace.get("channels") or []
        steps = _as_steps(nodes)
        return self._wrap(
            trace,
            task=trace.get("task_description"),
            goal=trace.get("goal"),
            steps=steps,
            tools=trace.get("tools") or _collect_tools(steps),
            input_data=trace.get("input"),
            output=(
                trace.get("state")
                if "state" in trace
                else trace.get("output")
            ),
        )


@register_adapter
class LangChainAdapter(FrameworkAdapter):
    """LangChain trace adapter."""

    framework = "langchain"

    def normalize(self, trace: dict[str, Any], **ctx: Any) -> dict[str, Any]:
        intermediates = (
            trace.get("intermediate_steps")
            or trace.get("runnables")
            or trace.get("events")
            or []
        )
        steps = _as_steps(intermediates, name_key="name")
        messages = trace.get("messages") or []

        prompts = [
            {"role": m.get("type", "user"), "content": m.get("content", "")}
            for m in messages
            if isinstance(m, dict) and m.get("content")
        ]

        return self._wrap(
            trace,
            task=trace.get("task_description"),
            steps=steps,
            tools=trace.get("tools") or _collect_tools(steps),
            prompts=prompts,
            input_data=trace.get("input"),
            output=trace.get("output"),
        )


@register_adapter
class LlamaIndexAdapter(FrameworkAdapter):
    """LlamaIndex trace adapter."""

    framework = "llamaindex"

    def normalize(self, trace: dict[str, Any], **ctx: Any) -> dict[str, Any]:
        events = trace.get("workflow_events") or trace.get("events") or []
        steps = _as_steps(events, name_key="event_name")
        return self._wrap(
            trace,
            task=trace.get("task_description"),
            steps=steps,
            tools=trace.get("tools") or _collect_tools(steps),
            input_data=trace.get("input"),
            output=trace.get("response") or trace.get("output"),
        )


@register_adapter
class HaystackAdapter(FrameworkAdapter):
    """Haystack trace adapter."""

    framework = "haystack"

    def normalize(self, trace: dict[str, Any], **ctx: Any) -> dict[str, Any]:
        runs = trace.get("pipeline_runs") or trace.get("runs") or []
        steps = _as_steps(runs, name_key="component")
        return self._wrap(
            trace,
            task=trace.get("task_description"),
            steps=steps,
            tools=trace.get("tools") or _collect_tools(steps),
            input_data=trace.get("inputs"),
            output=trace.get("outputs"),
        )


@register_adapter
class CrewAIAdapter(FrameworkAdapter):
    """CrewAI trace adapter."""

    framework = "crewai"

    def normalize(self, trace: dict[str, Any], **ctx: Any) -> dict[str, Any]:
        tasks = trace.get("tasks") or trace.get("crew_tasks") or []
        steps = _as_steps(tasks, name_key="description")
        return self._wrap(
            trace,
            task=trace.get("task_description") or trace.get("goal"),
            goal=trace.get("goal"),
            steps=steps,
            tools=trace.get("tools") or _collect_tools(steps),
            input_data=trace.get("inputs"),
            output=trace.get("output"),
        )


@register_adapter
class AutoGenAdapter(FrameworkAdapter):
    """AutoGen trace adapter."""

    framework = "autogen"

    def normalize(self, trace: dict[str, Any], **ctx: Any) -> dict[str, Any]:
        conversation = (
            trace.get("conversation")
            or trace.get("messages")
            or trace.get("chat_history")
            or []
        )
        messages = [m for m in conversation if isinstance(m, dict)]
        steps = _as_steps(messages, name_key="content")
        prompts = [
            {
                "role": m.get("role", "user"),
                "content": m.get("content", ""),
            }
            for m in messages
            if m.get("content")
        ]
        return self._wrap(
            trace,
            task=trace.get("task_description"),
            steps=steps,
            tools=trace.get("tools") or _collect_tools(steps),
            prompts=prompts,
            input_data=trace.get("input"),
            output=trace.get("summary") or trace.get("output"),
        )


@register_adapter
class SemanticKernelAdapter(FrameworkAdapter):
    """Semantic Kernel trace adapter."""

    framework = "semantic-kernel"

    def normalize(self, trace: dict[str, Any], **ctx: Any) -> dict[str, Any]:
        steps = _as_steps(trace.get("steps") or [])
        return self._wrap(
            trace,
            task=trace.get("task_description"),
            steps=steps,
            tools=trace.get("tools") or _collect_tools(steps),
            input_data=trace.get("input"),
            output=trace.get("output"),
        )


@register_adapter
class PydanticAIAdapter(FrameworkAdapter):
    """PydanticAI trace adapter."""

    framework = "pydantic-ai"

    def normalize(self, trace: dict[str, Any], **ctx: Any) -> dict[str, Any]:
        messages = (
            trace.get("all_messages")
            or trace.get("messages")
            or trace.get("steps")
            or []
        )
        steps = _as_steps(messages, name_key="content")
        prompts = [
            {
                "role": m.get("role", "user"),
                "content": m.get("content", ""),
            }
            for m in messages
            if isinstance(m, dict) and m.get("content")
        ]
        return self._wrap(
            trace,
            task=trace.get("task_description"),
            steps=steps,
            tools=trace.get("tools") or _collect_tools(steps),
            prompts=prompts,
            input_data=trace.get("input"),
            output=trace.get("output"),
        )