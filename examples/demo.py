# ============================================================================
# Project      : SkillGenie
# File         : examples/demo.py
# Description  : End-to-end demonstration of the SkillGenie pipeline using
#                in-memory repositories, so it runs anywhere without
#                PostgreSQL.
#
# Run with:  python examples/demo.py
#
# Author      : Sachin Pate
# License     : MIT
# ============================================================================

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from skillgenie.config import Config  # noqa: E402
from skillgenie.core.evaluator import SkillEvaluator  # noqa: E402
from skillgenie.core.evolution import SkillEvolutionEngine  # noqa: E402
from skillgenie.core.health import SkillHealthEngine  # noqa: E402
from skillgenie.core.learner import SkillLearner  # noqa: E402
from skillgenie.core.lifecycle import SkillLifecycle  # noqa: E402
from skillgenie.core.recommender import SkillRecommender  # noqa: E402
from skillgenie.core.scorer import SkillScorer  # noqa: E402
from skillgenie.storage.skill_store import SkillStore  # noqa: E402
from tests.conftest import (  # noqa: E402
    FakeAuditRepository,
    FakeCapabilityRepository,
    FakeExecutionRepository,
    FakeMetricsRepository,
    FakeRecommendationRepository,
    FakeTraceRepository,
    add_trace,
    make_raw_trace,
)

DUMMY_DATABASE = object()
WORKSPACE = tempfile.mkdtemp(prefix="skillgenie-demo-")
CONFIG_FILE = os.path.join(WORKSPACE, "config.json")


def _wiring():
    """Build the SkillGenie core pipeline wired to in-memory repositories."""

    config = Config(CONFIG_FILE)

    capability_repository = FakeCapabilityRepository()
    trace_repository = FakeTraceRepository()
    metrics_repository = FakeMetricsRepository()
    audit_repository = FakeAuditRepository()
    execution_repository = FakeExecutionRepository()
    recommendation_repository = FakeRecommendationRepository()

    scorer = SkillScorer(config)
    health_engine = SkillHealthEngine(config)
    embedder = None

    store = SkillStore(
        config=config,
        repository=capability_repository,
        embedding_provider=embedder,
        scorer=scorer,
    )

    learner = SkillLearner(
        config=config,
        database=DUMMY_DATABASE,
        trace_repository=trace_repository,
        skill_repository=capability_repository,
        metrics_repository=metrics_repository,
        audit_repository=audit_repository,
        execution_repository=execution_repository,
        embedding_provider=embedder,
    )

    evaluator = SkillEvaluator(
        config=config,
        database=DUMMY_DATABASE,
        skill_repository=capability_repository,
        metrics_repository=metrics_repository,
        audit_repository=audit_repository,
        execution_repository=execution_repository,
        scorer=scorer,
    )

    lifecycle = SkillLifecycle(
        config=config,
        database=DUMMY_DATABASE,
        skill_repository=capability_repository,
        audit_repository=audit_repository,
    )

    recommender = SkillRecommender(
        config=config,
        database=DUMMY_DATABASE,
        store=store,
        recommendation_repository=recommendation_repository,
        trace_repository=trace_repository,
    )

    evolution = SkillEvolutionEngine(
        config=config,
        database=DUMMY_DATABASE,
        store=store,
        lifecycle=lifecycle,
        health_engine=health_engine,
        skill_repository=capability_repository,
        audit_repository=audit_repository,
    )

    return config, store, learner, evaluator, recommender, evolution


def main() -> None:
    """Run the SkillGenie demo pipeline."""

    config, store, learner, evaluator, recommender, evolution = _wiring()

    print("1) Ingest a trace and learn a skill")
    trace_id = add_trace(
        learner._trace_repository,
        make_raw_trace(task="Summarize a long technical article"),
    )
    skill = learner.learn(trace_id)
    print(f"   -> learned: {skill.name} [{skill.status.value}]")

    print("2) Approve, then publish the skill")
    evaluator.approve(skill)
    skill = evaluator.publish(skill)
    print(f"   -> status: {skill.status.value}")

    print("3) Recommend skills for a similar task")
    for rec in recommender.recommend(
        "Summarize a long technical article",
        top_k=3,
    ):
        print(f"   -> {rec.metadata.get('skill_name')} "
              f"({rec.recommendation_type.value}, "
              f"similarity={rec.similarity_score:.2f})")

    print("4) Health snapshot of the registry")
    snapshot = evolution.health_snapshot()
    print("   ->", {k: v for k, v in snapshot.items() if v})

    cap = store.get(skill.id)
    print("5) Final capability")
    print("   ->", {
        "name": cap.name,
        "status": cap.status.value,
        "confidence": cap.confidence_score,
        "quality": cap.quality_score,
        "success_rate": cap.success_rate,
        "health": cap.health.value,
    })

    print("\nDemo finished. Temp workspace:", WORKSPACE)


if __name__ == "__main__":
    main()