# ============================================================================
# Project      : SkillGenie
# File         : marketplace.py
# Description  : Local marketplace — publish exported skills into a catalog
#                directory, build a searchable index and query it.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from skillgenie.marketplace.exporters import (
    _slugify,
    export_skill,
)


class MarketplaceIndex:
    """
    Publish and search exported skills in a local catalog directory.
    """

    INDEX_NAME = "marketplace.index.json"

    def __init__(self, catalog_dir: str = "marketplace"):
        self._catalog = Path(catalog_dir)

    def publish(
        self,
        skill: Any,
        fmt: str = "bundle",
    ) -> dict[str, Any]:
        """
        Write a skill export into the catalog and refresh the index.
        """

        self._catalog.mkdir(parents=True, exist_ok=True)

        extension = {
            "claude": ".claude.md",
            "openai": ".openai.json",
            "bundle": ".bundle.json",
            "mcp": ".mcp.json",
        }[fmt]

        filename = f"{_slugify(skill.name)}{extension}"

        artifact = export_skill(skill, fmt)

        if isinstance(artifact, str):
            payload = artifact.encode("utf-8")
        else:
            payload = json.dumps(artifact, indent=2, default=str).encode(
                "utf-8"
            )

        target = self._catalog / filename

        target.write_bytes(payload)

        entry = {
            "file": str(target),
            "format": fmt,
            "size_bytes": len(payload),
            "digest": hashlib.sha256(payload).hexdigest()[:16],
            "published_at": datetime.utcnow().isoformat(),
        }

        self._remember(skill, entry)

        return entry

    def catalog(self) -> list[dict[str, Any]]:
        """
        List all published skill entries.
        """

        return list(self._load_index().values())

    def search(self, query: str) -> list[dict[str, Any]]:
        """
        Filter the catalog by name/description tokens.
        """

        tokens = {
            word
            for word in re.findall(r"[a-z0-9]+", query.lower())
            if len(word) > 1
        }

        if not tokens:
            return self.catalog()

        matches: list[dict[str, Any]] = []

        for entry in self._load_index().values():
            haystack = (
                f"{entry.get('name', '')} "
                f"{entry.get('description', '')} "
                f"{entry.get('category', '')}"
            ).lower()

            if tokens & {
                word
                for word in re.findall(r"[a-z0-9]+", haystack)
            }:
                matches.append(entry)

        return matches

    def _remember(self, skill: Any, entry: dict[str, Any]) -> None:
        """
        Merge the new entry into the persisted index.
        """

        index = self._load_index()

        records = index.get(entry["file"], {})
        records.update(entry)
        records.setdefault("name", skill.name)
        records.setdefault("description", getattr(skill, "description", ""))
        records.setdefault(
            "category", getattr(skill, "category", "") or ""
        )

        versions = records.setdefault("versions", {})
        versions[entry["format"]] = {
            "digest": entry["digest"],
            "published_at": entry["published_at"],
        }

        index[entry["file"]] = records

        self._catalog.mkdir(parents=True, exist_ok=True)

        (self._catalog / self.INDEX_NAME).write_text(
            json.dumps(index, indent=2, default=str),
            encoding="utf-8",
        )

    def _load_index(self) -> dict[str, Any]:
        """
        Read the persisted index from the catalog directory.
        """

        index_path = self._catalog / self.INDEX_NAME

        if not index_path.exists():
            return {}

        try:
            return json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}