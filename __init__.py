# ============================================================================
# Project      : SkillGenie
# File         : __init__.py
# Description  : Public package exports.
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from importlib.metadata import version

# Public version
try:
    __version__ = version("skillgenie")
except Exception:
    __version__ = "0.1.0"

# Public API (will be implemented later)
from skillgenie.core.engine import SkillGenie

# Public exports
__all__ = [
    "SkillGenie",
    "__version__",
]