# ============================================================================
# Project      : SkillGenie
# File         : main.py
# Description  : Command-line interface for SkillGenie.
#
# Author       : Sachin Pate
# License      : MIT
# ============================================================================

from __future__ import annotations

import argparse
import json
import sys
from uuid import UUID

from skillgenie.core.engine import SkillGenie
from skillgenie.exceptions import SkillGenieError
from skillgenie.storage.skill_store import capability_to_dict


def build_parser() -> argparse.ArgumentParser:
    """
    Build the CLI argument parser.
    """

    parser = argparse.ArgumentParser(
        prog="skillgenie",
        description="SkillGenie CLI — Autonomous skill learning and "
        "management for Agentic AI.",
    )

    parser.add_argument(
        "--config",
        default="config/config.json",
        help="Path to configuration file.",
    )

    sub = parser.add_subparsers(dest="command")

    # init-db
    sub.add_parser("init-db", help="Initialize the database schema.")

    # ingest-trace
    ingest = sub.add_parser("ingest", help="Ingest a raw trace from a JSON file.")
    ingest.add_argument(
        "file",
        nargs="?",
        help="Path to JSON file. Reads stdin when omitted.",
    )
    ingest.add_argument("--name", default=None, help="Trace name.")
    ingest.add_argument(
        "--framework",
        default="custom",
        help="Source agent framework.",
    )

    # learn
    learn = sub.add_parser("learn", help="Learn a skill from a trace.")
    learn.add_argument("trace_id", help="Trace ID to learn from.")

    # learn-all
    sub.add_parser("learn-all", help="Learn skills from all traces.")

    # relearn
    relearn = sub.add_parser("relearn", help="Relearn a skill.")
    relearn.add_argument("skill_id", help="Skill ID to relearn.")

    # list
    ls = sub.add_parser("list", help="List skills.")
    ls.add_argument("--status", default=None, help="Filter by status.")
    ls.add_argument("--category", default=None, help="Filter by category.")

    # show
    show = sub.add_parser("show", help="Show skill details.")
    show.add_argument("skill_id", help="Skill ID.")

    # recommend
    rec = sub.add_parser("recommend", help="Recommend skills for a task.")
    rec.add_argument("query", help="Task description.")
    rec.add_argument("--top", type=int, default=5, help="Number of results.")

    # approve/reject/publish/deprecate/archive/restore
    for action_name in ("approve", "reject", "publish", "deprecate", "archive", "restore"):
        act = sub.add_parser(action_name, help=f"{action_name.title()} a skill.")
        act.add_argument("skill_id", help="Skill ID.")
        if action_name == "reject":
            act.add_argument("reason", nargs="?", default="", help="Rejection reason.")

    # record-execution
    exec_cmd = sub.add_parser("exec", help="Record a skill execution.")
    exec_cmd.add_argument("skill_id", help="Skill ID.")
    exec_cmd.add_argument("--task", required=True, help="Task name.")
    exec_cmd.add_argument("--status", default="SUCCESS", help="Execution status.")
    exec_cmd.add_argument("--time", type=float, default=0.0, help="Duration (ms).")

    # health
    sub.add_parser("health", help="Show skill health overview.")

    # search
    search = sub.add_parser("search", help="Semantic search for skills.")
    search.add_argument("query", help="Search query.")
    search.add_argument("--top", type=int, default=5, help="Number of results.")

    # run-api
    run_api = sub.add_parser("api", help="Start the REST API server.")
    run_api.add_argument("--host", default="127.0.0.1")
    run_api.add_argument("--port", type=int, default=8000)
    run_api.add_argument("--reload", action="store_true", help="Auto-reload.")

    # outcome (feedback loop)
    outcome = sub.add_parser("outcome", help="Record a recommendation outcome.")
    outcome.add_argument("skill_id", help="Skill ID.")
    outcome.add_argument(
        "--status",
        default="SUCCESS",
        help="Outcome: SUCCESS/FAILED/PARTIAL/CANCELLED.",
    )
    outcome.add_argument("--time", type=float, default=0.0, help="Latency (ms).")
    outcome.add_argument(
        "--recommendation-id",
        default=None,
        help="Originating recommendation ID.",
    )
    outcome.add_argument("--rating", type=float, default=None, help="Optional 0-5 rating.")

    # drift
    drift = sub.add_parser("drift", help="Detect performance drift for a skill.")
    drift.add_argument("skill_id", help="Skill ID.")

    # failures
    failures = sub.add_parser("failures", help="Show recent failures for a skill.")
    failures.add_argument("skill_id", help="Skill ID.")
    failures.add_argument("--limit", type=int, default=20)

    # explain-health
    explain = sub.add_parser("explain", help="Explain a skill's health score.")
    explain.add_argument("skill_id", help="Skill ID.")

    # validate
    validate = sub.add_parser("validate", help="Validate a skill for readiness.")
    validate.add_argument("skill_id", help="Skill ID.")

    # export
    export = sub.add_parser(
        "export",
        help="Export a skill (claude/openai/bundle/mcp).",
    )
    export.add_argument("skill_id", help="Skill ID.")
    export.add_argument(
        "--format",
        default="mcp",
        choices=["claude", "openai", "bundle", "mcp"],
        help="Export format identifier.",
    )
    export.add_argument(
        "--output",
        default=None,
        help="Publish into this marketplace catalog directory.",
    )

    # plan (compositional planner)
    plan = sub.add_parser("plan", help="Compose a multi-skill plan for a task.")
    plan.add_argument("task", help="Composite task description.")
    plan.add_argument(
        "--top", type=int, default=3, help="Skills to consider per step."
    )

    # plan-execute
    plan_execute = sub.add_parser(
        "plan-execute", help="Plan, execute and optionally learn a composite task."
    )
    plan_execute.add_argument("task", help="Composite task description.")
    plan_execute.add_argument(
        "--learn", action="store_true", help="Learn the composite as a new skill."
    )
    plan_execute.add_argument(
        "--top", type=int, default=3, help="Skills to consider per step."
    )

    # remediate
    remediate = sub.add_parser(
        "remediate", help="Assess and remediate a drifting or failing skill."
    )
    remediate.add_argument("skill_id", help="Skill ID.")
    remediate.add_argument(
        "--mode",
        default="auto",
        choices=["auto", "review"],
        help="auto applies reversible actions; review only reports.",
    )
    remediate.add_argument(
        "--force",
        action="store_true",
        help="Also apply destructive actions (retrain/deprecate).",
    )
    remediate.add_argument(
        "--actor", default="system", help="Identity for the audit trail."
    )

    # gaps
    sub.add_parser(
        "gaps",
        help="Discover registry coverage gaps and novelty opportunities.",
    )

    # provenance
    provenance = sub.add_parser(
        "provenance",
        help="Show a skill's lineage, attribution and explanation.",
    )
    provenance.add_argument("skill_id", help="Skill ID.")

    # arena
    arena = sub.add_parser(
        "arena",
        help="SkillGenie Arena: head-to-head skill battles.",
    )
    arena_sub = arena.add_subparsers(dest="arena_command")

    battle = arena_sub.add_parser("battle", help="Run a skill battle.")
    battle.add_argument("task", help="Task for the battle.")
    battle.add_argument("--skill-a", required=True, help="First skill ID.")
    battle.add_argument("--skill-b", required=True, help="Second skill ID.")
    battle.add_argument("--rounds", type=int, default=5, help="Matches to run.")
    battle.add_argument(
        "--fail-rate",
        type=float,
        default=0.30,
        help="Tool failure injection rate (0-1).",
    )

    arena_sub.add_parser("rank", help="Show the ELO leaderboard.")

    # mcp
    mcp = sub.add_parser("mcp", help="Start the MCP server (stdio).")
    mcp.add_argument("--host", default="127.0.0.1")
    mcp.add_argument("--port", type=int, default=3100)

    # governance
    gov = sub.add_parser("governance", help="Show governance/compliance summary.")
    gov.add_argument("--set-secret", nargs=2, metavar=("NAME", "VALUE"), default=None)

    # benchmark
    bench = sub.add_parser("benchmark", help="Run the SkillGenie benchmark suite.")

    return parser


