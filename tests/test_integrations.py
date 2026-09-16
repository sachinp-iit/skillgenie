"""
Tests for framework recording hooks/middleware.
"""

from skillgenie.integrations.base import BaseRecorder, record_trace
from skillgenie.integrations.crewai import CrewAIRecorder
from skillgenie.integrations.custom import CustomRecorder
from skillgenie.integrations.langgraph import LangGraphRecorder
from tests.conftest import FakeTraceRepository


def test_base_recorder_persists_trace(config, trace_repository):
    trace_id = record_trace(
        config,
        trace_repository,
        task="Summarize a document",
        steps=[{"name": "read"}],
        tools=[{"name": "reader"}],
    )

    assert trace_id

    row = trace_repository.get_by_id(trace_id)

    assert row is not None
    assert row["trace"]["task"] == "Summarize a document"
    assert row["trace"]["steps"] == [{"name": "read"}]
    assert row["agent_framework"] == "custom"


def test_recorder_disabled_skips_persist(config, trace_repository):
    recorder = BaseRecorder(config, trace_repository, framework="custom")
    recorder._enabled = False

    trace_id = recorder.record(task="Hidden task")

    assert trace_id == ""


def test_langgraph_recorder_extracts_nodes(config, trace_repository):
    recorder = LangGraphRecorder(config, trace_repository)

    trace_id = recorder.after_run(
        {
            "task": "Crawl a website",
            "nodes": [
                {"name": "fetch", "type": "tool", "tool": "web_fetch", "output": {"ok": True}},
                {"name": "parse", "type": "task"},
            ],
        }
    )

    row = trace_repository.get_by_id(trace_id)
    steps = row["trace"]["steps"]

    assert len(steps) == 2
    assert steps[0]["name"] == "fetch"
    assert steps[0]["tool"] == "web_fetch"


def test_langgraph_recorder_wrap_decorates_invoke(config, trace_repository):
    recorder = LangGraphRecorder(config, trace_repository)

    calls = []

    class FakeGraph:
        def invoke(self, input_data, **kwargs):
            calls.append(input_data)
            return {"nodes": [], "task": "wrapped run"}

    graph = recorder.wrap(FakeGraph())
    result = graph.invoke({"query": "hello"})

    assert result["task"] == "wrapped run"
    assert len(trace_repository.list()) == 1


def test_crewai_recorder_extracts_agents(config, trace_repository):
    recorder = CrewAIRecorder(config, trace_repository)

    trace_id = recorder.after_crew_run(
        {
            "task": "Market research",
            "agents": [
                {"role": "Researcher", "tool": "web_search", "output": "found"},
            ],
        }
    )

    row = trace_repository.get_by_id(trace_id)
    steps = row["trace"]["steps"]

    assert len(steps) == 1
    assert steps[0]["name"] == "Researcher"


def test_crewai_recorder_handles_raw_output(config, trace_repository):
    recorder = CrewAIRecorder(config, trace_repository)

    trace_id = recorder.after_crew_run({"raw": "no agents, just output"})

    row = trace_repository.get_by_id(trace_id)
    assert len(row["trace"]["steps"]) == 1


def test_custom_recorder_decorator(config, trace_repository):
    recorder = CustomRecorder(config, trace_repository)

    @recorder.trace(task="Fetch stock prices", inspect_result=True)
    def run_agent():
        return {"steps": [{"name": "api_call"}], "tools": [{"name": "stocks_api"}]}

    result = run_agent()

    assert result["steps"]

    traces = trace_repository.list()
    assert len(traces) == 1
    assert traces[0]["trace_name"] == "Fetch stock prices"
    assert traces[0]["trace"]["steps"] == [{"name": "api_call"}]