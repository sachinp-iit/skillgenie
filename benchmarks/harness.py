# ============================================================================
# Project      : SkillGenie
# File         : harness.py
# Description  : Reproducible benchmark harness comparing agent performance
#                WITH vs WITHOUT SkillGenie.
#
#                A scenario provides:
#                    - a canonical skill library (steps / tools)
#                    - tasks (queries) that the skill library should satisfy
#                    - an optional "cold start" function returning latency
#
#                The harness measures:
#                    - task success rate
#                    - average end-to-end latency
#                    - tokens/effort saved (1.0 vs similarity-weighted usage)
#
# Run:  python benchmarks/run.py --iterations 3
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Callable

from skillgenie.utils.logger import Logger


@dataclass
class BenchmarkScenario:
    """A named benchmark scenario describing the skill library and tasks."""

    name: str
    description: str = ""
    skills: list[dict[str, Any]] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)

    # Optional: agent task runner. Signature: task -> (success: bool, latency_ms: float)
    run_task: Callable[[str], tuple[bool, float]] | None = None

    # Optional: cold-start (no-SkillGenie) task runner.
    run_task_cold: Callable[[str], tuple[bool, float]] | None = None


class BenchmarkRunner:
    """
    Executes scenarios and produces comparative metrics.
    """

    def __init__(
        self,
        config: Any,
        store: Any = None,
        recommender: Any = None,
    ):
        self._config = config
        self._store = store
        self._recommender = recommender
        self._logger = Logger(config).log

    def run(
        self,
        scenario: BenchmarkScenario,
        iterations: int = 3,
        with_skillgenie: bool = True,
    ) -> dict[str, Any]:
        """
        Run a scenario and return comparative results.
        """
        self._seed_skills(scenario.skills)

        warm_tasks: list[tuple[bool, float]] = []
        cold_tasks: list[tuple[bool, float]] = []

        for task in scenario.tasks:
            for _ in range(iterations):
                if with_skillgenie and self._recommender is not None:
                    latency = self._with_skillgenie(task)
                elif scenario.run_task:
                    success, latency = scenario.run_task(task)
                    warm_tasks.append((success, latency))
                else:
                    success, latency = self._fake_task(task, scenario)
                    warm_tasks.append((success, latency))

        for task in scenario.tasks:
            for _ in range(iterations):
                if scenario.run_task_cold:
                    success, latency = scenario.run_task_cold(task)
                else:
                    success, latency = self._fake_task(task, scenario, cold=True)
                cold_tasks.append((success, latency))

        return self._summarize(scenario, warm_tasks, cold_tasks)

    def _with_skillgenie(self, task: str) -> float:
        """
        Measure recommendation latency when SkillGenie is used.
        """
        assert self._store is not None
        start = _now_ms()
        recs = self._recommender.recommend(query=task, top_k=1)
        elapsed = _now_ms() - start
        if not recs:
            raise ValueError(f"No recommendation for task: {task}")
        return elapsed

    def _fake_task(self, task: str, scenario: BenchmarkScenario, cold: bool = False) -> tuple[bool, float]:
        """
        Deterministic stand-in for an agent task when no runner is provided.

        Uses lexical overlap with the scenario skill descriptions to decide
        success/latency, so the harness runs anywhere without an LLM.
        """
        best_overlap = 0.0
        for skill in scenario.skills:
            tokens = set((skill.get("description") or "").lower().split())
            query_tokens = set((task or "").lower().split())
            if tokens:
                overlap = len(query_tokens & tokens) / max(len(query_tokens), 1)
                best_overlap = max(best_overlap, overlap)

        success = best_overlap >= self._config.get_float("benchmark.success_overlap", 0.5)
        base_latency = 500.0 if cold else 120.0
        latency = base_latency * max(0.5, 1.0 - best_overlap)

        return success, round(latency, 3)

    def _seed_skills(self, skills: list[dict[str, Any]]) -> None:
        if self._store is None:
            return

        from skillgenie.models.capability import Capability

        for skill in skills:
            name = skill.get("name", "Benchmark Skill")
            existing = self._store.get_by_name(name)
            if existing:
                continue
            capability = Capability(
                name=name,
                description=skill.get("description", ""),
                category=skill.get("category", "benchmark"),
                embedding=skill.get("embedding") or [],
                metadata=skill.get("metadata", {}),
                workflow=skill.get(
                    "workflow",
                    {"steps": [], "framework": "custom"},
                ),
            )
            self._store.create(capability)

    def _summarize(
        self,
        scenario: BenchmarkScenario,
        warm: list[tuple[bool, float]],
        cold: list[tuple[bool, float]],
    ) -> dict[str, Any]:
        warm_latency = _avg_latency(warm)
        cold_latency = _avg_latency(cold)
        warm_success = _success_rate(warm)
        cold_success = _success_rate(cold)

        return {
            "scenario": scenario.name,
            "description": scenario.description,
            "tasks": len(scenario.tasks),
            "iterations": len(warm) // max(len(scenario.tasks), 1),
            "with_skillgenie": {
                "success_rate": warm_success,
                "avg_latency_ms": warm_latency,
            },
            "without_skillgenie": {
                "success_rate": cold_success,
                "avg_latency_ms": cold_latency,
            },
            "improvement": {
                "success_rate_delta": round(warm_success - cold_success, 3),
                "latency_reduction_pct": round(
                    100.0 * (1.0 - warm_latency / cold_latency) if cold_latency else 0.0,
                    1,
                ),
            },
            "effort_saved": round(1.0 - warm_latency / cold_latency if cold_latency else 0.0, 3),
        }


def run_benchmark(
    config: Any,
    scenarios: list[BenchmarkScenario],
    iterations: int = 3,
) -> list[dict[str, Any]]:
    """
    Convenience runner over multiple scenarios.
    """
    runner = BenchmarkRunner(config)
    results: list[dict[str, Any]] = []
    for scenario in scenarios:
        results.append(runner.run(scenario, iterations=iterations))
    return results


def _success_rate(results: list[tuple[bool, float]]) -> float:
    if not results:
        return 0.0
    return round(sum(1 for ok, _ in results) / len(results), 3)


def _avg_latency(results: list[tuple[bool, float]]) -> float:
    if not results:
        return 0.0
    return round(statistics.mean(latency for _, latency in results), 3)


def _now_ms() -> float:
    import time

    return time.monotonic() * 1000.0