# ============================================================================
# Project      : SkillGenie
# File         : custom.py
# Description  : Generic decorator-based recording hook for any Python
#                function or custom agent framework.
#
# Usage:
#     recorder = CustomRecorder(config, trace_repository)
#
#     @recorder.trace(task="Fetch stock prices")
#     def run_agent(input_data):
#         ...
#         return {"result": "ok"}
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable

from skillgenie.config import Config
from skillgenie.integrations.base import BaseRecorder


class CustomRecorder(BaseRecorder):
    """
    Decorator-based recorder for arbitrary agent functions.
    """

    def __init__(self, config: Config, trace_repository: Any):
        super().__init__(config, trace_repository, framework="custom")

    def trace(
        self,
        task: str = "",
        goal: str = "",
        inspect_result: bool = False,
    ) -> Callable:
        """
        Decorator that records a function invocation as an execution trace.

        Args:
            task: Human-readable task name. When empty, the function name is used.
            goal: Optional goal description.
            inspect_result: When True, the return value is treated as a dict
                whose ``steps``/``tools`` keys feed the trace.
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                start = time.monotonic()
                result = func(*args, **kwargs)
                elapsed_ms = (time.monotonic() - start) * 1000.0

                steps: list[dict[str, Any]] = []
                tools: list[dict[str, Any]] = []

                if inspect_result and isinstance(result, dict):
                    steps = result.get("steps", []) or []
                    tools = result.get("tools", []) or []

                self.record(
                    task=task or func.__name__,
                    goal=goal,
                    steps=steps,
                    tools=tools,
                    metadata={"input": _inputs(args, kwargs), "output": _output(result)},
                    execution_time_ms=round(elapsed_ms, 3),
                )

                return result

            return wrapper

        return decorator


def _inputs(args: tuple, kwargs: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for index, value in enumerate(args):
        values[f"arg_{index}"] = _safe_repr(value)
    values.update({key: _safe_repr(value) for key, value in kwargs.items()})
    return values


def _output(result: Any) -> dict[str, Any]:
    return {"result": _safe_repr(result)}


def _safe_repr(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        import json

        return json.loads(json.dumps(value, default=str)[:2000])
    except (TypeError, ValueError):
        return str(value)[:2000]