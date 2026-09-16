"""
Tests for framework adapters.
"""

from skillgenie.adapters import (
    generic,
    get_adapter,
    supported_frameworks,
)
from skillgenie.adapters.generic import GenericAdapter
from skillgenie.adapters.base import FrameworkAdapter


def test_supported_frameworks_registered():
    frameworks = supported_frameworks()

    for expected in (
        "custom",
        "langgraph",
        "langchain",
        "llamaindex",
        "haystack",
        "crewai",
        "autogen",
        "semantic-kernel",
        "pydantic-ai",
    ):
        assert expected in frameworks


def test_get_adapter_custom():
    adapter = get_adapter("custom")

    assert isinstance(adapter, GenericAdapter)
    assert adapter.framework == "custom"


def test_get_adapter_unknown_falls_back():
    adapter = get_adapter("some-random-framework")

    assert isinstance(adapter, FrameworkAdapter)


def test_generic_adapter_passthrough():
    adapter = GenericAdapter()

    trace = {
        "task": "Summarize a document",
        "steps": [{"name": "read"}],
        "tools": [{"name": "reader"}],
        "metadata": {"category": "text"},
    }

    normalized = adapter.normalize(trace)

    assert normalized["task"] == "Summarize a document"
    assert normalized["steps"] == [{"name": "read"}]
    assert normalized["tools"] == [{"name": "reader"}]
    assert normalized["metadata"]["category"] == "text"


def test_langgraph_adapter_normalizes_internal_state():
    adapter = get_adapter("langgraph")

    trace = {
        "id": "run-1",
        "task": "Crawl a website",
        "nodes": [
            {
                "name": "fetch",
                "type": "tool",
                "tool": {"type": "web_fetch", "kwargs": {"url": "https://x.com"}},
                "outputs": {"content": "html"},
            }
        ],
        "metadata": {"category": "web"},
    }

    normalized = adapter.normalize(trace)

    assert normalized["task"] == "Crawl a website"
    assert len(normalized["steps"]) >= 1

    step = normalized["steps"][0]

    assert step.get("output") is not None or step.get("outputs") is not None


def test_crewai_adapter_handles_kwargs_style():
    adapter = get_adapter("crewai")

    trace = {
        "task": "Plan a trip",
        "agents": [
            {"name": "planner", "steps": [{"tool": "search", "output": "x"}]}
        ],
    }

    normalized = adapter.normalize(trace)

    assert normalized["task"] == "Plan a trip"