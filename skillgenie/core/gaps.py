# ============================================================================
# Project      : SkillGenie
# File         : gaps.py
# Description  : Registry analysis for coverage gaps, unserved task novelty
#                and redundancy.  Highlights where the skill registry is thin
#                and what new skills would add the most value.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from skillgenie.config import Config
from skillgenie.utils.logger import Logger

_STOPWORDS = {
    "a", "an", "the", "to", "and", "for", "of", "with", "on", "in",
    "from", "into", "then", "step", "steps", "task", "using", "use",
    "how", "do", "this", "that", "their", "your", "you",
}


class SkillGapAnalyzer:
    """
    Identify coverage gaps, novelty opportunities and duplications.
    """

    def __init__(
        self,
        config: Config,
        store: Any,
        trace_repository: Any = None,
    ):
        self._config = config
        self._store = store
        self._trace_repository = trace_repository
        self._logger = Logger(config).log

    def analyze(self) -> dict[str, Any]:
        """
        Run the full registry gap analysis.
        """

        skills = self._store.list()

        category_coverage = self._category_coverage(skills)
        tool_gaps = self._tool_gaps(skills)
        novelty = self._novelty_opportunities(skills)
        redundancy = self._redundancy(skills)

        gaps = [
            category for category, count in category_coverage.items() if count <= 1
        ]

        return {
            "generated_at": datetime.utcnow().isoformat(),
            "total_skills": len(skills),
            "category_coverage": category_coverage,
            "low_coverage_categories": [
                {
                    "category": category,
                    "skills": count,
                }
                for category, count in category_coverage.items()
                if count <= 1
            ],
            "tool_gaps": tool_gaps,
            "novelty_opportunities": novelty,
            "redundancy": redundancy,
            "summary": self._summary(
                total=len(skills),
                gaps=gaps,
                tool_gaps=tool_gaps,
                novelty=novelty,
                redundancy=redundancy,
            ),
        }

    def _category_coverage(
        self,
        skills: list[Any],
    ) -> dict[str, int]:
        """
        Count skills per category (skipping 'general').
        """

        counts: dict[str, int] = {}

        for skill in skills:
            category = (getattr(skill, "category", "") or "").strip()

            if not category or category.lower() == "general":
                continue

            counts[category] = counts.get(category, 0) + 1

        return dict(
            sorted(counts.items(), key=lambda item: item[1], reverse=True)
        )

    def _tool_gaps(self, skills: list[Any]) -> list[str]:
        """
        Tools seen in traces but not covered by any learned skill.
        """

        if self._trace_repository is None:
            return []

        used_tools = set()

        try:
            traces = self._trace_repository.list()
        except Exception:
            return []

        for trace in traces:
            row = dict(trace)
            trace_data = row.get("trace") or {}
            metadata = row.get("metadata") or {}

            for tool in self._extract_tools(trace_data):
                used_tools.add(tool.lower())

            for tool in self._extract_tools(metadata):
                used_tools.add(tool.lower())

        covered_tools: set[str] = set()

        for skill in skills:
            workflow = getattr(skill, "workflow", {}) or {}
            for step in workflow.get("steps") or []:
                tool = (step.get("tool") or "").strip().lower()
                if tool:
                    covered_tools.add(tool)

            metadata = getattr(skill, "metadata", {}) or {}
            for tool in self._extract_tools(metadata):
                covered_tools.add(tool.lower())

        return sorted(used_tools - covered_tools)

    def _novelty_opportunities(
        self,
        skills: list[Any],
    ) -> list[dict[str, Any]]:
        """
        Tasks observed in traces that no existing skill serves well.
        """

        if self._trace_repository is None:
            return []

        threshold = self._config.get_float(
            "similarity.recommendation_threshold",
            0.80,
        )

        tasks: dict[str, dict[str, Any]] = {}

        try:
            traces = self._trace_repository.list()
        except Exception:
            return []

        for trace in traces:
            row = dict(trace)
            task = (
                row.get("task_description")
                or row.get("trace_name")
                or ""
            ).strip()

            if not task:
                continue

            task_key = task.lower()

            entry = tasks.get(task_key)
            if entry is None:
                best = max(
                    (self._token_overlap(task, self._skill_text(skill))
                     for skill in skills),
                    default=0.0,
                )
                tasks[task_key] = {
                    "task": task,
                    "trace_id": row.get("id"),
                    "best_similarity": round(best, 3),
                }

        opportunities = [
            entry
            for entry in tasks.values()
            if entry["best_similarity"] < threshold
        ]

        opportunities.sort(key=lambda item: item["best_similarity"])

        return opportunities

    def _redundancy(self, skills: list[Any]) -> list[dict[str, Any]]:
        """
        Groups of skills whose intent overlaps heavily.
        """

        groups: dict[str, list[Any]] = {}

        for skill in skills:
            key = " ".join(
                sorted(self._tokens(self._skill_text(skill)))
            )
            if key:
                groups.setdefault(key, []).append(skill)

        redundant: list[dict[str, Any]] = []

        for key, members in groups.items():
            if len(members) < 2:
                continue

            members.sort(key=lambda skill: skill.name)

            redundant.append(
                {
                    "intent": key,
                    "skills": [
                        {
                            "id": str(skill.id),
                            "name": skill.name,
                        }
                        for skill in members
                    ],
                    "similarity": round(
                        self._token_overlap(key, key), 3
                    ),
                    "recommendation": (
                        "Consider merging into a single composite skill."
                    ),
                }
            )

        redundant.sort(key=lambda item: len(item["skills"]), reverse=True)

        return redundant

    @staticmethod
    def _extract_tools(payload: Any) -> list[str]:
        """
        Pull tool names from trace/metadata payloads.
        """

        if not isinstance(payload, dict):
            return []

        tools: list[str] = []

        raw_tools = payload.get("tools") or []

        for tool in raw_tools:
            if isinstance(tool, dict):
                name = tool.get("name") or ""
            else:
                name = tool

            if name:
                tools.append(str(name))

        return tools

    @staticmethod
    def _skill_text(skill: Any) -> str:
        """
        Concatenate the searchable text of a skill.
        """

        parts = [
            getattr(skill, "name", ""),
            getattr(skill, "description", "") or "",
        ]

        workflow = getattr(skill, "workflow", {}) or {}
        parts.extend(
            (step.get("name") or "") for step in workflow.get("steps") or []
        )

        metadata = getattr(skill, "metadata", {}) or {}
        search_profile = metadata.get("search_profile") or {}
        parts.append(search_profile.get("tokens") or "")

        return " ".join(parts)

    @classmethod
    def _tokens(cls, text: str) -> set[str]:
        """
        Lower-cased word tokens minus stopwords.
        """

        return {
            word
            for word in re.findall(r"[a-z0-9]+", text.lower())
            if word not in _STOPWORDS and len(word) > 2
        }

    @classmethod
    def _token_overlap(cls, left: str, right: str) -> float:
        """
        Jaccard-style overlap of the significant tokens.
        """

        a = cls._tokens(left)
        b = cls._tokens(right)

        if not a or not b:
            return 0.0

        return len(a & b) / len(a | b)

    @staticmethod
    def _summary(
        *,
        total: int,
        gaps: list[str],
        tool_gaps: list[str],
        novelty: list[dict[str, Any]],
        redundancy: list[dict[str, Any]],
    ) -> str:
        """
        One-line human summary of the findings.
        """

        parts = [f"{total} skill(s) in the registry."]

        if gaps:
            parts.append(f"{len(gaps)} sparse category(ies).")
        if tool_gaps:
            parts.append(f"{len(tool_gaps)} uncovered tool(s) in traces.")
        if novelty:
            parts.append(
                f"{len(novelty)} unserved task(s) worth learning."
            )
        if redundancy:
            parts.append(f"{len(redundancy)} potential duplicate group(s).")

        return " ".join(parts)