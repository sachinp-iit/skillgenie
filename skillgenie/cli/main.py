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
    }

    if args.command in command_map:
        command_map[args.command](args, engine)
    elif args.command in Lifecycle_actions:
        cmd_lifecycle(args, engine, action=args.command)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()