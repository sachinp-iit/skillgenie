# ============================================================================
# Project      : SkillGenie
# File         : dependencies.py
# Description  : Provides the SkillGenie engine instance to API routers.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from skillgenie.core.engine import SkillGenie

_ENGINE: SkillGenie | None = None


def set_engine(engine: SkillGenie) -> None:
    """
    Register the active engine instance.
    """

    global _ENGINE

    _ENGINE = engine


def get_engine() -> SkillGenie:
    """
    Return the active engine, building a default one when absent.
    """

    global _ENGINE

    if _ENGINE is None:
        _ENGINE = SkillGenie()

    return _ENGINE


def clear_engine() -> None:
    """
    Drop the active engine (used by tests).
    """

    global _ENGINE

    _ENGINE = None