def _build_engine(config_file: str) -> SkillGenie:
    """
    Build the engine, handling database errors gracefully.
    """

    try:
        return SkillGenie(config_file=config_file)
    except Exception as exc:
        print(f"Engine initialization failed: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_init_db(args, engine: SkillGenie | None = None) -> None:
    """
    Initialize database tables.
    """

    if engine is None:
        engine = SkillGenie(config_file=args.config)

    print("Database initialized successfully.")


def cmd_ingest(args, engine: SkillGenie) -> None:
    """
    Ingest a raw trace.
    """

    if args.file and args.file != "-":
        with open(args.file, "r", encoding="utf-8") as file:
            raw = json.load(file)
    else:
        raw = json.load(sys.stdin)

    from uuid import uuid4

    trace_id = uuid4()

    trace_name = (
        args.name
        or raw.get("trace_name")
        or raw.get("task")
        or raw.get("task_description")
        or "Unnamed Trace"
    )

    task = raw.get("task") or raw.get("task_description") or ""

    engine.traces.create(
        trace_id=trace_id,
        trace_name=trace_name[:200],
        agent_framework=args.framework,
        task_description=task,
        execution_status=raw.get("execution_status", "SUCCESS"),
        execution_time_ms=float(raw.get("execution_time_ms", 0)),
        trace=raw,
        metadata=raw.get("metadata", {}),
    )

    print(json.dumps({"trace_id": str(trace_id)}))


def cmd_learn(args, engine: SkillGenie) -> None:
    """
    Learn a skill from a trace.
    """

    skill = engine.learn(args.trace_id)

    print(json.dumps(capability_to_dict(skill), indent=2, default=str))


def cmd_learn_all(args, engine: SkillGenie) -> None:
    """
    Learn skills from all traces.
    """

    skills = engine.learn_all()

    print(f"Learned {len(skills)} skill(s).")

    for skill in skills:
        print(
            f"  - {skill.name} [{skill.status.value}] "
            f"(confidence={skill.confidence_score})"
        )


def cmd_relearn(args, engine: SkillGenie) -> None:
    """
    Relearn a skill.
    """

    try:
        skill = engine.learner.relearn(args.skill_id)
        print(json.dumps(capability_to_dict(skill), indent=2, default=str))
    except SkillGenieError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def cmd_list(args, engine: SkillGenie) -> None:
    """
    List skills.
    """

    skills = engine.store.list(status=args.status, category=args.category)

    if not skills:
        print("No skills found.")
        return

    print(f"{'ID':<38} {'STATUS':<14} {'NAME':<40} {'CATEGORY':<15} {'VER':<10} {'CONF':<7} {'USE':<6}")
    print("-" * 130)

    for skill in skills:
        print(
            f"{str(skill.id):<38} "
            f"{skill.status.value:<14} "
            f"{skill.name[:40]:<40} "
            f"{(skill.category or 'general'):<15} "
            f"{skill.version:<10} "
            f"{skill.confidence_score:<7} "
            f"{skill.usage_count:<6}"
        )


def cmd_show(args, engine: SkillGenie) -> None:
    """
    Show skill details.
    """

    from uuid import UUID

    skill = engine.store.get(UUID(args.skill_id))

    if skill is None:
        print("Skill not found.", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(capability_to_dict(skill), indent=2, default=str))


def cmd_recommend(args, engine: SkillGenie) -> None:
    """
    Recommend skills.
    """

    recommendations = engine.recommend(args.query, top_k=args.top)

    if not recommendations:
        print("No recommendations.")
        return

    print(f"\nTop {len(recommendations)} recommendation(s):\n")

    for item in recommendations:
        print(
            f"  [{item.recommendation_type.value}] "
            f"{item.confidence_score * 100:.1f}%  "
            f"{item.similarity_score * 100:.1f}% similarity  "
            f"{item.reason}"
        )


def cmd_lifecycle(args, engine: SkillGenie, action: str) -> None:
    """
    Perform a lifecycle action.
    """

    if action == "reject":
        engine.evaluator.reject(
            engine.store.get(UUID(args.skill_id)),
            reason=getattr(args, "reason", ""),
        )
    else:
        getattr(engine.lifecycle, action)(args.skill_id)

    print(f"Action '{action}' applied to skill '{args.skill_id}'.")


def cmd_exec(args, engine: SkillGenie) -> None:
    """
    Record an execution.
    """

    from datetime import datetime

    execution = engine.record_execution(
        capability_id=UUID(args.skill_id),
        task_name=args.task,
        execution_status=args.status,
        execution_time_ms=args.time,
        started_at=datetime.utcnow(),
        completed_at=datetime.utcnow(),
    )

    print(
        json.dumps(
            {
                "execution_id": str(execution.id),
                "status": execution.execution_status.value,
            },
            indent=2,
        )
    )


def cmd_health(args, engine: SkillGenie) -> None:
    """
    Show health overview.
    """

    overview = engine.health_overview()

    print(json.dumps(overview, indent=2, default=str))


def cmd_search(args, engine: SkillGenie) -> None:
    """
    Semantic search.
    """

    candidates = engine.store.search(args.query, top_k=args.top)

    if not candidates:
        print("No matching skills.")
        return

    for candidate in candidates:
        skill = candidate["skill"]
        print(
            f"  [{candidate['type']}] "
            f"{candidate['ranking']:.3f}  "
            f"{skill.name}  "
            f"(sim={candidate['similarity']:.3f})"
        )


def cmd_outcome(args, engine: SkillGenie) -> None:
    """
    Record a recommendation outcome.
    """

    from uuid import UUID

    outcome = engine.record_outcome(
        capability_id=UUID(args.skill_id),
        outcome=args.status,
        recommendation_id=(
            UUID(args.recommendation_id) if args.recommendation_id else None
        ),
        latency_ms=args.time,
        rating=args.rating,
    )

    print(
        json.dumps(
            {
                "outcome_id": str(outcome.id),
                "outcome": outcome.outcome,
                "latency_ms": outcome.latency_ms,
                "rating": outcome.rating,
            },
            indent=2,
        )
    )


def cmd_drift(args, engine: SkillGenie) -> None:
    """
    Detect performance drift.
    """

    from uuid import UUID

    drift = engine.detect_drift(UUID(args.skill_id))

    if drift is None:
        print("No significant drift detected.")
        return

    print(json.dumps(drift, indent=2, default=str))


def cmd_failures(args, engine: SkillGenie) -> None:
    """
    Show recent failures.
    """

    from uuid import UUID

    failures = engine.recent_failures(UUID(args.skill_id), limit=args.limit)

    if not failures:
        print("No failures recorded.")
        return

    print(json.dumps(failures, indent=2, default=str))


def cmd_explain(args, engine: SkillGenie) -> None:
    """
    Explain a skill's health score.
    """

    from uuid import UUID

    print(json.dumps(engine.health_explanation(UUID(args.skill_id)), indent=2))


def cmd_validate(args, engine: SkillGenie) -> None:
    """
    Validate a skill for readiness.
    """

    from uuid import UUID

    report = engine.validate_skill(UUID(args.skill_id))

    print(
        f"\n{report['skill_name']} "
        f"[{report['verdict']}] "
        f"readiness={report['readiness_score']:.0%}\n"
    )

    for check in report["checks"]:
        print(f"  {check['status']:<5} {check['id']:<28} {check['label']}")

    if report["actionable"]:
        print("\nActionable items:")
        for item in report["actionable"]:
            print(f"  - {item['id']}: {item['fix']}")


def cmd_export(args, engine: SkillGenie) -> None:
    """
    Export a skill (claude/openai/bundle/mcp), optionally to a marketplace.
    """

    from uuid import UUID

    artifact = engine.export_skill(
        skill_id=UUID(args.skill_id),
        fmt=args.format,
        output_dir=args.output,
    )

    if args.output:
        print(json.dumps(artifact, indent=2))
        return

    if isinstance(artifact, str):
        print(artifact)
        return

    print(json.dumps(artifact, indent=2, default=str))


def cmd_mcp(args) -> None:
    """
    Start the MCP server.
    """

    from skillgenie.mcp.server import SkillGenieMCPServer

    server = SkillGenieMCPServer(config_file=args.config)
    server.start(host=args.host, port=args.port)


def cmd_governance(args, engine: SkillGenie) -> None:
    """
    Governance summary / secret management.
    """

    if args.set_secret:
        name, value = args.set_secret
        engine.governance.vault.set(name, value)
        print(f"Secret '{name}' stored.")
        return

    print(json.dumps(engine.governance_report(), indent=2))


def cmd_plan(args, engine: SkillGenie) -> None:
    """
    Compose a multi-skill plan for a composite task.
    """

    plan = engine.compose(task=args.task, top_k=args.top)

    print(json.dumps(plan, indent=2))


def cmd_plan_execute(args, engine: SkillGenie) -> None:
    """
    Plan, execute and optionally learn a composite task.
    """

    payload = engine.execute_plan(
        task=args.task,
        top_k=args.top,
        learn=args.learn,
    )

    print(json.dumps(payload, indent=2))


def cmd_remediate(args, engine: SkillGenie) -> None:
    """
    Assess and remediate a drifting or failing skill.
    """

    from uuid import UUID

    report = engine.remediate(
        skill_id=UUID(args.skill_id),
        mode=args.mode,
        force=args.force,
        actor=args.actor,
    )

    print(
        f"\n{report['skill_name']} -> {report['state']} "
        f"(health={report['health']})\n"
    )

    for action in report["actions"]:
        marker = "[X]" if action["applied"] else "[ ]"
        print(
            f"  {marker} {action['action']:<26} "
            f"risk={action['risk']:<6} {action['description']}"
        )

    print(f"\n{report['summary']}")


def cmd_gaps(args, engine: SkillGenie) -> None:
    """
    Discover registry coverage gaps and novelty opportunities.
    """

    analysis = engine.analyze_gaps()

    print(f"\n{analysis['summary']}\n")

    for entry in analysis["low_coverage_categories"]:
        print(
            f"  [coverage] {entry['category']:<20} "
            f"{entry['skills']} skill(s)"
        )

    for tool in analysis["tool_gaps"]:
        print(f"  [tool-gap] {tool} used in traces but not covered")

    for entry in analysis["novelty_opportunities"]:
        print(
            f"  [novelty] {entry['best_similarity']:.2f}  {entry['task']}"
        )

    for group in analysis["redundancy"]:
        names = ", ".join(item["name"] for item in group["skills"])
        print(f"  [redundant] {names}")


def cmd_provenance(args, engine: SkillGenie) -> None:
    """
    Show a skill's lineage, attribution and explanation.
    """

    from uuid import UUID

    dossier = engine.skill_provenance(UUID(args.skill_id))

    print(
        f"\n{dossier['skill_name']} (v{dossier['version']}, "
        f"{dossier['status']})\n"
    )

    print(f"  {dossier['explainability']['narrative']}\n")

    print("  Audit trail:")
    for event in dossier["attribution"]["audit_events"]:
        print(
            f"    - {event['action']:<16} "
            f"by {event['performed_by'] or 'unknown'}"
        )

    print("\n  JSON:")
    print(json.dumps(dossier, indent=2, default=str))


def cmd_arena(args, engine: SkillGenie) -> None:
    """
    SkillGenie Arena battles and rankings.
    """

    from uuid import UUID

    if args.arena_command == "rank":
        board = engine.arena_leaderboard()

        if not board:
            print("No battles recorded yet.")
            return

        print(f"\n{'RANK':<6} {'SKILL':<40} {'RATING':<10} {'BATTLES':<10}")
        print("-" * 66)

        for index, entry in enumerate(board, start=1):
            print(
                f"{index:<6} "
                f"{entry['name'][:40]:<40} "
                f"{entry['rating']:<10} "
                f"{entry['battles']:<10}"
            )
        return

    battle = engine.arena_battle(
        task=args.task,
        skill_a=UUID(args.skill_a),
        skill_b=UUID(args.skill_b),
        rounds=args.rounds,
        failure_rate=args.fail_rate,
    )

    print(
        f"\nBattle: {battle['task']}\n"
        f"  Winner: {battle['winner'] or 'draw'}\n"
    )

    for contender in battle["contenders"]:
        print(
            f"  - {contender['agent']}\n"
            f"      wins={contender['wins']} "
            f"losses={contender['losses']} "
            f"draws={contender['draws']}\n"
            f"      success_rate={contender['success_rate']} "
            f"efficiency={contender['efficiency']} "
            f"resilience={contender['resilience']}\n"
        )

    print(json.dumps(battle["elo"], indent=2))


def cmd_benchmark(args) -> None:
    """
    Run the benchmark suite.
    """

    import os

    from skillgenie.config import Config

    from benchmarks.harness import BenchmarkRunner, BenchmarkScenario

    config = Config("config/benchmark.json")

    scenarios = [
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
        )
    ]

    runner = BenchmarkRunner(config)
    report = runner.run(scenarios[0], iterations=3)
    print(json.dumps(report, indent=2))


