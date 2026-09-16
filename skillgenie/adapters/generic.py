# ============================================================================
# Project      : SkillGenie
# File         : generic.py
# Description  : Generic / custom framework adapter.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

from typing import Any

from skillgenie.adapters.base import FrameworkAdapter, register_adapter


@register_adapter
class GenericAdapter(FrameworkAdapter):
    """
    Pass-through adapter for custom or already-normalized traces.
    """

    framework = "custom"

    def normalize(
        self,
        trace: dict[str, Any],
        **_: Any,
    ) -> dict[str, Any]:
        """
        Normalize a custom trace.
        """

        return self._wrap(trace)