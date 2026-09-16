"""
Tests for the benchmark harness.
"""

from skillgenie.config import Config
from benchmarks.harness import BenchmarkRunner, BenchmarkScenario


def _config(tmp_path):
    return Config(str(tmp_path / "config.json"))


def _scenario():
    return BenchmarkScenario(
        name="web-research",
        description="Web research tasks",
        skills=[
            {
                "name": "Web Researcher",
                "description": "search the web and summarize results",
                "category": "research",
                "metadata": {
                    "search_profile": {
                        "tokens": "Web Researcher search the web and summarize results",
                    }
                },
            }
        ],
        tasks=["search the web and summarize results"],
    )


def test_benchmark_run_without_store(tmp_path):
    config = _config(tmp_path)

    report = BenchmarkRunner(config).run(_scenario(), iterations=3)

    assert report["scenario"] == "web-research"
    assert 0.0 <= report["with_skillgenie"]["success_rate"] <= 1.0
    assert 0.0 <= report["without_skillgenie"]["success_rate"] <= 1.0
    assert "improvement" in report


def test_benchmark_run_with_recommender(tmp_path, store, config):
    runner = BenchmarkRunner(config, store=store)
    # config fixture is already a Config; use it
    scenario = _scenario()
    report = runner.run(scenario, iterations=2, with_skillgenie=True)

    assert report["scenario"] == "web-research"


def test_benchmark_fake_task_deterministic(tmp_path):
    config = _config(tmp_path)
    runner = BenchmarkRunner(config)
    scenario = _scenario()

    matching = runner._fake_task("search the web and summarize results", scenario)
    unrelated = runner._fake_task("paint a fence", scenario)

    # matching task should succeed where unrelated may not
    assert matching[0] is True
    assert matching[1] < unrelated[1]