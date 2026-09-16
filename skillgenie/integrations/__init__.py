# ============================================================================
# Project      : SkillGenie
# File         : __init__.py
# Description  : Framework integration hooks that automatically record
#                execution traces while agents run.
# ============================================================================

__all__ = [
    "record_trace",
    "LangGraphRecorder",
    "CrewAIRecorder",
    "CustomRecorder",
]

from skillgenie.integrations.base import record_trace
from skillgenie.integrations.crewai import CrewAIRecorder
from skillgenie.integrations.langgraph import LangGraphRecorder
from skillgenie.integrations.custom import CustomRecorder