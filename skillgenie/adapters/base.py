# ============================================================================
# Project      : SkillGenie
# File         : base.py
# Description  : Base contract and registry for framework adapters.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class FrameworkAdapter(ABC):
    """
    Converts a framework-specific execution trace into the common SkillGenie
    raw trace shape consumed by TraceParser.
    """

    framework: str = "custom"

    @abstractmethod
    def normalize(
        self,
        trace: dict[str, Any],
        **_: Any,
    ) -> dict[str, Any]:
        """
        Normalize a framework trace into the canonical raw shape.
        """

    def _wrap(
        self,
        trace: dict[str, Any],
        *,
        task: Any = "",
        goal: Any = "",
        steps: Any = None,
        tools: Any = None,
        prompts: Any = None,
        llm_calls: Any = None,
        errors: Any = None,
        input_data: Any = None,
        output: Any = None,
    ) -> dict[str, Any]:
        """
        Build the canonical raw trace dict with defensive defaults.
        """

        return {
            "trace_id": trace.get("trace_id") or trace.get("id"),
            "execution_id": trace.get("execution_id"),
            "task": task or trace.get("task", ""),
            "goal": goal or trace.get("goal", ""),
            "input": input_data if input_data is not None else trace.get("input", {}),
            "output": (
                output if output is not None else trace.get("output", {})
            ),
            "steps": steps if steps is not None else trace.get("steps", []),
            "tools": tools if tools is not None else trace.get("tools", []),
            "prompts": (
                prompts if prompts is not None else trace.get("prompts", [])
            ),
            "llm_calls": (
                llm_calls if llm_calls is not None else trace.get("llm_calls", [])
            ),
            "errors": (
                errors if errors is not None else trace.get("errors", [])
            ),
            "metadata": dict(trace.get("metadata", {}) or {}),
            "created_at": trace.get("created_at"),
        }


# -----------------------------------------------------------------------------
# Registry
# -----------------------------------------------------------------------------

_ADAPTERS: dict[str, type[FrameworkAdapter]] = {}


def register_adapter(adapter_class: type[FrameworkAdapter]) -> type[FrameworkAdapter]:
    """
    Register a framework adapter class.
    """

    name = adapter_class.framework

    _ADAPTERS[name] = adapter_class

    return adapter_class


def get_adapter(framework: str) -> FrameworkAdapter:
    """
    Return the adapter for a framework, falling back to the generic adapter.
    """

    name = framework.lower()

    adapter_cls = _ADAPTERS.get(name)

    if adapter_cls is None:
        from skillgenie.adapters.generic import GenericAdapter

        adapter_cls = _ADAPTERS.get("custom", GenericAdapter)

    return adapter_cls()


def supported_frameworks() -> list[str]:
    """
    List of registered framework names.
    """

    return sorted(_ADAPTERS.keys())