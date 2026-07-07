# ============================================================================
# Project      : SkillGenie
# File         : parser.py
# Description  : Normalizes execution traces from different Agentic AI
#                frameworks into a common SkillGenie trace format.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from copy import deepcopy
from datetime import datetime
from typing import Any


class TraceParser:
    """
    Parses execution traces into a common format.
    """

    def __init__(self) -> None:
        """
        Initialize parser.
        """

        # Supported frameworks
        self._supported_frameworks = {
            "langgraph",
            "langchain",
            "llamaindex",
            "haystack",
            "crewai",
            "autogen",
            "semantic-kernel",
            "pydantic-ai",
            "custom",
        }

    def parse(
        self,
        trace: dict[str, Any],
        framework: str = "custom",
    ) -> dict[str, Any]:
        """
        Parse a raw execution trace.

        Args:
            trace: Raw execution trace.
            framework: Source framework.

        Returns:
            Normalized trace.
        """

        framework = framework.lower()

        if framework not in self._supported_frameworks:
            raise ValueError(
                f"Unsupported framework: {framework}"
            )

        normalized_trace = {
            "framework": framework,
            "trace_id": trace.get("trace_id"),
            "execution_id": trace.get("execution_id"),
            "task": trace.get("task", ""),
            "goal": trace.get("goal", ""),
            "input": deepcopy(trace.get("input", {})),
            "output": deepcopy(trace.get("output", {})),
            "steps": deepcopy(trace.get("steps", [])),
            "tools": deepcopy(trace.get("tools", [])),
            "prompts": deepcopy(trace.get("prompts", [])),
            "llm_calls": deepcopy(trace.get("llm_calls", [])),
            "errors": deepcopy(trace.get("errors", [])),
            "metadata": deepcopy(trace.get("metadata", {})),
            "created_at": trace.get(
                "created_at",
                datetime.utcnow().isoformat(),
            ),
        }

        normalized_trace["statistics"] = self.extract_statistics(
            normalized_trace
        )

        return normalized_trace

    def extract_statistics(
        self,
        trace: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract execution statistics.

        Args:
            trace: Normalized trace.

        Returns:
            Trace statistics.
        """

        return {
            "step_count": len(trace.get("steps", [])),
            "tool_count": len(trace.get("tools", [])),
            "prompt_count": len(trace.get("prompts", [])),
            "llm_call_count": len(trace.get("llm_calls", [])),
            "error_count": len(trace.get("errors", [])),
        }

    def validate(
        self,
        trace: dict[str, Any],
    ) -> bool:
        """
        Validate normalized trace.

        Args:
            trace: Normalized trace.

        Returns:
            True if valid.
        """

        required_fields = [
            "framework",
            "task",
            "steps",
            "tools",
            "prompts",
        ]

        for field in required_fields:

            if field not in trace:
                return False

        return True