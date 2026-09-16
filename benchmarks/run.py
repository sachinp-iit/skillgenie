# ============================================================================
# Project      : SkillGenie
# File         : run.py
# Description  : Run the SkillGenie benchmark suite.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skillgenie.config import Config  # noqa: E402

# Define scenario skills/tasks without requiring a database.
from benchmarks.harness import (  # noqa: E402
    BenchmarkRunner,
    BenchmarkScenario,
)


def _scenarios() -> list[BenchmarkScenario]:
    return [
        BenchmarkScenario(
            name="web-research",
            description="Web research and summarization tasks.",
            skills=[
                {
                    "name": "Web Researcher",
                    "description": "search the web and summarize results",
                    "category": "research",
                    "metadata": {"search_profile": {"tokens": "Web Researcher search the web and summarize results"}},
                }
            ],
            tasks=[
                "search the web and summarize results",
                "web research with structured summaries",
                "summarize a long technical article",
            ],
        ),
        BenchmarkScenario(
            name="flight-booking",
            description="Flight booking and fare checking tasks.",
            skills=[
                {
                    "name": "Flight Booker",
                    "description": "book flights and check fares",
                    "category": "travel",
                    "metadata": {"search_profile": {"tokens": "Flight Booker book flights and check fares"}},
                }
            ],
            tasks=[
                "book flights",
                "check flight fares",
                "compare airline prices",
            ],
        ),
    ]


def main() -> None:
    """Run all benchmark scenarios and print a summary report."""

    config = Config(os.path.join(os.getcwd(), "config/benchmark.json"))
    runner = BenchmarkRunner(config)

    print("SkillGenie Benchmark Report")
    print("=" * 60)

    for scenario in _scenarios():
        result = runner.run(scenario, iterations=3)
        print(f"\nScenario: {result['scenario']} ({result['description']})")
        print(f"  With SkillGenie:    success={result['with_skillgenie']['success_rate']:.3f}, "
              f"latency={result['with_skillgenie']['avg_latency_ms']}ms")
        print(f"  Without SkillGenie: success={result['without_skillgenie']['success_rate']:.3f}, "
              f"latency={result['without_skillgenie']['avg_latency_ms']}ms")
        print(f"  Improvement: success_delta={result['improvement']['success_rate_delta']:+.3f}, "
              f"latency_reduction={result['improvement']['latency_reduction_pct']:.1f}%")


if __name__ == "__main__":
    main()