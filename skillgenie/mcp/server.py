# ============================================================================
# Project      : SkillGenie
# File         : server.py
# Description  : MCP (Model Context Protocol) server that exposes SkillGenie
#                capabilities as discoverable tools.
#
#                Run standalone:  python -m skillgenie.mcp
#                Or integrate:    SkillGenieMCPServer(engine).start()
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from skillgenie.config import Config
from skillgenie.core.engine import SkillGenie
from skillgenie.utils.logger import Logger


class SkillGenieMCPServer:
    """
    MCP-compatible server exposing SkillGenie skills as tools.

    Exposes:
        - skillgenie_search   : search the skill registry by query
        - skillgenie_list     : list skills with optional filters
        - skillgenie_recommend: recommend skills for a task
        - skillgenie_learn    : learn a skill from a trace
        - skillgenie_export   : export a skill as a standalone tool definition
        - skillgenie_health   : get skill health with explainable breakdown
    """

    PROTOCOL_VERSION = "2025-03-26"
    SERVER_NAME = "skillgenie"
    SERVER_VERSION = "0.1.0"

    def __init__(self, engine: SkillGenie | None = None, config_file: str | None = None):
        self._engine = engine or SkillGenie(
            config_file=config_file or "config/config.json"
        )
        self._logger = Logger(self._engine.config).log

    @property
    def tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "skillgenie_search",
                "description": "Search the SkillGenie registry for skills matching a task query.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Task description to search for"},
                        "top_k": {"type": "integer", "description": "Max results", "default": 5},
                        "status": {"type": "string", "description": "Lifecycle status filter"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "skillgenie_list",
                "description": "List registered skills with optional status/category filter.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "category": {"type": "string"},
                        "limit": {"type": "integer", "default": 50},
                    },
                },
            },
            {
                "name": "skillgenie_recommend",
                "description": "Recommend the most relevant skills for a task.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Task description"},
                        "top_k": {"type": "integer", "default": 5},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "skillgenie_learn",
                "description": "Learn a new skill from an execution trace.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "trace_id": {"type": "string", "description": "Trace identifier to learn from"},
                    },
                    "required": ["trace_id"],
                },
            },
            {
                "name": "skillgenie_export",
                "description": "Export a skill as a standalone MCP tool definition.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "skill_id": {"type": "string", "description": "Skill identifier"},
                    },
                    "required": ["skill_id"],
                },
            },
            {
                "name": "skillgenie_health",
                "description": "Get explainable health breakdown for a skill.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "skill_id": {"type": "string", "description": "Skill identifier"},
                    },
                    "required": ["skill_id"],
                },
            },
        ]

    def handle(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Route an MCP tool call to the appropriate handler."""
        handlers = {
            "skillgenie_search": self._search,
            "skillgenie_list": self._list,
            "skillgenie_recommend": self._recommend,
            "skillgenie_learn": self._learn,
            "skillgenie_export": self._export,
            "skillgenie_health": self._health,
        }

        handler = handlers.get(method)
        if handler is None:
            return {"error": {"code": -32601, "message": f"Unknown method: {method}"}}

        try:
            return {"result": handler(params)}
        except Exception as exc:
            self._logger.error(f"MCP call {method} failed: {exc}")
            return {"error": {"code": -32000, "message": str(exc)}}

    def _search(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        query = params["query"]
        top_k = params.get("top_k", 5)
        status = params.get("status")
        results = self._engine.store.search(query=query, top_k=top_k, status=status)
        return [
            {
                "skill_id": str(r["skill"].id),
                "name": r["skill"].name,
                "description": r["skill"].description,
                "status": r["skill"].status.value,
                "similarity": r.get("similarity", 0.0),
                "type": r.get("type", ""),
            }
            for r in results
        ]

    def _list(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        status = params.get("status")
        category = params.get("category")
        limit = params.get("limit", 50)
        skills = self._engine.store.list(status=status, category=category, limit=limit)
        return [
            {
                "skill_id": str(s.id),
                "name": s.name,
                "description": s.description,
                "category": s.category,
                "version": s.version,
                "status": s.status.value,
                "health": s.health.value,
                "confidence": s.confidence_score,
                "quality": s.quality_score,
                "success_rate": s.success_rate,
            }
            for s in skills
        ]

    def _recommend(self, params: dict[str, Any]) -> list[dict[str, Any]]:
        query = params["query"]
        top_k = params.get("top_k", 5)
        recs = self._engine.recommend(query=query, top_k=top_k)
        return [
            {
                "skill_id": str(r.capability_id),
                "name": r.metadata.get("skill_name", ""),
                "type": r.recommendation_type.value,
                "confidence": r.confidence_score,
                "similarity": r.similarity_score,
                "ranking": r.ranking_score,
                "reason": r.reason,
            }
            for r in recs
        ]

    def _learn(self, params: dict[str, Any]) -> dict[str, Any]:
        trace_id = params["trace_id"]
        skill = self._engine.learn(trace_id)
        return {
            "skill_id": str(skill.id),
            "name": skill.name,
            "status": skill.status.value,
        }

    def _export(self, params: dict[str, Any]) -> dict[str, Any]:
        skill_id = UUID(str(params["skill_id"]))
        skill = self._engine.store.get(skill_id)
        if skill is None:
            raise ValueError(f"Skill '{skill_id}' not found.")

        tool: dict[str, Any] = {
            "name": _slugify(skill.name),
            "description": skill.description,
            "inputSchema": skill.metadata.get("input_output", {}).get("input", {"type": "object"}),
            "skillgenie": {
                "skill_id": str(skill.id),
                "version": skill.version,
                "status": skill.status.value,
                "confidence": skill.confidence_score,
                "quality": skill.quality_score,
                "health": skill.health.value,
                "workflow": skill.workflow,
                "tools": skill.metadata.get("tools", []),
            },
        }
        return tool

    def _health(self, params: dict[str, Any]) -> dict[str, Any]:
        from skillgenie.core.feedback import SkillFeedbackService

        feedback = SkillFeedbackService(
            config=self._engine.config,
            database=self._engine.database,
            skill_repository=self._engine.capabilities,
            audit_repository=self._engine.audit,
        )
        skill_id = UUID(str(params["skill_id"]))
        skill = self._engine.store.get(skill_id)
        if skill is None:
            raise ValueError(f"Skill '{skill_id}' not found.")

        explanation = feedback.health_explanation(skill)
        explanation["skill_id"] = str(skill.id)
        explanation["name"] = skill.name
        return explanation

    def start(self, host: str = "127.0.0.1", port: int = 3100) -> None:
        """Start a simple stdio-based MCP transport loop."""
        self._logger.info(
            f"SkillGenie MCP server listening on {host}:{port} (stdio)"
        )
        import sys

        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                continue

            method = request.get("method", "")
            params = request.get("params", {})
            req_id = request.get("id")

            response = self.handle(method, params)
            if req_id is not None:
                response["jsonrpc"] = "2.0"
                response["id"] = req_id
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()


def _slugify(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("__", "_")
        .strip("_")
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="SkillGenie MCP Server")
    parser.add_argument("--config", default="config/config.json", help="Config file path")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3100)
    args = parser.parse_args()

    server = SkillGenieMCPServer(config_file=args.config)
    server.start(host=args.host, port=args.port)


if __name__ == "__main__":
    main()