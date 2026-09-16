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

from __future__ import annotations

from typing import Any
from uuid import UUID

from skillgenie.config import Config
from skillgenie.core.evaluator import SkillEvaluator
from skillgenie.core.scorer import SkillScorer
from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.audit_repository import AuditRepository
from skillgenie.database.repositories.capability_repository import (
    CapabilityRepository,
)
from skillgenie.database.repositories.execution_repository import (
    ExecutionRepository,
)
from skillgenie.database.repositories.metrics_repository import (
    MetricsRepository,
)
from skillgenie.database.repositories.trace_repository import (
    TraceRepository,
)
from skillgenie.embeddings.base import EmbeddingProvider
from skillgenie.exceptions import CapabilityNotFoundError
from skillgenie.models.capability import Capability
from skillgenie.storage.skill_store import SkillStore
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
        trace_repository: TraceRepository | None = None,
        skill_repository: CapabilityRepository | None = None,
        metrics_repository: MetricsRepository | None = None,
        audit_repository: AuditRepository | None = None,
        execution_repository: ExecutionRepository | None = None,
        embedding_provider: EmbeddingProvider | None = None,
    ):
        """
        Initialize Skill Learner.

        Args:
            config: SkillGenie configuration.
            database: Database manager.
            trace_repository: Optional repository override.
            skill_repository: Optional repository override.
            metrics_repository: Optional repository override.
            audit_repository: Optional repository override.
            execution_repository: Optional repository override.
            embedding_provider: Optional embedding provider.
        """

        self._config = config
        self._database = database

        self._logger = Logger(config).log

        self._trace_repository = (
            trace_repository or TraceRepository(database)
        )
        self._skill_repository = (
            skill_repository or CapabilityRepository(database)
        )
        self._metrics_repository = (
            metrics_repository or MetricsRepository(database)
        )
        self._audit_repository = (
            audit_repository or AuditRepository(database)
        )
        self._execution_repository = (
            execution_repository or ExecutionRepository(database)
        )

        self._embedding_provider = embedding_provider

        self._store = SkillStore(
            config=config,
            repository=self._skill_repository,
            embedding_provider=embedding_provider,
        )

        self._scorer = SkillScorer(config)

        self._duplicate_detector = DuplicateDetector(
            repository=self._skill_repository,
            config=config,
            scorer=self._scorer,
            store=self._store,
        )

        self._evaluator = SkillEvaluator(
            config=config,
            database=database,
            skill_repository=self._skill_repository,
            metrics_repository=self._metrics_repository,
            audit_repository=self._audit_repository,
            execution_repository=self._execution_repository,
            scorer=self._scorer,
        )

        # Tracing components
        self._trace_parser = TraceParser()
        self._workflow_extractor = WorkflowExtractor()
        self._tool_extractor = ToolExtractor()
        self._prompt_extractor = PromptExtractor()
        self._io_extractor = InputOutputExtractor()
        self._skill_generator = SkillGenerator()

    @property
    def store(self) -> SkillStore:
        """
        Skill store backing the learner.
        """

        return self._store

    def learn(
        self,
        trace_id: str,
    ) -> Capability:
        """
        Learn a reusable skill from a trace.

        Args:
            trace_id: Trace identifier.

        Returns:
            Generated skill or matched duplicate.
        """

        self._logger.info(
            f"Starting learning pipeline for trace '{trace_id}'."
        )

        raw_trace = self._load_trace(trace_id)
        trace = self._parse_trace(raw_trace)
        self._validate_trace(trace)

        workflow = self._extract_workflow(trace)
        tools = self._extract_tools(trace)
        prompts = self._extract_prompts(trace)
        input_output = self._extract_input_output(trace)

        skill = self._generate_skill(
            trace=trace,
            workflow=workflow,
            tools=tools,
            prompts=prompts,
            input_output=input_output,
        )

        self._finalize_skill(
            skill,
            trace=trace,
            tools=tools,
            workflow=workflow,
        )

        threshold = self._config.get_float(
            "similarity.threshold",
            0.85,
        )

        duplicate = self._duplicate_detector.find_duplicate(
            skill,
            threshold=threshold,
        )

        if duplicate is not None:
            self._logger.info(
                f"Duplicate skill found: {skill.name}"
            )

            self._attach_trace(duplicate, trace_id)

            return duplicate

        self._save_skill(skill, trace_id)

        self._evaluator.evaluate(skill)

        self._logger.info(
            f"Generated new skill: {skill.name} "
            f"[{skill.status.value}]"
        )

        return skill

    def learn_all(self) -> list[Capability]:
        """
        Learn skills from all traces.
        """

        self._logger.info(
            "Learning from all available traces."
        )

        traces = self._trace_repository.list()

        learned_skills: list[Capability] = []

        for trace in traces:
            trace_id = trace["id"]

            learned_skills.append(
                self.learn(str(trace_id))
            )

        return learned_skills

    def relearn(
        self,
        skill_id: str,
    ) -> Capability:
        """
        Relearn an existing skill from its source traces.

        Args:
            skill_id: Skill identifier.
        """

        self._logger.info(
            f"Relearning skill '{skill_id}'."
        )

        capability_id = UUID(str(skill_id))

        skill = self._store.get(capability_id)

        if skill is None:
            raise CapabilityNotFoundError(
                f"Skill '{skill_id}' does not exist."
            )

        source_trace_ids = skill.created_from

        new_workflow = None
        new_tools: list[dict[str, Any]] = []
        new_prompts: list[dict[str, Any]] = []
        new_input_output: dict[str, Any] = {}

        for trace_id in source_trace_ids:
            trace = self._parse_trace(self._load_trace(trace_id))

            work = self._extract_workflow(trace)
            tools = self._extract_tools(trace)
            prompts = self._extract_prompts(trace)
            io = self._extract_input_output(trace)

            new_workflow = new_workflow or work
            new_tools.extend(tools)
            new_prompts.extend(prompts)
            new_input_output = new_input_output or io

        if new_workflow is None:
            raise ValueError(
                f"Skill '{skill_id}' has no source traces to relearn from."
            )

        skill.workflow = new_workflow
        skill.embedding = self._embed_skill(
            skill,
            trace=skill.workflow.get("name", skill.name) or skill.name,
            tools=new_tools,
            workflow=new_workflow,
        )

        enriched_metadata = dict(skill.metadata or {})
        enriched_metadata["tools"] = new_tools
        enriched_metadata["prompts"] = new_prompts
        enriched_metadata["input_output"] = new_input_output
        enriched_metadata["search_profile"] = self._search_profile(
            skill,
            trace=(skill.workflow.get("name", skill.name) or skill.name),
            tools=new_tools,
        )
        skill.metadata = enriched_metadata

        self._store.update(
            capability_id,
            workflow=new_workflow,
            embedding=skill.embedding,
            metadata=enriched_metadata,
        )

        self._evaluator.reevaluate(skill)

        self._audit(
            skill=skill,
            action="RELEARNED",
            remarks=f"Reprocessed {len(source_trace_ids)} trace(s).",
        )

        return skill

    def _load_trace(self, trace_id: str) -> dict[str, Any]:
        """
        Load a trace from the repository.

        Args:
            trace_id: Trace identifier.

        Returns:
            Raw execution trace.
        """

        self._logger.debug(f"Loading trace '{trace_id}'.")

        trace = self._trace_repository.get_by_id(UUID(trace_id))

        if trace is None:
            raise ValueError(f"Trace '{trace_id}' does not exist.")

        return dict(trace)

    def _parse_trace(self, trace: dict[str, Any]) -> dict[str, Any]:
        """
        Parse raw execution trace.

        Args:
            trace: Stored trace row containing the raw execution payload
                under the 'trace' key.

        Returns:
            Normalized trace.
        """

        framework = trace.get("agent_framework", "custom")

        raw = trace.get("trace")

        if not isinstance(raw, dict):
            raise ValueError("Trace payload is empty or malformed.")

        merged = dict(raw)

        merged.setdefault(
            "task",
            trace.get("task_description") or trace.get("task", ""),
        )
        merged.setdefault(
            "goal",
            trace.get("goal") or trace.get("task_description", ""),
        )
        merged.setdefault("metadata", trace.get("metadata") or {})

        self._logger.debug(f"Parsing {framework} trace.")

        return self._trace_parser.parse(merged, framework=framework)

    def _validate_trace(self, trace: dict[str, Any]) -> None:
        """
        Validate normalized trace.

        Args:
            trace: Normalized trace.
        """

        self._logger.debug("Validating normalized trace.")

        if not self._trace_parser.validate(trace):
            raise ValueError("Trace validation failed.")

    def _extract_workflow(self, trace: dict[str, Any]) -> dict[str, Any]:
        """
        Extract workflow.
        """

        return self._workflow_extractor.extract(trace)

    def _extract_tools(self, trace: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Extract tools.
        """

        tools = self._tool_extractor.extract(trace)

        return self._tool_extractor.unique_tools(tools)

    def _extract_prompts(self, trace: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Extract prompts.
        """

        prompts = self._prompt_extractor.extract(trace)

        return self._prompt_extractor.unique_prompts(prompts)

    def _extract_input_output(self, trace: dict[str, Any]) -> dict[str, Any]:
        """
        Extract execution inputs and outputs.
        """

        return self._io_extractor.extract(trace)

    def _generate_skill(
        self,
        trace: dict[str, Any],
        workflow: dict[str, Any],
        tools: list[dict[str, Any]],
        prompts: list[dict[str, Any]],
        input_output: dict[str, Any],
    ) -> Capability:
        """
        Generate a candidate skill.
        """

        return self._skill_generator.generate(
            trace=trace,
            workflow=workflow,
            tools=tools,
            prompts=prompts,
            input_output=input_output,
        )

    def _finalize_skill(
        self,
        skill: Capability,
        trace: dict[str, Any],
        tools: list[dict[str, Any]],
        workflow: dict[str, Any],
    ) -> None:
        """
        Enrich a generated skill with embeddings and search metadata.
        """

        task_text = trace.get("task", "") or trace.get("goal", "") or skill.name

        skill.embedding = self._embed_skill(
            skill,
            trace=task_text,
            tools=tools,
            workflow=workflow,
        )

        metadata = dict(skill.metadata or {})

        metadata["search_profile"] = self._search_profile(
            skill,
            trace=task_text,
            tools=tools,
        )

        skill.metadata = metadata

    def _embed_skill(
        self,
        skill: Capability,
        trace: str,
        tools: list[dict[str, Any]],
        workflow: dict[str, Any],
    ) -> list[float]:
        """
        Generate the embedding for a skill.
        """

        if self._embedding_provider is None:
            return []

        tool_names = " ".join(
            str(tool.get("name", "")) if isinstance(tool, dict) else str(tool)
            for tool in tools
        )

        purpose = (
            f"{skill.name}. {skill.description}. "
            f"Task: {trace}. Tools: {tool_names}."
        )

        return self._embedding_provider.embed_text(purpose)

    def _search_profile(
        self,
        skill: Capability,
        trace: str,
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Lexical fallback profile for no-embedding searches.
        """

        tool_names = " ".join(
            str(tool.get("name", "")) if isinstance(tool, dict) else str(tool)
            for tool in tools
        )

        return {
            "tokens": (
                f"{skill.name} {skill.description} {trace} {tool_names}"
            ),
        }

    def _attach_trace(
        self,
        skill: Capability,
        trace_id: str,
    ) -> None:
        """
        Associate a source trace with an existing skill.
        """

        if trace_id in skill.created_from:
            self._logger.debug(
                f"Trace '{trace_id}' already attached to '{skill.name}'."
            )
            return

        skill.created_from.append(trace_id)

        self._skill_repository.update(
            capability_id=skill.id,
            created_from=skill.created_from,
        )

        self._audit(
            skill=skill,
            action="TRACE_ATTACHED",
            remarks=f"Attached trace '{trace_id}'.",
        )

    def _save_skill(self, skill: Capability, trace_id: str) -> None:
        """
        Persist a newly generated skill.
        """

        self._logger.debug(f"Persisting skill '{skill.name}'.")

        skill.created_from.append(trace_id)

        self._store.create(skill)

        self._audit(
            skill=skill,
            action="CREATE",
            remarks=f"Created from trace '{trace_id}'.",
        )

    def _audit(
        self,
        skill: Capability,
        action: str,
        remarks: str = "",
    ) -> None:
        """
        Create an audit entry.
        """

        self._logger.debug(f"Audit action '{action}' for '{skill.name}'.")

        from uuid import uuid4

        self._audit_repository.create(
            audit_id=uuid4(),
            capability_id=skill.id,
            action=action,
            performed_by="learner",
            remarks=remarks,
            payload={
                "name": skill.name,
                "version": skill.version,
            },
        )