# ============================================================================
# Project      : SkillGenie
# File         : workflow_extractor.py
# Description  : Extracts an executable workflow from a normalized execution
#                trace. The generated workflow is framework agnostic and is
#                later used for skill generation.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from copy import deepcopy
from typing import Any


class WorkflowExtractor:
    """
    Extracts workflow from a normalized execution trace.
    """

    def extract(
        self,
        trace: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract workflow.

        Args:
            trace: Normalized trace.

        Returns:
            Normalized workflow.
        """

        workflow = {
            "name": trace.get("task", "Unnamed Workflow"),
            "framework": trace.get("framework"),
            "steps": [],
            "metadata": deepcopy(trace.get("metadata", {})),
        }

        for index, step in enumerate(trace.get("steps", []), start=1):

            workflow["steps"].append(
                self._normalize_step(
                    step=step,
                    order=index,
                )
            )

        workflow["statistics"] = self._workflow_statistics(workflow)

        return workflow

    def _normalize_step(
        self,
        step: dict[str, Any],
        order: int,
    ) -> dict[str, Any]:
        """
        Normalize a workflow step.

        Args:
            step: Raw workflow step.
            order: Execution order.

        Returns:
            Normalized step.
        """

        return {
            "order": order,
            "name": step.get("name", f"Step {order}"),
            "type": step.get("type", "task"),
            "description": step.get("description", ""),
            "tool": step.get("tool"),
            "input": deepcopy(step.get("input", {})),
            "output": deepcopy(step.get("output", {})),
            "status": step.get("status", "SUCCESS"),
            "duration_ms": step.get("duration_ms", 0),
            "metadata": deepcopy(step.get("metadata", {})),
        }

    def _workflow_statistics(
        self,
        workflow: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Compute workflow statistics.

        Args:
            workflow: Workflow dictionary.

        Returns:
            Workflow statistics.
        """

        steps = workflow["steps"]

        return {
            "total_steps": len(steps),
            "tool_steps": len(
                [
                    step
                    for step in steps
                    if step["tool"] is not None
                ]
            ),
            "total_duration_ms": sum(
                step["duration_ms"]
                for step in steps
            ),
        }

    def flatten(
        self,
        workflow: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Flatten workflow into ordered steps.

        Args:
            workflow: Workflow.

        Returns:
            Ordered list of steps.
        """

        return deepcopy(workflow["steps"])