def cmd_api(args) -> None:
    """
    Start the REST API server.
    """

    try:
        import uvicorn
    except ImportError:
        print("uvicorn is required. Install: pip install uvicorn", file=sys.stderr)
        sys.exit(1)

    uvicorn.run(
        "skillgenie.api.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


Lifecycle_actions = {
    "approve",
    "reject",
    "publish",
    "deprecate",
    "archive",
    "restore",
}


def main(argv: list[str] | None = None) -> None:
    """
    CLI entry point.
    """

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return

    if args.command == "init-db":
        cmd_init_db(args)
        return

    if args.command == "api":
        cmd_api(args)
        return

    if args.command == "mcp":
        cmd_mcp(args)
        return

    if args.command == "benchmark":
        cmd_benchmark(args)
        return

    engine = _build_engine(args.config)

    command_map = {
        "ingest": cmd_ingest,
        "learn": cmd_learn,
        "learn-all": cmd_learn_all,
        "relearn": cmd_relearn,
        "list": cmd_list,
        "show": cmd_show,
        "recommend": cmd_recommend,
        "exec": cmd_exec,
        "health": cmd_health,
        "search": cmd_search,
        "outcome": cmd_outcome,
        "drift": cmd_drift,
        "failures": cmd_failures,
        "explain": cmd_explain,
        "validate": cmd_validate,
        "export": cmd_export,
        "plan": cmd_plan,
        "plan-execute": cmd_plan_execute,
        "remediate": cmd_remediate,
        "gaps": cmd_gaps,
        "provenance": cmd_provenance,
        "arena": cmd_arena,
        "governance": cmd_governance,
    }

    if args.command in command_map:
        command_map[args.command](args, engine)
    elif args.command in Lifecycle_actions:
        cmd_lifecycle(args, engine, action=args.command)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()