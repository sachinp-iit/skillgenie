# ============================================================================
# Project      : SkillGenie
# File         : provenance.py
# Description  : Lineage tracking and explainability.  Ties a skill back to
#                the source traces it was learned from, the audit trail that
#                governed it and the outcome evidence that supports it, then
#                explains WHY the skill exists and how trustworthy it is.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any

from skillgenie.config import Config
from skillgenie.utils.logger import Logger


class SkillProvenance:
    """
    Assemble the provenance dossier for a learned capability.
    """

    def __init__(
        self,
        config: Config,
        store: Any,
        audit_repository: Any = None,
        outcome_repository: Any = None,
        trace_repository: Any = None,
    ):
        self._config = config
        self._store = store
        self._audit_repository = audit_repository
        self._outcome_repository = outcome_repository
        self._trace_repository = trace_repository
        self._logger = Logger(config).log

    def provenance(self, skill_id: Any) -> dict[str, Any]:
        """
        Build the full provenance dossier for a skill.
        """

        skill = self._store.get(skill_id)

        if skill is None:
            raise ValueError(f"Skill '{skill_id}' does not exist.")

        sources = self._source_traces(skill)
        audit_events = self._audit_events(skill)
        outcomes = self._outcomes(skill)

        confidence = float(getattr(skill, "confidence_score", 0.0) or 0.0)
        quality = float(getattr(skill, "quality_score", 0.0) or 0.0)

        return {
            "skill_id": str(skill.id),
            "skill_name": skill.name,
            "version": skill.version,
            "status": skill.status.value,
            "health": getattr(skill, "health", "GOOD").value,
            "origin": {
                "created_from": list(
                    getattr(skill, "created_from", []) or []
                ),
                "source_traces": sources,
                "learned_at": (
                    getattr(skill, "created_at", None).isoformat()
                    if getattr(skill, "created_at", None)
                    else None
                ),
            },
            "lineage": {
                "updated_at": (
                    getattr(skill, "updated_at", None).isoformat()
                    if getattr(skill, "updated_at", None)
                    else None
                ),
                "last_used_at": (
                    getattr(skill, "last_used_at", None).isoformat()
                    if getattr(skill, "last_used_at", None)
                    else None
                ),
                "executions": int(
                    getattr(skill, "usage_count", 0) or 0
                ),
                "relearns": sum(
                    1
                    for event in audit_events
                    if event["action"] == "RELEARN"
                ),
                "composite_children": bool(
                    (getattr(skill, "metadata", {}) or {}).get("composite")
                ),
            },
            "attribution": {
                "audit_events": audit_events,
                "governing_events": [
                    event["action"]
                    for event in audit_events
                    if event["action"]
                    in {
                        "APPROVED",
                        "REJECTED",
                        "PUBLISHED",
                        "DEPRECATED",
                        "ARCHIVED",
                        "RELEARN",
                        "DRIFT_DEGRADED",
                        "REMEDIATE",
                    }
                ],
                "outcomes": outcomes,
            },
            "explainability": {
                "confidence": round(confidence, 3),
                "quality": round(quality, 3),
                "confidence_reason": self._confidence_reason(skill),
                "quality_reason": self._quality_reason(skill),
                "narrative": self._narrative(
                    skill,
                    sources=sources,
                    audit_events=audit_events,
                    outcomes=outcomes,
                ),
            },
        }

    def _source_traces(self, skill: Any) -> list[dict[str, Any]]:
        """
        Resolve source trace records for the skill.
        """

        if self._trace_repository is None:
            return []

        sources: list[dict[str, Any]] = []

        for trace_id in getattr(skill, "created_from", []) or []:
            try:
                row = self._trace_repository.get_by_id(str(trace_id))
            except Exception:
                row = None

            if row is None:
                continue

            row = dict(row)

            sources.append(
                {
                    "trace_id": str(row.get("id", trace_id)),
                    "trace_name": row.get("trace_name"),
                    "framework": row.get("agent_framework"),
                    "task_description": row.get("task_description"),
                }
            )

        return sources

    def _audit_events(self, skill: Any) -> list[dict[str, Any]]:
        """
        Audit trail for the skill.
        """

        if self._audit_repository is None:
            return []

        try:
            events = [
                dict(event)
                for event in self._audit_repository.get_by_capability(skill.id)
            ]
        except Exception:
            return []

        events = [dict(event) for event in self._audit_repository.get_by_capability(skill.id)]

        return [
            {
                "action": event.get("action", ""),
                "performed_by": event.get("performed_by", ""),
                "remarks": event.get("remarks", ""),
                "created_at": (
                    event["created_at"].isoformat()
                    if event.get("created_at")
                    else None
                ),
            }
            for event in events
        ][:50]

    def _outcomes(self, skill: Any) -> dict[str, Any]:
        """
        Outcome evidence summary.
        """

        if self._outcome_repository is None:
            return {}

        try:
            counts = self._outcome_repository.count_outcomes(skill.id)
        except Exception:
            return {}

        total = int(counts.get("total") or 0)
        successes = int(counts.get("successes") or 0)

        return {
            "successes": successes,
            "total": total,
            "success_rate": round(successes / total, 3) if total else None,
        }

    @staticmethod
    def _confidence_reason(skill: Any) -> str:
        """
        Why the confidence score is what it is.
        """

        workflow = getattr(skill, "workflow", {}) or {}
        metadata = getattr(skill, "metadata", {}) or {}
        usage = int(getattr(skill, "usage_count", 0) or 0)

        present: list[str] = []

        if workflow.get("steps"):
            present.append("an ordered workflow")
        if metadata.get("tools"):
            present.append("declared tools")
        if metadata.get("prompts"):
            present.append("prompts")
        if metadata.get("input_output"):
            present.append("input/output contracts")
        if usage > 0:
            present.append(f"{usage} recorded executions")

        return (
            "Confidence derives from artifact completeness: "
            + (", ".join(present) or "no artifacts yet")
            + "."
        )

    @staticmethod
    def _quality_reason(skill: Any) -> str:
        """
        Why the quality score is what it is.
        """

        description = (getattr(skill, "description", "") or "").strip()
        category = (getattr(skill, "category", "") or "").strip()
        steps = (getattr(skill, "workflow", {}) or {}).get("steps") or []

        signals: list[str] = []

        signals.append(
            f"{len(description)} character description"
            if description
            else "no description"
        )
        signals.append(
            f"category '{category}'"
            if category
            else "no category"
        )
        signals.append(
            f"{len(steps)} workflow steps"
            if steps
            else "no workflow steps"
        )

        return "Quality weighs documentation depth, category specificity and workflow structure: " + ", ".join(signals) + "."

    def _narrative(
        self,
        skill: Any,
        *,
        sources: list[dict[str, Any]],
        audit_events: list[dict[str, Any]],
        outcomes: dict[str, Any],
    ) -> str:
        """
        Compose a human-readable provenance narrative.
        """

        if sources:
            origin = (
                f"This skill was learned from "
                f"{len(sources)} observed trace(s), e.g. "
                f"'{sources[0].get('trace_name')}'."
            )
        else:
            origin = "This skill has no linked source traces."

        governance = ""

        relevant = [
            event
            for event in audit_events
            if event["action"]
            in {"APPROVED", "PUBLISHED", "DRIFT_DEGRADED", "REMEDIATE"}
        ]

        if relevant:
            governance = (
                f" {len(relevant)} governance event(s) are recorded, "
                "including "
                + ", ".join(
                    event["action"] for event in relevant[:3]
                )
                + "."
            )

        performance = ""

        if outcomes.get("total"):
            rate = outcomes["success_rate"]
            performance = (
                f" Real-world outcomes show a "
                f"{rate:.0%} success rate over "
                f"{outcomes['total']} recorded outcomes."
            )

        return origin + governance + performance