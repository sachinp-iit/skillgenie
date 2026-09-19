# ============================================================================
# Project      : SkillGenie
# File         : composer.py
# Description  : Compositional planner.  Decomposes a composite task into
#                sub-tasks, matches each sub-task to an atomic skill, chains
#                them into a plan, executes the plan through a runner, and
#                learns the successful composite as a new skill.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import re
from typing import Any, Callable
from uuid import UUID

from skillgenie.config import Config
from skillgenie.constants import SkillStatus
from skillgenie.core.recommender import SkillRecommender
from skillgenie.models.capability import Capability
from skillgenie.models.plan import PlanResult, PlanStep, SkillPlan, StepResult
from skillgenie.storage.skill_store import SkillStore
from skillgenie.utils.logger import Logger


class TaskDecomposer:
    """
    Splits a composite task into ordered sub-tasks.
    """

    # Chain separators trigger a split whenever they appear.
    PRIMARY = (" then ", " afterwards ", " next ")

    # Separators that split only when both fragments are substantial.
    SECONDARY = (" and ", "\n", "; ", ", ", ". ")

    def split(self, task: str) -> list[str]:
        """
        Decompose ``task`` into ordered sub-tasks.
        """

        fragments = [task.strip()]

        for separator in self.PRIMARY:
            fragments = self._split_all(fragments, separator)

        for separator in self.SECONDARY:
            fragments = self._split_selective(fragments, separator)

        cleaned: list[str] = []

        for fragment in fragments:
            fragment = re.sub(r"\s+", " ", fragment).strip(" .,;:-")
            if fragment and fragment.lower() not in {
                cleaned_fragment.lower() for cleaned_fragment in cleaned
            }:
                cleaned.append(fragment)

        return cleaned

    def _split_all(
        self,
        fragments: list[str],
        separator: str,
    ) -> list[str]:
        pieces: list[str] = []

        for fragment in fragments:
            pieces.extend(
                piece for piece in fragment.split(separator) if piece.strip()
            )

        return pieces

    def _split_selective(
        self,
        fragments: list[str],
        separator: str,
    ) -> list[str]:
        pieces: list[str] = []

        for fragment in fragments:
            parts = fragment.split(separator)
            if len(parts) > 1 and self._substantial(
                parts[0]
            ) and self._substantial(parts[1]):
                pieces.extend(
                    [part for part in parts if part.strip()]
                )
                continue

            pieces.append(fragment)

        return pieces

    @staticmethod
    def _substantial(fragment: str) -> bool:
        return len(fragment.split()) >= 3


class SimulatedRunner:
    """
    Deterministic synthetic task runner used when no real agent is linked.

    Outcome is derived from token overlap between the sub-task and the skill's
    search profile, so tests are repeatable without external services.
    """

    def __init__(self, store: SkillStore | None = None):
        self._store = store

    def __call__(
        self,
        skill: Capability | None,
        task: str,
    ) -> dict[str, Any]:
        return self.run(skill, task)

    def run(
        self,
        skill: Capability | None,
        task: str,
    ) -> dict[str, Any]:
        """
        Run a task against a skill and return a synthetic outcome.
        """

        if skill is None:
            return {
                "success": False,
                "latency_ms": 0.0,
                "output": {"reason": "no skill matched"},
            }

        query_tokens = set(task.lower().split())
        stored = set(
            str(
                (skill.metadata or {}).get("search_profile", {}).get("tokens", "")
            ).lower().split()
        )

        overlap = (
            len(query_tokens & stored) / len(query_tokens)
            if query_tokens
            else 0.0
        )

        success = overlap >= 0.5
        latency_ms = 80.0 + (1.0 - overlap) * 320.0

        return {
            "success": success,
            "latency_ms": round(latency_ms, 3),
            "output": {
                "task": task,
                "skill": skill.name,
                "overlap": round(overlap, 3),
            },
        }


