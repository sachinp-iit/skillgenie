# ============================================================================
# Project      : SkillGenie
# File         : lifecycle.py
# Description  : Manages the lifecycle of learned skills.
#
#                Responsible for transitioning skills between lifecycle
#                states while enforcing business rules.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from skillgenie.config import Config
from skillgenie.constants import SkillStatus
from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.audit_repository import AuditRepository
from skillgenie.database.repositories.capability_repository import (
    CapabilityRepository,
)
from skillgenie.exceptions import (
    CapabilityNotFoundError,
    LifecycleError,
)
from skillgenie.utils.logger import Logger

# Valid status transitions enforced by the lifecycle engine.
_TRANSITIONS: dict[SkillStatus, set[SkillStatus]] = {
    SkillStatus.DRAFT: {
        SkillStatus.CANDIDATE,
        SkillStatus.APPROVED,
    },
    SkillStatus.CANDIDATE: {
        SkillStatus.APPROVED,
        SkillStatus.DRAFT,
    },
    SkillStatus.APPROVED: {
        SkillStatus.PUBLISHED,
        SkillStatus.DRAFT,
        SkillStatus.DEPRECATED,
    },
    SkillStatus.PUBLISHED: {
        SkillStatus.DEPRECATED,
        SkillStatus.APPROVED,
    },
    SkillStatus.DEPRECATED: {
        SkillStatus.ARCHIVED,
        SkillStatus.PUBLISHED,
        SkillStatus.DRAFT,
    },
    SkillStatus.ARCHIVED: {
        SkillStatus.DRAFT,
        SkillStatus.PUBLISHED,
    },
}


