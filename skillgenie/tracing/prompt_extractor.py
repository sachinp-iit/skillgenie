# ============================================================================
# Project      : SkillGenie
# File         : prompt_extractor.py
# Description  : Extracts prompts from normalized execution traces.
#
#                Prompts are later used for skill generation, duplicate
#                detection, evaluation, and recommendations.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from collections import Counter
from copy import deepcopy
from typing import Any


class PromptExtractor:
    """
    Extracts prompts from execution traces.
    """

    def extract(
        self,
        trace: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Extract prompts from a trace.

        Args:
            trace: Normalized execution trace.

        Returns:
            List of normalized prompts.
        """

        prompts: list[dict[str, Any]] = []

        # Prompts captured explicitly
        for prompt in trace.get("prompts", []):

            prompts.append(
                self._normalize_prompt(prompt)
            )

        # Prompts embedded in workflow steps
        for step in trace.get("steps", []):

            prompt = step.get("prompt")

            if prompt is None:
                continue

            if isinstance(prompt, str):

                prompts.append(
                    {
                        "role": "user",
                        "content": prompt,
                        "model": None,
                        "temperature": None,
                        "metadata": {},
                    }
                )

            elif isinstance(prompt, dict):

                prompts.append(
                    self._normalize_prompt(prompt)
                )

        return prompts

    def unique_prompts(
        self,
        prompts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Remove duplicate prompts.

        Args:
            prompts: Extracted prompts.

        Returns:
            Unique prompts.
        """

        unique: dict[str, dict[str, Any]] = {}

        for prompt in prompts:

            unique[prompt["content"]] = prompt

        return list(unique.values())

    def statistics(
        self,
        prompts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Compute prompt statistics.

        Args:
            prompts: Extracted prompts.

        Returns:
            Prompt statistics.
        """

        roles: Counter[str] = Counter()

        for prompt in prompts:

            roles[prompt["role"]] += 1

        return {
            "total_prompts": len(prompts),
            "unique_prompts": len(
                self.unique_prompts(prompts)
            ),
            "roles": dict(roles),
        }

    def _normalize_prompt(
        self,
        prompt: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize prompt.

        Args:
            prompt: Raw prompt.

        Returns:
            Normalized prompt.
        """

        return {
            "role": prompt.get("role", "user"),
            "content": prompt.get("content", ""),
            "model": prompt.get("model"),
            "temperature": prompt.get("temperature"),
            "metadata": deepcopy(
                prompt.get("metadata", {})
            ),
        }