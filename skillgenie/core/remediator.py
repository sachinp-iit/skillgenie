# ============================================================================
# Project      : SkillGenie
# File         : remediator.py
# Description  : Autonomous drift remediation.  When a skill starts failing,
#                drifts from its historical baseline or fails validation, the
#                remediator decides a safe remediation plan and applies the
#                low-risk reversible actions automatically.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from skillgenie.config import Config
from skillgenie.utils.logger import Logger


class SkillRemediator:
    """
    Assess skill health and apply remediation actions.
    """

    def __init__(
        self,
        config: Config,
        store: Any,
        feedback: Any,
        validator: Any,
        lifecycle: Any = None,
        audit_repository: Any = None,
    ):
        self._config = config
        self._store = store
        self._feedback = feedback
        self._validator = validator
        self._lifecycle = lifecycle
        self._audit_repository = audit_repository
        self._logger = Logger(config).log

    def remediate(
        self,
        skill_id: Any,
        mode: str = "auto",
        force: bool = False,
        actor: str = "system",
    ) -> dict[str, Any]:
        """
        Assess a skill and produce/apply a remediation plan.

        Args:
            skill_id: Skill to assess.
            mode: "auto" applies reversible low-risk actions, "review" only
                reports.
            force: Also apply destructive actions (retrain, deprecate).
            actor: Identity recorded in the audit trail.
        """

        skill = self._store.get(skill_id)

        if skill is None:
            raise ValueError(f"Skill '{skill_id}' does not exist.")

        drift = self._feedback.detect_drift(skill_id)

        validation = self._validator.validate(skill)

        health = self._feedback.health_explanation(skill)
        degraded = health.get("health") in {"POOR", "CRITICAL"}
        invalid = validation["verdict"] == "INVALID"

        if invalid or degraded:
            state = "FAILING"
        elif drift and drift.get("direction") == "DEGRADED":
            state = "AT_RISK"
        else:
            state = "HEALTHY"

        actions = self._build_actions(
            skill,
            state=state,
            drift=drift,
            validation=validation,
        )

        apply_auto = mode == "auto"

        applied: list[str] = []

        for action in actions:
            should_apply = action["risk"] == "low" and apply_auto
            should_apply = should_apply or (action["force_only"] and force)
            action["applied"] = should_apply
            if should_apply:
                applied.append(action["action"])

        self._apply(skill, actions)

        if applied:
            self._audit(skill, applied, state, actor)

        return {
            "skill_id": str(skill.id),
            "skill_name": skill.name,
            "state": state,
            "health": health.get("health"),
            "drift": drift,
            "validation": {
                "verdict": validation["verdict"],
                "readiness_score": validation["readiness_score"],
            },
            "actions": actions,
            "applied": applied,
            "summary": (
                f"{len(applied)} action(s) applied."
                if applied
                else "No remediation required."
            ),
        }

    def _build_actions(
        self,
        skill: Any,
        *,
        state: str,
        drift: dict[str, Any] | None,
        validation: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Compose the ordered remediation plan for the current state.
        """

        metadata = dict(getattr(skill, "metadata", {}) or {})
        usage = int(getattr(skill, "usage_count", 0) or 0)

        actions: list[dict[str, Any]] = []

        if state != "HEALTHY":
            actions.append(
                self._action(
                    "flag_review",
                    "Mark the skill for human review.",
                    risk="low",
                    reversible=True,
                    force_only=False,
                )
            )

        if state != "HEALTHY":
            actions.append(
                self._action(
                    "suppress_recommendations",
                    "Temporarily exclude the skill from "
                    "recommendations until it recovers.",
                    risk="low",
                    reversible=True,
                    force_only=False,
                )
            )

        if drift and drift.get("direction") == "DEGRADED" and usage > 0:
            actions.append(
                self._action(
                    "retrain",
                    "Relearn from recent traces to recover the "
                    "performance baseline.",
                    risk="medium",
                    reversible=True,
                    force_only=True,
                )
            )

        if state == "FAILING":
            actions.append(
                self._action(
                    "deprecate",
                    "Deprecate the skill; it no longer meets "
                    "readiness or health requirements.",
                    risk="high",
                    reversible=False,
                    force_only=True,
                )
            )

        if metadata.get("suppress"):
            actions.append(
                self._already(
                    "unsuppress",
                    "Skill is currently suppressed; lift the "
                    "flag once recovery is confirmed.",
                )
            )

        if metadata.get("review_required"):
            actions.append(
                self._already(
                    "review_pending",
                    "A human review request is already open.",
                )
            )

        return actions

    def _apply(
        self,
        skill: Any,
        actions: list[dict[str, Any]],
    ) -> None:
        """
        Persist the applied actions as metadata flags.
        """

        applied = {
            action["action"] for action in actions if action["applied"]
        }

        if not applied:
            return

        metadata = dict(getattr(skill, "metadata", {}) or {})

        if "flag_review" in applied:
            metadata["review_required"] = True

        if "suppress_recommendations" in applied:
            metadata["suppress"] = True
            metadata["suppressed_at"] = datetime.utcnow().isoformat()

        self._store.update(
            skill.id,
            metadata=metadata,
        )

    def _audit(
        self,
        skill: Any,
        applied: list[str],
        state: str,
        actor: str,
    ) -> None:
        """
        Record the remediation in the audit trail.
        """

        if self._audit_repository is None:
            return

        try:
            from uuid import uuid4

            self._audit_repository.create(
                audit_id=uuid4(),
                capability_id=skill.id,
                action="REMEDIATE",
                performed_by=actor,
                remarks=f"state={state} applied={','.join(applied)}",
                payload={
                    "applied": applied,
                    "state": state,
                    "expires_hours": (
                        self._config.get_int(
                            "feedback.drift_window_hours",
                            168,
                        )
                    ),
                },
            )
        except Exception as exc:
            self._logger.warning(
                f"Remediation audit for {skill.id} failed: {exc}"
            )

    @staticmethod
    def _action(
        action_id: str,
        description: str,
        *,
        risk: str,
        reversible: bool,
        force_only: bool,
    ) -> dict[str, Any]:
        return {
            "action": action_id,
            "description": description,
            "risk": risk,
            "reversible": reversible,
            "force_only": force_only,
            "applied": False,
        }

    @staticmethod
    def _already(
        action_id: str,
        description: str,
    ) -> dict[str, Any]:
        return {
            "action": action_id,
            "description": description,
            "risk": "none",
            "reversible": True,
            "force_only": False,
            "applied": False,
        }