class SkillLifecycle:
    """
    Manages the lifecycle of skills.
    """

    def __init__(
        self,
        config: Config,
        database: DatabaseManager,
        skill_repository: CapabilityRepository | None = None,
        audit_repository: AuditRepository | None = None,
    ) -> None:
        """
        Initialize Skill Lifecycle.

        Args:
            config: SkillGenie configuration.
            database: Database manager.
            skill_repository: Optional capability repository override.
            audit_repository: Optional audit repository override.
        """

        self._config = config
        self._database = database

        self._logger = Logger(config).log

        self._skill_repository = (
            skill_repository or CapabilityRepository(database)
        )

        self._audit_repository = (
            audit_repository or AuditRepository(database)
        )

    def draft(self, skill_id: str) -> None:
        """Move a skill to DRAFT state."""

        self._transition(skill_id, SkillStatus.DRAFT)

    def candidate(self, skill_id: str) -> None:
        """Move a skill to CANDIDATE state."""

        self._transition(skill_id, SkillStatus.CANDIDATE)

    def approve(self, skill_id: str) -> None:
        """Move a skill to APPROVED state."""

        self._transition(skill_id, SkillStatus.APPROVED)

    def publish(self, skill_id: str) -> None:
        """Move a skill to PUBLISHED state."""

        self._transition(skill_id, SkillStatus.PUBLISHED)

    def deprecate(self, skill_id: str) -> None:
        """Move a skill to DEPRECATED state."""

        self._transition(skill_id, SkillStatus.DEPRECATED)

    def archive(self, skill_id: str) -> None:
        """Move a skill to ARCHIVED state."""

        self._transition(skill_id, SkillStatus.ARCHIVED)

    def restore(self, skill_id: str) -> None:
        """Restore an archived skill back to DRAFT."""

        self._transition(skill_id, SkillStatus.DRAFT)

    def reopen_for_review(self, skill_id: str) -> None:
        """
        Move a skill back to CANDIDATE for re-review, regardless of its
        current lifecycle state. Invalid direct transitions are routed
        through intermediate states.
        """

        if not skill_id or not skill_id.strip():
            raise ValueError("skill_id cannot be empty.")

        skill = self._load_skill(skill_id)

        raw_status = skill.get("status") or SkillStatus.DRAFT.value

        try:
            current_status = SkillStatus(raw_status)
        except ValueError:
            raise LifecycleError(
                f"Skill '{skill_id}' has an unknown status: "
                f"'{raw_status}'."
            ) from None

        if current_status == SkillStatus.CANDIDATE:
            return

        path: list[SkillStatus] = []

        if current_status == SkillStatus.PUBLISHED:
            path = [
                SkillStatus.DEPRECATED,
                SkillStatus.DRAFT,
                SkillStatus.CANDIDATE,
            ]
        elif current_status in {
            SkillStatus.APPROVED,
            SkillStatus.DEPRECATED,
            SkillStatus.ARCHIVED,
        }:
            path = [
                SkillStatus.DRAFT,
                SkillStatus.CANDIDATE,
            ]
        elif current_status == SkillStatus.DRAFT:
            path = [SkillStatus.CANDIDATE]

        for target in path:
            self._transition(skill_id, target)

    def reject(self, skill_id: str, reason: str) -> None:
        """
        Reject a candidate skill and move it back to DRAFT with a reason.
        """

        skill = self._load_skill(skill_id)

        self._transition(skill_id, SkillStatus.DRAFT)

        self._skill_repository.update(
            capability_id=skill_id,
            metadata={
                **(skill.get("metadata") or {}),
                "rejection_reason": reason,
            },
        )

        self._audit(
            capability_id=UUID(skill_id),
            action="REJECT",
            remarks=reason,
        )

    def can_transition(
        self,
        current: SkillStatus,
        target: SkillStatus,
    ) -> bool:
        """
        Check whether a transition is allowed.
        """

        return target in _TRANSITIONS.get(current, set())

    def transition(
        self,
        skill_id: str,
        status: SkillStatus,
    ) -> None:
        """
        Perform a validated transition.
        """

        self._transition(skill_id, status)

    def transition_links(
        self,
        current: SkillStatus,
    ) -> list[str]:
        """
        List allowed target states from a given state.
        """

        return sorted(
            status.value
            for status in _TRANSITIONS.get(current, set())
        )

    def _transition(
        self,
        skill_id: str,
        status: SkillStatus,
    ) -> None:
        """
        Transition a skill to the given lifecycle state.
        """

        if not skill_id or not skill_id.strip():
            raise ValueError("skill_id cannot be empty.")

        skill = self._load_skill(skill_id)

        raw_status = skill.get("status") or SkillStatus.DRAFT.value

        try:
            current_status = SkillStatus(raw_status)
        except ValueError:
            raise LifecycleError(
                f"Skill '{skill_id}' has an unknown status: "
                f"'{raw_status}'."
            ) from None

        if not self.can_transition(current_status, status):
            raise LifecycleError(
                f"Invalid lifecycle transition: "
                f"'{current_status.value}' -> '{status.value}' "
                f"for skill '{skill_id}'."
            )

        self._logger.info(
            "Moving skill '%s' from '%s' to '%s'.",
            skill_id,
            current_status.value,
            status.value,
        )

        self._skill_repository.update(
            capability_id=skill_id,
            status=status.value,
            updated_at=datetime.utcnow(),
        )

        self._audit(
            capability_id=UUID(skill_id),
            action="STATUS_CHANGED",
            remarks=(
                f"{current_status.value} -> {status.value}"
            ),
            payload={
                "from": current_status.value,
                "to": status.value,
            },
        )

    def _load_skill(self, skill_id: str) -> dict[str, Any]:
        """
        Load a skill row from the repository.
        """

        try:
            capability_id = UUID(str(skill_id))
        except ValueError:
            raise ValueError(
                f"Invalid skill id: {skill_id}"
            ) from None

        skill = self._skill_repository.get_by_id(capability_id)

        if skill is None:
            raise CapabilityNotFoundError(
                f"Skill '{skill_id}' does not exist."
            )

        return dict(skill)

    def _audit(
        self,
        capability_id: UUID,
        action: str,
        remarks: str = "",
        payload: dict[str, Any] | None = None,
    ) -> None:
        """
        Write an audit entry.
        """

        from uuid import uuid4

        self._audit_repository.create(
            audit_id=uuid4(),
            capability_id=capability_id,
            action=action,
            performed_by="lifecycle",
            remarks=remarks,
            payload=payload or {},
        )