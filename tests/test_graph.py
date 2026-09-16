"""
Tests for the skill relationship graph builder.
"""

from skillgenie.graph.relationship_graph import SkillGraphBuilder
from tests.conftest import make_capability


def _build(config, store):
    return SkillGraphBuilder(config=config, store=store)


def test_build_related_by_shared_tools(config, store):
    builder = _build(config, store)

    skill = make_capability(embedding=[1.0, 0.0, 0.0])

    other = make_capability(
        name="Web Scraper",
        embedding=[0.9, 0.1, 0.0],
    )

    graph = builder.build(skill, [other], similarity_threshold=0.8)

    assert graph["related"]

    assert any(edge["capability_id"] == str(other.id) for edge in graph["related"])

    assert graph["parents"] == []
    assert graph["children"] == []


def test_build_respects_threshold(config, store):
    builder = _build(config, store)

    skill = make_capability(embedding=[1.0, 0.0, 0.0])

    other = make_capability(name="Finance Tool", embedding=[0.1, 0.9, 0.0])

    graph = builder.build(skill, [other], similarity_threshold=0.9)

    assert graph["related"] == []


def test_build_tool_overlap(config, store):
    builder = _build(config, store)

    metadata = {
        "tools": [{"name": "web_search", "type": "web"}],
        "prompts": [],
        "input_output": {},
    }

    skill = make_capability(embedding=[1.0, 0.0], metadata=metadata)
    other = make_capability(name="Searcher", embedding=[0.0, 1.0], metadata=metadata)

    graph = builder.build(skill, [other], similarity_threshold=0.99)

    assert graph["tool_overlap"]

    assert "web_search" in graph["tool_overlap"][0].get("shared_tools", [])


def test_refresh_persists_graphs(config, store, capability_repository):
    from tests.conftest import make_skill

    row = make_skill()

    capability_repository.create(
        capability_id=row["id"],
        name=row["name"],
        description=row["description"],
        category=row["category"],
        version=row["version"],
        status=row["status"],
    )

    capability_repository.update(
        capability_id=row["id"], **{k: v for k, v in row.items() if k != "id"}
    )

    builder = _build(config, store)

    graphs = builder.refresh(store.list())

    row_after = capability_repository.get_by_id(row["id"])

    assert row_after["relationship_graph"]["related"] == []