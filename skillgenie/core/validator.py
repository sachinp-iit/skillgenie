# ============================================================================
# Project      : SkillGenie
# File         : validator.py
# Description  : Validation harness that audits a learned skill for structural
#                completeness, best practices and production readiness.  Used
#                before publishing and as part of the autonomous remediation
#                loop.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any

from skillgenie.config import Config
from skillgenie.utils.logger import Logger


class SkillValidator:
    """
    Runs a battery of checks against a Capability and produces a readiness
    report with a single verdict.
    """

    def __init__(self, config: Config):
        self._config = config
        self._logger = Logger(config).log

    def validate(self, skill: Any) -> dict[str, Any]:
        """
        Validate a skill and return the readiness report.
        """

        checks: list[dict[str, Any]] = []

        self._metadata_checks(skill, checks)
        self._workflow_checks(skill, checks)
        self._runtime_checks(skill, checks)

        score = self._score(checks)
        has_failure = any(check["status"] == "FAIL" for check in checks)

        if has_failure:
            verdict = "INVALID"
        elif score >= 0.9:
            verdict = "READY"
        else:
            verdict = "NEEDS_WORK"

        return {
            "skill_id": str(getattr(skill, "id", "")),
            "skill_name": getattr(skill, "name", ""),
            "verdict": verdict,
            "readiness_score": round(score, 3),
            "checks": checks,
            "actionable": [
                {
                    "id": check["id"],
                    "fix": check["fix"],
                }
                for check in checks
                if check["status"] != "PASS"
            ],
        }

    def _metadata_checks(
        self,
        skill: Any,
        checks: list[dict[str, Any]],
    ) -> None:
        """
        Structural checks on core fields.
        """

        name = (getattr(skill, "name", "") or "").strip()
        description = (getattr(skill, "description", "") or "").strip()
        category = (getattr(skill, "category", "") or "").strip()

        self._add(
            checks,
            "name_present",
            "A non-empty skill name.",
            "Provide a descriptive skill name.",
            "FAIL" if not name else "PASS",
            detail=name,
        )

        if not description:
            status = "FAIL"
        elif len(description) < 20:
            status = "WARN"
        else:
            status = "PASS"

        self._add(
            checks,
            "description_present",
            "A description of at least 20 characters.",
            "Expand the skill description.",
            status,
            detail=f"{len(description)} chars",
        )

        if not category or category.lower() == "general":
            status = "WARN"
        else:
            status = "PASS"

        self._add(
            checks,
            "category_specific",
            "A specific category (not 'general').",
            "Assign a specific category.",
            status,
            detail=category,
        )

        embedding = getattr(skill, "embedding", None)

        self._add(
            checks,
            "embedding_present",
            "A vector embedding is available.",
            "Recompute the skill embedding.",
            "PASS" if embedding else "WARN",
        )

        metadata = getattr(skill, "metadata", {}) or {}

        for key, label in (
            ("tools", "Tools metadata"),
            ("prompts", "Prompts metadata"),
            ("input_output", "Input/output metadata"),
        ):
            self._add(
                checks,
                f"metadata_{key}",
                f"{label} is declared.",
                f"Add {label} to the skill metadata.",
                "PASS"
                if metadata.get(key)
                else "WARN",
            )

        search_profile = metadata.get("search_profile") or {}
        tokens = (search_profile.get("tokens") or "").strip()

        self._add(
            checks,
            "search_profile",
            "Search profile tokens for lexical retrieval.",
            "Add search_profile.tokens to metadata.",
            "PASS" if tokens else "WARN",
        )

    def _workflow_checks(
        self,
        skill: Any,
        checks: list[dict[str, Any]],
    ) -> None:
        """
        Checks on workflow structure and tool usage.
        """

        workflow = getattr(skill, "workflow", {}) or {}
        framework = (workflow.get("framework") or "").strip()
        steps = workflow.get("steps") or []

        if not steps:
            self._add(
                checks,
                "workflow_steps",
                "At least one workflow step.",
                "Define ordered workflow steps.",
                "FAIL",
            )
            return

        self._add(
            checks,
            "workflow_steps",
            f"{len(steps)} ordered workflow step(s).",
            None,
            "PASS",
            detail=f"{len(steps)} steps",
        )

        steps_without_name = [
            step for step in steps if not (step.get("name") or "").strip()
        ]

        self._add(
            checks,
            "workflow_step_names",
            "Every step has a name.",
            "Name each workflow step.",
            "WARN" if steps_without_name else "PASS",
            detail=f"{len(steps_without_name)} unnamed",
        )

        if not framework:
            status = "WARN"
        else:
            status = "PASS"

        self._add(
            checks,
            "workflow_framework",
            "Workflow framework is declared.",
            "Set a workflow framework (e.g. custom).",
            status,
            detail=framework,
        )

        metadata = getattr(skill, "metadata", {}) or {}
        declared_tools = {
            (tool.get("name") or "").strip().lower()
            for tool in metadata.get("tools") or []
        }

        unknown = []
        for step in steps:
            tool = (step.get("tool") or "").strip().lower()
            if tool and tool not in declared_tools:
                unknown.append(tool)

        self._add(
            checks,
            "workflow_tools_known",
            "Steps reference declared tools only.",
            "Declare every step tool in metadata.tools.",
            "WARN" if unknown else "PASS",
            detail=", ".join(sorted(unknown)) or "all known",
        )

    def _runtime_checks(
        self,
        skill: Any,
        checks: list[dict[str, Any]],
    ) -> None:
        """
        Checks on real-world evidence and runtime health.
        """

        usage_count = int(getattr(skill, "usage_count", 0) or 0)

        self._add(
            checks,
            "execution_evidence",
            "At least one recorded execution.",
            "Run the skill before publishing.",
            "PASS" if usage_count > 0 else "WARN",
            detail=f"{usage_count} executions",
        )

        success_rate = float(getattr(skill, "success_rate", 0.0) or 0.0)

        if usage_count > 0 and success_rate >= self._config.get_float(
            "learning.min_success_rate", 0.90
        ):
            status = "PASS"
        elif usage_count > 0:
            status = "WARN"
        else:
            status = "INFO"

        self._add(
            checks,
            "success_rate",
            "Success rate meets the learning threshold.",
            "Inspect failures before publishing.",
            status,
            detail=f"{success_rate:.0%}" if usage_count else "no outcomes yet",
        )

        latency = float(getattr(skill, "avg_latency_ms", 0.0) or 0.0)

        if latency <= 0:
            status = "INFO"
        elif latency <= 2000:
            status = "PASS"
        else:
            status = "WARN"

        self._add(
            checks,
            "latency_budget",
            "Average latency within 2s budget.",
            "Profile and optimise slow steps.",
            status,
            detail=f"{latency:.0f}ms",
        )

    def _add(
        self,
        checks: list[dict[str, Any]],
        check_id: str,
        label: str,
        fix: str | None,
        status: str,
        detail: str = "",
    ) -> None:
        """
        Append a check entry.
        """

        checks.append(
            {
                "id": check_id,
                "label": label,
                "status": status,
                "detail": detail,
                "fix": fix or "",
            }
        )

    @staticmethod
    def _score(checks: list[dict[str, Any]]) -> float:
        """
        Weighted readiness score: PASS 1.0, WARN 0.5, INFO excluded, FAIL 0.
        """

        weighted = [check for check in checks if check["status"] != "INFO"]

        if not weighted:
            return 0.0

        points = sum(
            {
                "PASS": 1.0,
                "WARN": 0.5,
                "FAIL": 0.0,
                "INFO": 0.0,
            }[check["status"]]
            for check in weighted
        )

        return points / len(weighted)