"""
Tests for the gap & novelty discovery analyzer.
"""

from uuid import uuid4

from skillgenie.core.gaps import SkillGapAnalyzer
from skillgenie.core.engine import SkillGenie
from tests.conftest import make_capability, make_raw_trace


def test_empty_registry_reports_no_gaps(config, store, trace_repository):
    analysis = SkillGapAnalyzer(
        config=config,
        store=store,
        trace_repository=trace_repository,
    ).analyze()

    assert analysis["total_skills"] == 0
    assert analysis["category_coverage"] == {}
    assert analysis["tool_gaps"] == []
    assert analysis["novelty_opportunities"] == []
    assert analysis["redundancy"] == []


def test_tool_gap_identified_from_traces(config, store, trace_repository):
    store.create(
        make_capability(
            name="Web Researcher",
            category="research",
            status="PUBLISHED",
        )
    )

    raw = make_raw_trace(
        "Scrape dynamic pages",
        tools=[
            {"name": "browser_automation", "type": "web"},
        ],
        steps=[
            {
                "name": "launch",
                "type": "task",
                "tool": "browser_automation",
            },
        ],
    )

    raw["trace"]["tools"] = [{"name": "browser_automation", "type": "web"}]
    raw["metadata"] = {"tools": [{"name": "browser_automation"}]}

    trace_repository.create(
        trace_id=uuid4(),
        trace_name=raw["trace_name"],
        agent_framework=raw["agent_framework"],
        task_description=raw["task_description"],
        execution_status=raw["execution_status"],
        execution_time_ms=raw["execution_time_ms"],
        trace=raw["trace"],
        metadata=raw["metadata"],
    )

    analysis = SkillGapAnalyzer(
        config=config,
        store=store,
        trace_repository=trace_repository,
    ).analyze()

    assert "browser_automation" in analysis["tool_gaps"]


def test_novelty_opportunity_for_unserved_task(config, store, trace_repository):
    store.create(
        make_capability(
            name="Web Researcher",
            description="search the web and summarize results",
            category="research",
            status="PUBLISHED",
        )
    )

    raw = make_raw_trace("send transactional email campaigns")

    trace_repository.create(
        trace_id=uuid4(),
        trace_name=raw["trace_name"],
        agent_framework=raw["agent_framework"],
        task_description=raw["task_description"],
        execution_status=raw["execution_status"],
        execution_time_ms=raw["execution_time_ms"],
        trace=raw["trace"],
        metadata=raw["metadata"],
    )

    analysis = SkillGapAnalyzer(
        config=config,
        store=store,
        trace_repository=trace_repository,
    ).analyze()

    assert len(analysis["novelty_opportunities"]) == 1
    entry = analysis["novelty_opportunities"][0]
    assert "email" in entry["task"]
    assert entry["best_similarity"] < 0.8


def test_low_coverage_categories_flagged(config, store, trace_repository):
    store.create(
        make_capability(
            name="Lone Skill",
            description="A single skill in its own narrow category.",
            category="marginalia",
            status="PUBLISHED",
        )
    )
    store.create(
        make_capability(
            name="Research Alpha",
            description="First research skill covering a broad topic.",
            category="research",
            status="PUBLISHED",
        )
    )
    store.create(
        make_capability(
            name="Research Beta",
            description="Second research skill overlapping the topic.",
            category="research",
            status="PUBLISHED",
        )
    )

    analysis = SkillGapAnalyzer(
        config=config,
        store=store,
        trace_repository=trace_repository,
    ).analyze()

    categories = {
        entry["category"] for entry in analysis["low_coverage_categories"]
    }
    assert "marginalia" in categories
    assert "research" not in categories


def test_redundant_skills_detected(config, store, trace_repository):
    store.create(
        make_capability(
            name="Summary Tool A",
            description="summarize long articles into brief notes",
            category="research",
            status="PUBLISHED",
        )
    )
    store.create(
        make_capability(
            name="Summary Tool B",
            description="Summarize long articles into brief notes",
            category="research",
            status="PUBLISHED",
        )
    )

    analysis = SkillGapAnalyzer(
        config=config,
        store=store,
        trace_repository=trace_repository,
    ).analyze()

    assert analysis["redundancy"]
    names = {
        name
        for group in analysis["redundancy"]
        for name in [item["name"] for item in group["skills"]]
    }
    assert "Summary Tool A" in names
    assert "Summary Tool B" in names


def test_engine_analyze_gaps_works(tmp_path):
    from unittest.mock import Mock

    from tests.conftest import FakeCapabilityRepository, FakeTraceRepository

    database = Mock()

    engine = SkillGenie(
        config_file=str(tmp_path / "config.json"),
        database=database,
        embeddings_enabled=False,
    )

    database.get_session.side_effect = AssertionError(
        "Should not hit the database."
    )

    fake_capabilities = FakeCapabilityRepository()
    fake_traces = FakeTraceRepository()

    engine.capabilities = fake_capabilities
    engine.traces = fake_traces
    engine.store._repository = fake_capabilities
    engine.gap_analyzer._trace_repository = fake_traces

    analysis = engine.analyze_gaps()

    assert "category_coverage" in analysis
    assert analysis["total_skills"] == 0

    engine.shutdown()