"""
Tests for the skill marketplace exporters and catalog.
"""

import pytest

from skillgenie.marketplace import MarketplaceIndex, export_skill
from skillgenie.marketplace.exporters import (
    export_bundle,
    export_claude,
    export_mcp,
    export_openai,
)
from tests.conftest import make_capability


@pytest.fixture
def engine(tmp_path):
    from unittest.mock import Mock

    from skillgenie.core.engine import SkillGenie

    from tests.conftest import FakeCapabilityRepository

    database = Mock()

    skillgenie = SkillGenie(
        config_file=str(tmp_path / "config.json"),
        database=database,
        embeddings_enabled=False,
    )

    fake = FakeCapabilityRepository()

    database.get_session.side_effect = AssertionError(
        "Should not hit the database."
    )

    skillgenie.capabilities = fake
    skillgenie.store._repository = fake

    yield skillgenie

    skillgenie.shutdown()


def _skill():
    return make_capability(
        name="Web Researcher",
        description="search the web and summarize results",
        category="research",
        status="PUBLISHED",
    )


def test_claude_export_is_markdown_with_frontmatter():
    doc = export_claude(_skill())

    assert doc.startswith("---\n")
    assert "name: web_researcher" in doc
    assert "description:" in doc
    assert "version: 1.0.0" in doc
    assert "## Steps" in doc


def test_openai_export_function_shape():
    definition = export_openai(_skill())

    assert definition["type"] == "function"
    function = definition["function"]
    assert function["name"] == "web_researcher"
    assert function["parameters"]["type"] == "object"
    assert "skillgenie" in function


def test_mcp_export_tool_shape():
    skill = _skill()
    tool = export_mcp(skill)

    assert tool["name"] == "web_researcher"
    assert "inputSchema" in tool
    assert tool["skillgenie"]["skill_id"] == str(skill.id)


def test_bundle_export_manifest_and_artifacts():
    skill = _skill()
    bundle = export_bundle(skill)

    assert bundle["manifest"]["format"] == "skillgenie-bundle"
    assert bundle["manifest"]["id"] == str(skill.id)
    assert bundle["artifacts"]["workflow"] == skill.workflow
    assert "embedding" in bundle["artifacts"]


def test_export_skill_dispatch():
    assert isinstance(export_skill(_skill(), "claude"), str)
    assert export_skill(_skill(), "openai")["type"] == "function"
    assert export_skill(_skill(), "mcp")["name"] == "web_researcher"
    assert (
        export_skill(_skill(), "bundle")["manifest"]["format"]
        == "skillgenie-bundle"
    )


def test_export_unknown_format_raises():
    import pytest

    with pytest.raises(ValueError):
        export_skill(_skill(), "terraform")


def test_marketplace_publish_and_catalog(tmp_path):
    skill = _skill()
    index = MarketplaceIndex(str(tmp_path / "store"))

    entry = index.publish(skill, fmt="bundle")

    assert entry["format"] == "bundle"
    assert entry["digest"]
    assert (tmp_path / "store" / "web_researcher.bundle.json").exists()
    assert (tmp_path / "store" / MarketplaceIndex.INDEX_NAME).exists()

    catalog = index.catalog()
    assert len(catalog) == 1
    assert catalog[0]["name"] == "Web Researcher"


def test_marketplace_search_filters(tmp_path):
    index = MarketplaceIndex(str(tmp_path / "store"))

    web = make_capability(
        name="Web Researcher",
        description="search the web and summarize results",
        category="research",
        status="PUBLISHED",
    )
    email = make_capability(
        name="Email Drafter",
        description="draft and send transactional email campaigns",
        category="communication",
        status="PUBLISHED",
    )

    index.publish(web, fmt="bundle")
    index.publish(email, fmt="bundle")

    results = index.search("email")

    assert len(results) == 1
    assert results[0]["name"] == "Email Drafter"


def test_engine_export_publishes_bundle(engine, tmp_path):

    skill = make_capability(
        name="Web Researcher",
        description="search the web and summarize results",
        category="research",
        status="PUBLISHED",
    )
    engine.store.create(skill)

    entry = engine.export_skill(
        skill.id,
        fmt="bundle",
        output_dir=str(tmp_path / "store"),
    )

    assert entry["format"] == "bundle"
    assert entry["digest"]

    catalog = MarketplaceIndex(str(tmp_path / "store")).catalog()
    assert len(catalog) == 1