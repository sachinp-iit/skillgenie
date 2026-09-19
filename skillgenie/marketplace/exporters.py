# ============================================================================
# Project      : SkillGenie
# File         : exporters.py
# Description  : Multi-format skill exporters — Claude Skills (markdown),
#                OpenAI GPT function definitions, a portable SkillGenie
#                bundle and the MCP tool definition.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

FORMATS = {"claude", "openai", "bundle", "mcp"}


def _slugify(name: str) -> str:
    """
    Convert a skill name into a safe file/identifier slug.
    """

    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")

    return slug or "skill"


def _workflow_steps(skill: Any) -> list[dict[str, Any]]:
    workflow = getattr(skill, "workflow", {}) or {}
    steps = workflow.get("steps") or []

    return [
        {
            "order": step.get("order", index + 1),
            "name": step.get("name") or f"step-{index + 1}",
            "tool": step.get("tool") or "",
            "instructions": (step.get("prompt") or step.get("output") or {}),
        }
        for index, step in enumerate(steps)
    ]


def export_claude(skill: Any) -> str:
    """
    Anthropic Claude Skill document (frontmatter + ordered steps).
    """

    steps = _workflow_steps(skill)

    lines = [
        f"name: {_slugify(skill.name)}",
        f"description: {getattr(skill, 'description', '') or ''}".replace(
            "\n", " "
        ),
    ]

    if getattr(skill, "category", None):
        lines.append(f"category: {(skill.category or '').lower()}")

    lines.append(f"version: {getattr(skill, 'version', '1.0.0')}")

    body: list[str] = []

    if steps:
        body.append("## Steps")
        for step in steps:
            body.append(f"{step['order']}. {step['name']}")

            if step["tool"]:
                body.append(f"   Tool: {step['tool']}")

            instructions = step["instructions"]
            if isinstance(instructions, dict) and instructions:
                body.append(
                    "   Instructions: "
                    + json_compact(instructions)
                )

    return "---\n" + "\n".join(lines) + "\n---\n\n" + "\n".join(body) + "\n"


def export_openai(skill: Any) -> dict[str, Any]:
    """
    OpenAI / Anyscale function tool definition.
    """

    metadata = getattr(skill, "metadata", {}) or {}
    input_output = metadata.get("input_output") or {}

    parameters = input_output.get("input") or {
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "Task description.",
            }
        },
    }

    if (
        isinstance(parameters, dict)
        and "type" not in parameters
        and "properties" not in parameters
    ):
        properties: dict[str, Any] = {}

        for key, value in parameters.items():
            if isinstance(value, dict):
                properties[key] = value
            else:
                properties[key] = {
                    "type": "string",
                    "description": str(value),
                }

        parameters = {
            "type": "object",
            "properties": properties,
        }

    steps = _workflow_steps(skill)

    return {
        "type": "function",
        "function": {
            "name": _slugify(skill.name),
            "description": (
                getattr(skill, "description", "")
                or "Executes a learned SkillGenie capability."
            ),
            "parameters": parameters,
            "strict": False,
            "steps": steps,
            "skillgenie": {
                "skill_id": str(skill.id),
                "version": skill.version,
                "workflow": skill.workflow,
            },
        },
    }


def export_bundle(skill: Any) -> dict[str, Any]:
    """
    Portable SkillGenie bundle: manifest plus reusable artifacts.
    """

    metadata = getattr(skill, "metadata", {}) or {}

    bundle = {
        "manifest": {
            "format": "skillgenie-bundle",
            "schema_version": "1.0",
            "id": str(skill.id),
            "name": skill.name,
            "description": getattr(skill, "description", "") or "",
            "category": getattr(skill, "category", "") or "",
            "version": skill.version,
            "status": skill.status.value,
            "health": skill.health.value,
            "confidence": round(float(skill.confidence_score or 0.0), 3),
            "quality": round(float(skill.quality_score or 0.0), 3),
            "exported_at": datetime.utcnow().isoformat(),
        },
        "artifacts": {
            "workflow": skill.workflow,
            "metadata": metadata,
            "embedding": list(getattr(skill, "embedding", []) or []),
        },
    }

    return bundle


def export_mcp(skill: Any) -> dict[str, Any]:
    """
    MCP tool definition matching the SkillGenie MCP server shape.
    """

    metadata = getattr(skill, "metadata", {}) or {}

    return {
        "name": _slugify(skill.name),
        "description": skill.description,
        "inputSchema": metadata.get("input_output", {}).get(
            "input", {"type": "object"}
        ),
        "skillgenie": {
            "skill_id": str(skill.id),
            "version": skill.version,
            "status": skill.status.value,
            "confidence": skill.confidence_score,
            "quality": skill.quality_score,
            "health": skill.health.value,
            "workflow": skill.workflow,
            "tools": metadata.get("tools", []),
        },
    }


def export_skill(skill: Any, fmt: str) -> Any:
    """
    Export a skill in the requested format.

    Returns a string for ``claude``, a dict otherwise.
    """

    if fmt == "claude":
        return export_claude(skill)

    if fmt == "openai":
        return export_openai(skill)

    if fmt == "bundle":
        return export_bundle(skill)

    if fmt == "mcp":
        return export_mcp(skill)

    raise ValueError(
        f"Unknown export format '{fmt}'. "
        f"Supported: {', '.join(sorted(FORMATS))}."
    )


def json_compact(value: Any) -> str:
    """
    Compact JSON serialization for embedding instructions.
    """

    import json

    return json.dumps(value, default=str, separators=(",", ":"))