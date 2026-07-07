# ============================================================================
# Project      : SkillGenie
# File         : input_output_extractor.py
# Description  : Extracts and normalizes inputs and outputs from execution
#                traces.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from copy import deepcopy
from typing import Any


class InputOutputExtractor:
    """
    Extracts execution inputs and outputs.
    """

    def extract(
        self,
        trace: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract normalized inputs and outputs.

        Args:
            trace: Normalized execution trace.

        Returns:
            Normalized input/output information.
        """

        return {
            "input": self._extract_input(trace),
            "output": self._extract_output(trace),
            "statistics": self._statistics(trace),
        }

    def _extract_input(
        self,
        trace: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract execution input.
        """

        return deepcopy(
            trace.get("input", {})
        )

    def _extract_output(
        self,
        trace: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract execution output.
        """

        return deepcopy(
            trace.get("output", {})
        )

    def _statistics(
        self,
        trace: dict[str, Any],
    ) -> dict[str, int]:
        """
        Compute basic input/output statistics.
        """

        input_data = trace.get("input", {})
        output_data = trace.get("output", {})

        return {
            "input_fields": len(input_data),
            "output_fields": len(output_data),
            "step_count": len(trace.get("steps", [])),
        }

    def flatten(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Flatten nested dictionaries.

        Args:
            payload: Dictionary to flatten.

        Returns:
            Flattened dictionary.
        """

        flattened: dict[str, Any] = {}

        self._flatten(
            payload=payload,
            result=flattened,
        )

        return flattened

    def _flatten(
        self,
        payload: dict[str, Any],
        result: dict[str, Any],
        prefix: str = "",
    ) -> None:
        """
        Recursive flatten implementation.
        """

        for key, value in payload.items():

            full_key = (
                f"{prefix}.{key}"
                if prefix
                else key
            )

            if isinstance(value, dict):

                self._flatten(
                    payload=value,
                    result=result,
                    prefix=full_key,
                )

            else:

                result[full_key] = value