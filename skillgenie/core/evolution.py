# ============================================================================
# Project      : SkillGenie
# File         : evolution.py
# Description  : Skill evolution engine. Handles automatic promotion,
#                degradation, versioning and retirement of skills.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from skillgenie.config import Config
from skillgenie.constants import SkillHealth, SkillStatus
from skillgenie.core.health import SkillHealthEngine
from skillgenie.core.lifecycle import SkillLifecycle
from skillgenie.database.manager import DatabaseManager
from skillgenie.database.repositories.audit_repository import AuditRepository
from skillgenie.database.repositories.capability_repository import (
    CapabilityRepository,
)
from skillgenie.models.capability import Capability
from skillgenie.storage.skill_store import SkillStore
from skillgenie.utils.logger import Logger


def bump_version(version: str, level: str = "patch") -> str:
    """
    Increment a semantic version string.

    Args:
        version: Version string such as "1.2.3".
        level: One of "major", "minor", "patch".

    Returns:
        Bumped version string.
    """

    parts = version.split(".")

    try:
        numbers = [int(part) for part in parts[:3]]
    except ValueError:
        return version

    while len(numbers) < 3:
        numbers.append(0)

    if level == "major":
        numbers[0] += 1
        numbers[1] = 0
        numbers[2] = 0
    elif level == "minor":
        numbers[1] += 1
        numbers[2] = 0
    else:
        numbers[2] += 1

    return ".".join(str(number) for number in numbers)


class SkillEvolutionEngine:
    """
    Manages automatic skill evolution.
    """

    def __init__(
        self,
        config: Config,
        database: DatabaseManager,
        store: SkillStore | None = None,
        lifecycle: SkillLifecycle | None = None,
        health_engine: SkillHealthEngine | None = None,
        skill_repository: CapabilityRepository | None = None,
        audit_repository: AuditRepository | None = None,
    ):
        """
        Initialize evolution engine.

        Args:
            config: SkillGenie configuration.
            database: Database manager.
            store: Optional skill store.
            lifecycle: Optional lifecycle manager.
            health_engine: Optional health engine.
            skill_repository: Optional capability repository.
            audit_repository: Optional audit repository.
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

        self._store = store or SkillStore(
            config=config,
            repository=self._skill_repository,
        )

        self._lifecycle = lifecycle or SkillLifecycle(
            config=config,
            database=database,
            skill_repository=self._skill_repository,
            audit_repository=self._audit_repository,
        )

        self._health = health_engine or SkillHealthEngine(config)

    def evolve(
        self,
        skill: Capability,
        changes: dict[str, Any],
        level: str = "minor",
    ) -> Capability:
        """
        Evolve an existing skill with new workflow/metadata while bumping its
        version. The skill is moved back through the lifecycle for review.

        Args:
            skill: Existing skill model.
            changes: Fields to apply (workflow, metadata, embedding...).
            level: Version increment level.

        Returns:
            Updated skill.
        """

        current = self._store.get(skill.id)

        if current is None:
            raise ValueError(f"Skill '{skill.id}' does not exist.")

        applied: dict[str, Any] = {}

        for key in (
            "workflow",
            "metadata",
            "embedding",
            "description",
            "category",
        ):
            if key in changes and changes[key] is not None:
                applied[key] = changes[key]
                setattr(current, key, changes[key])

        current.version = bump_version(current.version, level)

        applied["version"] = current.version

        self._store.update(current.id, **applied)

        self._lifecycle.reopen_for_review(str(current.id))

        self._audit(
            capability_id=current.id,
            action="EVOLVED",
            remarks=f"Applied {len(applied)} field(s).",
            payload=applied,
        )

        return current

    def deprecate_degraded(self) -> list[str]:
        """
        Automatically deprecate published skills whose health has degraded.

        Returns:
            List of deprecated skill ids.
        """

        deprecated: list[str] = []

        for skill in self._store.list(
            status=SkillStatus.PUBLISHED.value
        ):
            if self._health.degraded(skill):
                self._lifecycle.deprecate(str(skill.id))
                deprecated.append(str(skill.id))
                self._logger.warning(
                    f"Deprecated degraded skill '{skill.name}'."
                )

        return deprecated

    def archive_stale(
        self,
        max_idle_days: int = 90,
    ) -> list[str]:
        """
        Archive approved/published skills that have been idle too long.

        Returns:
            List of archived skill ids.
        """

        archived: list[str] = []

        cutoff = datetime.utcnow() - timedelta(days=max_idle_days)

        for status in (SkillStatus.PUBLISHED.value, SkillStatus.APPROVED.value):
            for skill in self._store.list(status=status):
                last_used = skill.last_used_at or skill.created_at

                if last_used and last_used < cutoff:
                    self._lifecycle.deprecate(str(skill.id))
                    self._lifecycle.archive(str(skill.id))
                    archived.append(str(skill.id))

        return archived

    def health_snapshot(self) -> dict[str, Any]:
        """
        Distribution of skill health across the registry.
        """

        snapshot: dict[str, int] = {
            status.value: 0
            for status in SkillHealth
        }

        for skill in self._store.list():
            snapshot[self._health.health(skill).value] += 1

        return snapshot

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
            performed_by="evolution",
            remarks=remarks,
            payload=payload or {},
        )