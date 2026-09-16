# ============================================================================
# Project      : SkillGenie
# File         : __init__.py
# Description  : Framework adapter package exports.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from skillgenie.adapters.base import (
    FrameworkAdapter,
    get_adapter,
    register_adapter,
    supported_frameworks,
)
from skillgenie.adapters.generic import GenericAdapter

from skillgenie.adapters import frameworks  # noqa: F401  (registers adapters)

__all__ = [
    "FrameworkAdapter",
    "GenericAdapter",
    "get_adapter",
    "register_adapter",
    "supported_frameworks",
]