class SkillComposer:
    """
    Chains atomic skills into executable plans for composite tasks.
    """

    def __init__(
        self,
        config: Config,
        store: SkillStore,
        recommender: SkillRecommender,
        runner: Callable[[Capability | None, str], dict[str, Any]] | None = None,
    ):
        self._config = config
        self._store = store
        self._recommender = recommender
        self._runner = runner or SimulatedRunner(store)
        self._logger = Logger(config).log

    def compose(
        self,
        task: str,
        top_k: int = 3,
        status: str | None = None,
    ) -> SkillPlan:
        """
        Build an executable plan for a composite task.
        """

        sub_tasks = TaskDecomposer().split(task)

        steps: list[PlanStep] = []

        for index, sub_task in enumerate(sub_tasks, start=1):
            step = PlanStep(order=index, task=sub_task)

            try:
                recommendations = self._recommender.recommend(
                    sub_task,
                    top_k=1,
                    status=status,
                )
            except Exception:
                recommendations = []

            if recommendations:
                best = recommendations[0]
                step.skill_id = best.capability_id
                step.skill_name = str(
                    (best.metadata or {}).get("skill_name", "")
                )
                step.likeness = best.similarity_score or 0.0
                step.matched = True

            steps.append(step)

        plan = SkillPlan(
            task=task,
            steps=steps,
            status="READY" if steps and all(s.matched for s in steps) else "PARTIAL",
        )

        self._logger.info(
            f"Composed plan '{plan.id}' with "
            f"{sum(1 for s in steps if s.matched)}/{len(steps)} matched steps."
        )

        return plan

    def execute(
        self,
        plan: SkillPlan,
        runner: Callable[[Capability | None, str], dict[str, Any]] | None = None,
    ) -> PlanResult:
        """
        Execute a plan through the task runner.
        """

        active_runner = runner or self._runner

        results: list[StepResult] = []

        for step in plan.steps:
            skill = None
            if step.matched and step.skill_id is not None:
                skill = self._store.get(step.skill_id)

            outcome = active_runner(skill, step.task)

            results.append(
                StepResult(
                    order=step.order,
                    task=step.task,
                    skill_id=step.skill_id,
                    skill_name=step.skill_name,
                    success=bool(outcome.get("success", False)),
                    latency_ms=float(outcome.get("latency_ms", 0.0)),
                    output=outcome.get("output", {}),
                )
            )

        return PlanResult(
            plan_id=plan.id,
            task=plan.task,
            steps=results,
            success=all(result.success for result in results),
            total_latency_ms=round(
                sum(result.latency_ms for result in results), 3
            ),
        )

    def learn(
        self,
        plan_result: PlanResult,
        task: str | None = None,
    ) -> Capability | None:
        """
        Learn a composite skill from a fully successful plan execution.
        """

        if not plan_result.success:
            return None

        composite_task = task or plan_result.task

        steps = [
            result
            for result in plan_result.steps
            if result.skill_id is not None and result.success
        ]

        if not steps:
            return None

        child_ids = [str(step.skill_id) for step in steps]

        workflow = {
            "name": composite_task,
            "framework": "composite",
            "steps": [
                {
                    "order": step.order,
                    "name": step.skill_name or step.task,
                    "skill_id": str(step.skill_id),
                    "task": step.task,
                }
                for step in steps
            ],
            "metadata": {
                "composite": True,
                "plan_id": str(plan_result.plan_id),
            },
        }

        metadata = {
            "composite": True,
            "plan_id": str(plan_result.plan_id),
            "children": child_ids,
            "plan_steps": [
                {
                    "skill_id": str(step.skill_id),
                    "skill_name": step.skill_name,
                    "task": step.task,
                }
                for step in steps
            ],
            "search_profile": {
                "tokens": f"{self._title(composite_task)} {composite_task}",
            },
        }

        categories = [
            step.skill_name
            for step in steps
        ]
        category = self._infer_category(steps) or "composite"

        capability = Capability(
            name=self._title(composite_task),
            description=composite_task,
            category=category,
            status=SkillStatus.DRAFT,
            quality_score=0.0,
            confidence_score=0.0,
            success_rate=0.0,
            workflow=workflow,
            metadata=metadata,
            created_from=[str(plan_result.plan_id), *child_ids],
            relationship_graph={
                "children": child_ids,
            },
        )

        self._store.create(capability)

        self._logger.info(
            f"Learned composite skill '{capability.name}' from plan "
            f"'{plan_result.plan_id}'."
        )

        return capability

    def _infer_category(self, steps: list[StepResult]) -> str:
        from collections import Counter

        categories: Counter[str] = Counter()

        for step in steps:
            skill = self._store.get(step.skill_id) if step.skill_id else None
            if skill is not None:
                categories[skill.category] += 1

        if not categories:
            return "composite"

        return categories.most_common(1)[0][0]

    @staticmethod
    def _title(task: str) -> str:
        words = task.strip().split()

        if not words:
            return "Composite Skill"

        title_words = [word.capitalize() for word in words[:6]]

        trailing_stopwords = {
            "The",
            "A",
            "An",
            "And",
            "To",
            "Of",
            "In",
            "On",
            "Then",
            "With",
        }

        while title_words and title_words[-1] in trailing_stopwords:
            title_words.pop()

        rendered = " ".join(title_words).rstrip(" ,.")

        return rendered or "Composite Skill"