# ============================================================================
# Project      : SkillGenie
# File         : __init__.py
# Description  : REST API package exports.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from skillgenie.api.app import create_app

__all__ = [
    "create_app",
]