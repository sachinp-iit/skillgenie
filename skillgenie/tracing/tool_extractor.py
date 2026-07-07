# ============================================================================
# Project      : SkillGenie
# File         : tool_extractor.py
# Description  : Extracts tools used during execution from a normalized trace.
#
#                The extracted information is later used for skill generation,
#                recommendation, analytics, and relationship graph creation.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from collections import Counter
from copy import deepcopy
from typing import Any


class ToolExtractor:
    """
    Extracts tool usage information from execution traces.
    """

    def extract(
        self,
        trace: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Extract all tools used in a trace.

        Args:
            trace: Normalized trace.

        Returns:
            List of extracted tools.
        """

        extracted_tools: list[dict[str, Any]] = []

        # Tools explicitly captured
        for tool in trace.get("tools", []):

            extracted_tools.append(
                self._normalize_tool(tool)
            )

        # Tools embedded inside workflow steps
        for step in trace.get("steps", []):

            tool = step.get("tool")

            if tool is None:
                continue

            if isinstance(tool, str):

                extracted_tools.append(
                    {
                        "name": tool,
                        "type": "unknown",
                        "version": None,
                        "input": {},
                        "output": {},
                        "metadata": {},
                    }
                )

            elif isinstance(tool, dict):

                extracted_tools.append(
                    self._normalize_tool(tool)
                )

        return extracted_tools

    def unique_tools(
        self,
        tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Remove duplicate tools.

        Args:
            tools: Extracted tools.

        Returns:
            Unique tools.
        """

        unique: dict[str, dict[str, Any]] = {}

        for tool in tools:

            unique[tool["name"]] = tool

        return list(unique.values())

    def usage_statistics(
        self,
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Compute tool usage statistics.

        Args:
            tools: Extracted tools.

        Returns:
            Statistics.
        """

        counter: Counter[str] = Counter()

        for tool in tools:

            counter[tool["name"]] += 1

        return {
            "total_tools": len(tools),
            "unique_tools": len(counter),
            "usage": dict(counter),
        }

    def _normalize_tool(
        self,
        tool: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize tool definition.

        Args:
            tool: Raw tool.

        Returns:
            Normalized tool.
        """

        return {
            "name": tool.get("name"),
            "type": tool.get("type", "unknown"),
            "version": tool.get("version"),
            "input": deepcopy(tool.get("input", {})),
            "output": deepcopy(tool.get("output", {})),
            "metadata": deepcopy(tool.get("metadata", {})),
        }