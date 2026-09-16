# ============================================================================
# Project      : SkillGenie
# File         : __init__.py
# Description  : Web dashboards (admin + monitor) for SkillGenie.
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

__all__ = ["TEMPLATES_DIR"]

from pathlib import Path

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"