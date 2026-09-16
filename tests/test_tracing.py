"""
Tests for trace parsing, extraction and duplicate detection.
"""

from uuid import uuid4

import pytest

from skillgenie.tracing.duplicate_detector import DuplicateDetector
from skillgenie.tracing.input_output_extractor import InputOutputExtractor
from skillgenie.tracing.parser import TraceParser
from skillgenie.tracing.prompt_extractor import PromptExtractor
from skillgenie.tracing.skill_generator import SkillGenerator
from skillgenie.tracing.tool_extractor import ToolExtractor
from skillgenie.tracing.workflow_extractor import WorkflowExtractor
from tests.conftest import make_capability, make_skill


def make_normalized_trace(
    task: str = "Research a topic",
    steps: list | None = None,
    tools: list | None = None,
    prompts: list | None = None,
):
    return {
        "framework": "custom",
        "trace_id": str(uuid4()),
        "task": task,
        "goal": task,
        "input": {"query": task},
        "output": {"result": "ok"},
        "steps": steps
        or [
            {"name": "search", "tool": "web_search", "output": {"result": "found"}},
            {"name": "summarize", "tool": "summarize", "output": {"result": "done"}},
        ],
        "tools": tools
        or [
            {"name": "web_search", "type": "web"},
            {"name": "summarize", "type": "llm"},
        ],
        "prompts": prompts
        or [{"role": "user", "content": "Please research a topic"}],
        "llm_calls": [],
        "errors": [],
        "metadata": {"category": "research"},
        "created_at": "2026-09-16T00:00:00",
    }


def test_parser_normalizes_trace():
    parser = TraceParser()

    trace = make_normalized_trace()

    parsed = parser.parse(trace, framework="custom")

    assert parsed["task"] == "Research a topic"
    assert len(parsed["steps"]) == 2
    assert len(parsed["tools"]) == 2
    assert parsed["statistics"]["step_count"] == 2
    assert parser.validate(parsed) is True


def test_parser_rejects_unknown_framework():
    parser = TraceParser()

    with pytest.raises(ValueError):
        parser.parse(make_normalized_trace(), framework="unknown-framework")


def test_parser_validate_missing_fields():
    parser = TraceParser()

    assert parser.validate({"framework": "custom"}) is False


def test_workflow_extractor():
    extractor = WorkflowExtractor()

    workflow = extractor.extract(make_normalized_trace())

    assert workflow["name"] == "Research a topic"
    assert workflow["steps"][0]["order"] == 1
    assert workflow["steps"][0]["tool"] == "web_search"
    assert workflow["statistics"]["total_steps"] == 2
    assert len(extractor.flatten(workflow)) == 2


def test_tool_extractor_unique():
    extractor = ToolExtractor()

    trace = make_normalized_trace(tools=[
        {"name": "web_search", "type": "web", "usage": 3},
        {"name": "web_search", "type": "web"},
        {"name": "summarize", "type": "llm"},
    ])

    tools = extractor.extract(trace)

    assert len(extractor.unique_tools(tools)) == 2


def test_prompt_extractor():
    extractor = PromptExtractor()

    trace = make_normalized_trace(prompts=[
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "hi"},
    ])

    prompts = extractor.extract(trace)

    assert len(extractor.unique_prompts(prompts)) == 2


def test_io_extractor():
    extractor = InputOutputExtractor()

    io = extractor.extract(make_normalized_trace())

    assert io["input"]["query"] == "Research a topic"
    assert io["output"]["result"] == "ok"


def test_skill_generator_produces_candidate():
    generator = SkillGenerator()

    skill = generator.generate(
        trace=make_normalized_trace(),
        workflow=WorkflowExtractor().extract(make_normalized_trace()),
        tools=ToolExtractor().extract(make_normalized_trace()),
        prompts=PromptExtractor().extract(make_normalized_trace()),
        input_output=InputOutputExtractor().extract(make_normalized_trace()),
    )

    assert skill.name
    assert skill.description
    assert skill.category
    assert skill.workflow["steps"]
    assert skill.metadata["tools"]


# ---------------------------------------------------------------------------
# Duplicate detection
# ---------------------------------------------------------------------------


def _build_detector(config, capability_repository, store):
    return DuplicateDetector(
        repository=capability_repository,
        config=config,
        store=store,
    )


def _seed(repo):
    row = make_skill()

    repo.create(
        capability_id=row["id"],
        name=row["name"],
        description=row["description"],
        category=row["category"],
        version=row["version"],
        status=row["status"],
    )

    repo.update(capability_id=row["id"], **{k: v for k, v in row.items() if k != "id"})

    return row["id"]


def test_duplicate_by_exact_name(config, capability_repository, store):
    _seed(capability_repository)

    detector = _build_detector(config, capability_repository, store)

    candidate = make_capability()

    duplicate = detector.find_duplicate(candidate, threshold=0.9)

    assert duplicate is not None
    assert duplicate.name == candidate.name


def test_duplicate_by_similarity(config, capability_repository, store):
    from skillgenie.core.scorer import SkillScorer

    row = make_skill()
    row["embedding"] = [1.0, 0.0, 0.0]

    capability_repository.create(
        capability_id=row["id"],
        name=row["name"],
        description=row["description"],
        category=row["category"],
        version=row["version"],
        status=row["status"],
    )

    capability_repository.update(
        capability_id=row["id"],
        **{k: v for k, v in row.items() if k != "id"},
    )

    detector = DuplicateDetector(
        repository=capability_repository,
        config=config,
        scorer=SkillScorer(config),
        store=store,
    )

    candidate = make_capability(name="Different Name", embedding=[1.0, 0.0, 0.0])

    duplicate = detector.find_duplicate(candidate, threshold=0.9)

    assert duplicate is not None
    assert str(duplicate.id) == str(row["id"])


def test_no_duplicate_when_below_threshold(config, capability_repository, store):
    from skillgenie.core.scorer import SkillScorer

    row = make_skill(embedding=[1.0, 0.0, 0.0])

    capability_repository.create(
        capability_id=row["id"],
        name=row["name"],
        description=row["description"],
        category=row["category"],
        version=row["version"],
        status=row["status"],
    )

    capability_repository.update(
        capability_id=row["id"],
        **{k: v for k, v in row.items() if k != "id"},
    )

    detector = DuplicateDetector(
        repository=capability_repository,
        config=config,
        scorer=SkillScorer(config),
        store=store,
    )

    candidate = make_capability(name="Unrelated Skill", embedding=[0.0, 0.0, 1.0])

    assert detector.find_duplicate(candidate, threshold=0.9) is None


def test_similarity_helpers(config, capability_repository, store):
    detector = _build_detector(config, capability_repository, store)

    assert detector.is_similar(0.95) is True
    assert detector.is_similar(0.8) is False
    assert detector.is_similar(0.95, threshold=0.9) is True
    assert detector.similarity_score([1.0, 0.0], [1.0, 0.0]) == 1.0