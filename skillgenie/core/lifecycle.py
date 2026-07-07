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

from skillgenie.config import Config
from skillgenie.constants import SkillStatus
from skillgenie.database.manager import DatabaseManager
from skillgenie.utils.logger import Logger


class SkillLifecycle:
    """
    Manages the lifecycle of skills.
    """

    def __init__(
        self,
        config: Config,
        database: DatabaseManager,
    ) -> None:
        """
        Initialize Skill Lifecycle.

        Args:
            config: SkillGenie configuration.
            database: Database manager.
        """

        self._config = config
        self._database = database

        self._logger = Logger(config).log

    def draft(self, skill_id: str) -> None:
        """
        Move a skill to DRAFT state.
        """

        self._transition(
            skill_id,
            SkillStatus.DRAFT,
        )

    def approve(self, skill_id: str) -> None:
        """
        Move a skill to APPROVED state.
        """

        self._transition(
            skill_id,
            SkillStatus.APPROVED,
        )

    def publish(self, skill_id: str) -> None:
        """
        Move a skill to PUBLISHED state.
        """

        self._transition(
            skill_id,
            SkillStatus.PUBLISHED,
        )

    def deprecate(self, skill_id: str) -> None:
        """
        Move a skill to DEPRECATED state.
        """

        self._transition(
            skill_id,
            SkillStatus.DEPRECATED,
        )

    def archive(self, skill_id: str) -> None:
        """
        Move a skill to ARCHIVED state.
        """

        self._transition(
            skill_id,
            SkillStatus.ARCHIVED,
        )

    def restore(self, skill_id: str) -> None:
        """
        Restore an archived skill.
        """

        self._logger.info(
            "Restoring skill '%s'.",
            skill_id,
        )

        # Repository update will be implemented here.

    def _transition(
        self,
        skill_id: str,
        status: SkillStatus,
    ) -> None:
        """
        Transition a skill to the given lifecycle state.

        Args:
            skill_id: Skill identifier.
            status: Target lifecycle status.
        """

        if not skill_id.strip():
            raise ValueError(
                "skill_id cannot be empty."
            )

        self._logger.info(
            "Moving skill '%s' to '%s'.",
            skill_id,
            status.value,
        )

        # Repository update will be implemented here.