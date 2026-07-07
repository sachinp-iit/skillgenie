# ============================================================================
# Project      : SkillGenie
# File         : skill_generator.py
# Description  : Generates a candidate skill from normalized execution data.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from datetime import datetime
from typing import Any
from uuid import uuid4

from skillgenie.models.capability import Capability


class SkillGenerator:
    """
    Generates candidate skills from extracted execution artifacts.
    """

    def generate(
        self,
        trace: dict[str, Any],
        workflow: dict[str, Any],
        tools: list[dict[str, Any]],
        prompts: list[dict[str, Any]],
        input_output: dict[str, Any],
    ) -> Capability:
        """
        Generate a candidate skill.

        Args:
            trace: Normalized trace.
            workflow: Extracted workflow.
            tools: Extracted tools.
            prompts: Extracted prompts.
            input_output: Extracted input/output.

        Returns:
            Candidate skill.
        """

        skill = Capability(

            # Identity
            id=uuid4(),

            # Basic information
            name=self._generate_name(trace),
            description=self._generate_description(trace),
            category=self._generate_category(trace),

            # Workflow
            workflow=workflow,

            # Metadata
            metadata={
                "framework": trace.get("framework"),
                "task": trace.get("task"),
                "goal": trace.get("goal"),
                "tools": tools,
                "prompts": prompts,
                "input_output": input_output,
                "generated_at": datetime.utcnow().isoformat(),
            },

            # Source traces
            created_from=[],

            # Relationship graph
            relationship_graph={
                "parents": [],
                "children": [],
                "related": [],
            },
        )

        return skill

    def _generate_name(
        self,
        trace: dict[str, Any],
    ) -> str:
        """
        Generate skill name.
        """

        task = trace.get("task", "").strip()

        if task:

            return task.title()

        return "Unnamed Skill"

    def _generate_description(
        self,
        trace: dict[str, Any],
    ) -> str:
        """
        Generate skill description.
        """

        goal = trace.get("goal", "").strip()

        if goal:

            return goal

        return "Automatically generated skill."

    def _generate_category(
        self,
        trace: dict[str, Any],
    ) -> str:
        """
        Generate skill category.
        """

        metadata = trace.get("metadata", {})

        return metadata.get(
            "category",
            "general",
        )