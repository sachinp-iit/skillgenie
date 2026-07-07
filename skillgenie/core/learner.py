# ============================================================================
# Project      : SkillGenie
# File         : learner.py
# Description  : Learns reusable skills from execution traces.
#
#                This component orchestrates the complete learning pipeline.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from typing import Any
from uuid import UUID

from skillgenie.config import Config
from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.capability_repository import (
    CapabilityRepository,
)
from skillgenie.database.repositories.trace_repository import (
    TraceRepository,
)
from skillgenie.tracing.duplicate_detector import DuplicateDetector
from skillgenie.tracing.input_output_extractor import (
    InputOutputExtractor,
)
from skillgenie.tracing.parser import TraceParser
from skillgenie.tracing.prompt_extractor import PromptExtractor
from skillgenie.tracing.skill_generator import SkillGenerator
from skillgenie.tracing.tool_extractor import ToolExtractor
from skillgenie.tracing.workflow_extractor import (
    WorkflowExtractor,
)
from skillgenie.utils.logger import Logger


class SkillLearner:
    """
    Learns reusable skills from execution traces.
    """

    def __init__(
        self,
        config: Config,
        database: DatabaseManager,
    ):
        """
        Initialize Skill Learner.

        Args:
            config: SkillGenie configuration.
            database: Database manager.
        """

        # Store dependencies
        self._config = config
        self._database = database

        # Logger
        self._logger = Logger(config).log

        # Repositories
        self._trace_repository = TraceRepository(database)
        self._skill_repository = CapabilityRepository(database)

        # Tracing components
        self._trace_parser = TraceParser()
        self._workflow_extractor = WorkflowExtractor()
        self._tool_extractor = ToolExtractor()
        self._prompt_extractor = PromptExtractor()
        self._io_extractor = InputOutputExtractor()
        self._skill_generator = SkillGenerator()
        self._duplicate_detector = DuplicateDetector(
            self._skill_repository
        )

    def learn(
        self,
        trace_id: str,
    ):
        """
        Learn a reusable skill from a trace.

        Args:
            trace_id: Trace identifier.

        Returns:
            Generated skill or existing duplicate.
        """

        self._logger.info(
            f"Starting learning pipeline for trace '{trace_id}'."
        )

        # Load raw trace
        raw_trace = self._load_trace(trace_id)

        # Parse trace
        trace = self._parse_trace(raw_trace)

        # Validate trace
        self._validate_trace(trace)

        # Extract workflow
        workflow = self._extract_workflow(trace)

        # Extract tools
        tools = self._extract_tools(trace)

        # Extract prompts
        prompts = self._extract_prompts(trace)

        # Extract inputs & outputs
        input_output = self._extract_input_output(trace)

        # Generate candidate skill
        skill = self._generate_skill(
            trace=trace,
            workflow=workflow,
            tools=tools,
            prompts=prompts,
            input_output=input_output,
        )

        # Check duplicates
        duplicate = self._find_duplicate(skill)

        if duplicate is not None:

            self._logger.info(
                f"Duplicate skill found: {skill.name}"
            )

            return duplicate

        # Persist new skill
        self._save_skill(skill)

        self._logger.info(
            f"Generated new skill: {skill.name}"
        )

        return skill

    def learn_all(self):
        """
        Learn skills from all traces.
        """

        self._logger.info(
            "Learning from all available traces."
        )

        traces = self._trace_repository.list()

        learned_skills = []

        for trace in traces:

            trace_id = trace["id"]

            learned_skills.append(
                self.learn(str(trace_id))
            )

        return learned_skills
    
    def _load_trace(
        self,
        trace_id: str,
    ) -> dict[str, Any]:
        """
        Load a trace from the repository.

        Args:
            trace_id: Trace identifier.

        Returns:
            Raw execution trace.
        """

        self._logger.debug(
            f"Loading trace '{trace_id}'."
        )

        trace = self._trace_repository.get_by_id(
            UUID(trace_id)
        )

        if trace is None:

            raise ValueError(
                f"Trace '{trace_id}' does not exist."
            )

        return dict(trace)

    def _parse_trace(
        self,
        trace: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Parse raw execution trace.

        Args:
            trace: Raw trace.

        Returns:
            Normalized trace.
        """

        framework = trace.get(
            "agent_framework",
            "custom",
        )

        self._logger.debug(
            f"Parsing {framework} trace."
        )

        return self._trace_parser.parse(
            trace=trace,
            framework=framework,
        )

    def _validate_trace(
        self,
        trace: dict[str, Any],
    ) -> None:
        """
        Validate normalized trace.

        Args:
            trace: Normalized trace.
        """

        self._logger.debug(
            "Validating normalized trace."
        )

        if not self._trace_parser.validate(trace):

            raise ValueError(
                "Trace validation failed."
            )

    def _extract_workflow(
        self,
        trace: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract workflow.

        Args:
            trace: Normalized trace.

        Returns:
            Workflow.
        """

        self._logger.debug(
            "Extracting workflow."
        )

        return self._workflow_extractor.extract(
            trace
        )

    def _extract_tools(
        self,
        trace: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Extract tools.

        Args:
            trace: Normalized trace.

        Returns:
            List of tools.
        """

        self._logger.debug(
            "Extracting tools."
        )

        tools = self._tool_extractor.extract(
            trace
        )

        return self._tool_extractor.unique_tools(
            tools
        )

    def _extract_prompts(
        self,
        trace: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Extract prompts.

        Args:
            trace: Normalized trace.

        Returns:
            List of prompts.
        """

        self._logger.debug(
            "Extracting prompts."
        )

        prompts = self._prompt_extractor.extract(
            trace
        )

        return self._prompt_extractor.unique_prompts(
            prompts
        )

    def _extract_input_output(
        self,
        trace: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Extract execution inputs and outputs.

        Args:
            trace: Normalized trace.

        Returns:
            Input/output information.
        """

        self._logger.debug(
            "Extracting execution inputs and outputs."
        )

        return self._io_extractor.extract(
            trace
        )
        
    def _generate_skill(
        self,
        trace: dict[str, Any],
        workflow: dict[str, Any],
        tools: list[dict[str, Any]],
        prompts: list[dict[str, Any]],
        input_output: dict[str, Any],
    ):
        """
        Generate a candidate skill.

        Args:
            trace: Normalized trace.
            workflow: Extracted workflow.
            tools: Extracted tools.
            prompts: Extracted prompts.
            input_output: Extracted input/output.

        Returns:
            Generated skill.
        """

        self._logger.debug(
            "Generating candidate skill."
        )

        return self._skill_generator.generate(
            trace=trace,
            workflow=workflow,
            tools=tools,
            prompts=prompts,
            input_output=input_output,
        )

    def _find_duplicate(
        self,
        skill,
    ):
        """
        Check whether the generated skill already exists.

        Args:
            skill: Generated skill.

        Returns:
            Existing skill if found, otherwise None.
        """

        self._logger.debug(
            f"Checking duplicate for '{skill.name}'."
        )

        return self._duplicate_detector.find_duplicate(
            skill
        )

    def _save_skill(
        self,
        skill,
    ) -> None:
        """
        Persist a newly generated skill.

        Args:
            skill: Generated skill.
        """

        self._logger.debug(
            f"Persisting skill '{skill.name}'."
        )

        self._skill_repository.create(
            capability_id=skill.id,
            name=skill.name,
            description=skill.description,
            category=skill.category,
            version=skill.version,
            status=skill.status.value,
        )

        self._update_metrics(skill)

        self._audit(
            skill=skill,
            action="CREATE",
        )

    def _update_metrics(
        self,
        skill,
    ) -> None:
        """
        Update initial skill metrics.

        Args:
            skill: Generated skill.
        """

        self._logger.debug(
            f"Initializing metrics for '{skill.name}'."
        )

        # Metrics initialization will be implemented
        # after the scoring engine is completed.

    def _audit(
        self,
        skill,
        action: str,
    ) -> None:
        """
        Create an audit entry.

        Args:
            skill: Generated skill.
            action: Audit action.
        """

        self._logger.debug(
            f"Audit action '{action}' for '{skill.name}'."
        )

        # Audit integration will be implemented after
        # the audit service is completed.

    def relearn(
        self,
        skill_id: str,
    ):
        """
        Relearn an existing skill.

        Args:
            skill_id: Skill identifier.
        """

        self._logger.info(
            f"Relearning skill '{skill_id}'."
        )

        # Existing execution traces associated with the
        # skill will be reprocessed to improve quality,
        # confidence and recommendation ranking.

        raise NotImplementedError(
            "Skill relearning is not implemented yet."
        )