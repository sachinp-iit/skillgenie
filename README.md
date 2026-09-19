# 🧞 SkillGenie

> **Autonomous Skill Discovery, Learning, Evolution & Recommendation Framework for Agentic AI**

SkillGenie is an open-source Python library that enables AI agents to automatically discover, learn, evolve, recommend, and manage reusable skills from execution traces.

Instead of manually hardcoding workflows, SkillGenie continuously learns from successful executions and builds a reusable skill library that improves future agent performance.

---

# Features

- Autonomous Skill Discovery
- Skill Learning from Execution Traces
- Skill Generation
- Skill Evaluation
- Skill Recommendation
- Skill Lifecycle Management
- Skill Confidence & Quality Scoring
- Skill Evolution
- Skill Health Monitoring
- Skill Relationship Graph
- Human Approval Workflow
- Semantic Search
- PostgreSQL + pgvector Support
- Framework Agnostic
- Version Management
- Model Context Protocol (MCP) Server & Skill Export
- Framework Recording Hooks (LangGraph, CrewAI, custom)
- Benchmark Harness
- Outcome Feedback Loop & Drift Detection
- Enterprise Governance (privacy, secret vault, explainability)
- Compositional Multi-Skill Planning
- Learned Recommendation Ranking (bandit / ELO-style fits)
- Skill Validation & Readiness Scoring
- Autonomous Drift Remediation
- Gap & Novelty Discovery
- Skill Marketplace & Claude / OpenAI / MCP Exports
- Provenance & Explainability Dossiers
- SkillGenie Arena (head-to-head battles + ELO leaderboard)

---

# Supported Frameworks

- LangGraph
- LangChain
- LlamaIndex
- Haystack
- CrewAI
- AutoGen
- Microsoft Semantic Kernel
- PydanticAI
- Custom Agent Frameworks

---

# Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| Database | PostgreSQL |
| Vector Database | pgvector |
| ORM | SQLAlchemy 2.x |
| Validation | Pydantic v2 |
| Configuration | JSON + Environment Variables |
| Logging | Loguru |
| Serialization | orjson |

---

# Installation

Clone the repository.

```bash
git clone git@github.com:sachinp-iit/skillgenie.git

cd skillgenie
```

Create a virtual environment.

```bash
python -m venv .venv
```

Activate the virtual environment.

### Windows

```bash
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies.

```bash
pip install -r requirements.txt
```

Install SkillGenie in editable mode.

```bash
pip install -e .
```

---

# Quick Start

Run the end-to-end demo (uses in-memory repositories, no database required):

```bash
python examples/demo.py
```

Run the full mock-based test suite:

```bash
python -m pytest tests -q
```

---

# Command Line Interface

```text
usage: skillgenie [-h] {init-db,ingest,learn,learn-all,relearn,list,show,recommend,
                   approve,reject,publish,deprecate,archive,restore,exec,health,
                   search,api,outcome,drift,failures,explain,export,mcp,governance,
                   benchmark,plan,plan-execute,validate,remediate,gaps,provenance,
                   arena} ...
```

Examples:

```bash
# Initialize the database
skillgenie init-db

# Ingest an execution trace from JSON
skillgenie ingest trace.json

# Learn/publish/recommend skills
skillgenie learn <trace-id>
skillgenie approve <skill-id>
skillgenie recommend "search the web for product reviews"

# Feedback loop & drift detection
skillgenie outcome <skill-id> SUCCESS --time 120
skillgenie drift <skill-id>
skillgenie failures <skill-id>
skillgenie explain <skill-id>

# Export a skill (claude / openai / bundle / mcp)
skillgenie export <skill-id> --format bundle --output ./exports

# Enterprise governance summary
skillgenie governance

# Run the benchmark suite (no database required)
skillgenie benchmark

# Compose and execute a multi-skill plan
skillgenie plan "plan a software project"
skillgenie plan-execute "plan a software project"

# Validate a skill and get readiness verdict + actionable next steps
skillgenie validate <skill-id>

# Autonomously remediate a drifting/failing skill
skillgenie remediate <skill-id> --mode auto

# Discover gaps, novelty opportunities and redundancy
skillgenie gaps

# Provenance & explainability dossier
skillgenie provenance <skill-id>

# SkillGenie Arena: battle two skills, then view the ELO leaderboard
skillgenie arena battle "research a topic" --skill-a <id> --skill-b <id> --rounds 5
skillgenie arena rank

# Serve the MCP server over stdio
skillgenie mcp --port 3100

# Serve the REST API + dashboards
skillgenie api --host 0.0.0.0 --port 8000
```

---

# REST API & Dashboards

Start the API with `skillgenie api` (or `uvicorn skillgenie.api.app:create_app --factory`):

| Route | Description |
|-------|-------------|
| `GET /api/v1/health` | Registry health overview |
| `GET /api/v1/skills` | List + search skills |
| `GET /api/v1/skills/{skill_id}` | Skill detail |
| `POST /api/v1/learn` | Learn a skill from a trace |
| `POST /api/v1/learn/all` | Learn skills from all traces |
| `POST /api/v1/skills/{skill_id}/relearn` | Relearn a skill |
| `POST /api/v1/skills/{skill_id}/evaluate` | Evaluate a skill |
| `POST /api/v1/skills/{skill_id}/{approve,publish,deprecate,archive,restore,reject}` | Lifecycle actions |
| `POST /api/v1/recommend` | Recommend skills for a query |
| `POST /api/v1/recommend/trace/{trace_id}` | Recommend from a trace |
| `GET /api/v1/recommend/similar/{skill_id}` | Similar skills |
| `POST /api/v1/outcomes` | Record a recommendation outcome |
| `GET /api/v1/outcomes` | List recent outcomes |
| `GET /api/v1/skills/{skill_id}/drift` | Drift detection |
| `GET /api/v1/skills/{skill_id}/failures` | Recent failures |
| `GET /api/v1/skills/{skill_id}/health/explain` | Explainable health score |
| `GET /api/v1/export/{skill_id}` | Export skill (claude/openai/bundle/mcp) |
| `POST /api/v1/plan` | Compose a multi-skill plan |
| `POST /api/v1/plan/execute` | Plan, execute and optionally learn |
| `GET /api/v1/skills/{skill_id}/validate` | Validation verdict + readiness score |
| `POST /api/v1/skills/{skill_id}/remediate` | Autonomous drift remediation |
| `GET /api/v1/monitor/gaps` | Gap / novelty / redundancy analysis |
| `GET /api/v1/skills/{skill_id}/provenance` | Provenance dossier |
| `POST /api/v1/arena/battle` | Head-to-head skill battle |
| `GET /api/v1/arena/leaderboard` | Arena ELO leaderboard |
| `POST /api/v1/governance/secrets` | Store a secret in the vault |
| `GET /api/v1/governance/secrets` | List vault secrets |
| `POST /api/v1/traces` | Create a trace |
| `GET /api/v1/traces` | List traces |
| `GET /api/v1/traces/{trace_id}` | Trace detail |
| `POST /api/v1/executions` | Record an execution |
| `GET /api/v1/executions` | List executions |
| `GET /api/v1/metrics/skills/{skill_id}` | Metrics history |
| `GET /api/v1/audit/skills/{skill_id}` | Audit trail |
| `GET /api/v1/monitor/overview` | Monitoring overview |
| `GET /api/v1/monitor/governance` | Governance/compliance summary |
| `GET /api/v1/admin/overview` | Admin overview |

Dashboards (served by the API):

- `GET /admin` — Admin dashboard: search, lifecycle actions, health overview
- `GET /monitor` — Monitoring dashboard: registry stats, status & health charts

Interactive API docs are available at `GET /docs`.

---

# Configuration

Copy

```text
.env.example
```

to

```text
.env
```

Update the following values:

- PostgreSQL Connection
- Embedding Model
- OpenRouter API Key
- Learning Thresholds

Configuration sections include:

| Section | Purpose |
|---------|---------|
| `feedback` | Outcome window and drift threshold (`drift_threshold`, `drift_window_hours`) |
| `recommendation` | Top-K / score weight / fallback behavior |
| `ranking` | Learned ranking mode + bandit/recency/latency fit weights |
| `arena` | Arena leaderboard persistence path |
| `mcp` | MCP server host/port |
| `integrations` | Framework recording hooks toggle |
| `benchmark` | Benchmark task success overlap |
| `governance` | Telemetry, data residency, PII redaction, secret vault |

---

# Project Structure

```text
skillgenie/
│
├── skillgenie/
│   ├── core/
│   │   ├── engine.py
│   │   ├── learner.py
│   │   ├── evaluator.py
│   │   ├── recommender.py
│   │   ├── scorer.py
│   │   ├── lifecycle.py
│   │   ├── health.py
│   │   ├── evolution.py
│   │   ├── feedback.py
│   │   ├── execution_service.py
│   │   ├── ranking.py
│   │   ├── validator.py
│   │   ├── remediator.py
│   │   ├── gaps.py
│   │   ├── provenance.py
│   │   └── __init__.py
│   │
│   ├── arena/
│   │   ├── agent.py
│   │   ├── battle.py
│   │   └── __init__.py
│   │
│   ├── marketplace/
│   │   ├── exporters.py
│   │   ├── marketplace.py
│   │   └── __init__.py
│   │
│   ├── planning/
│   │   ├── composer.py
│   │   └── __init__.py
│   │
│   ├── api/
│   │   ├── app.py
│   │   ├── routers.py
│   │   ├── schemas.py
│   │   └── dependencies.py
│   │
│   ├── cli/
│   │   ├── main.py
│   │   └── __init__.py
│   │
│   ├── dashboard/
│   │   └── templates/
│   │       ├── admin.html
│   │       └── monitor.html
│   │
│   ├── mcp/
│   │   ├── server.py
│   │   ├── __main__.py
│   │   └── __init__.py
│   │
│   ├── integrations/
│   │   ├── base.py
│   │   ├── langgraph.py
│   │   ├── crewai.py
│   │   ├── custom.py
│   │   └── __init__.py
│   │
│   ├── governance/
│   │   ├── privacy.py
│   │   ├── vault.py
│   │   ├── manager.py
│   │   └── __init__.py
│   │
│   ├── adapters/
│   │   ├── base.py
│   │   ├── generic.py
│   │   ├── frameworks.py
│   │   └── __init__.py
│   │
│   ├── embeddings/
│   │   ├── base.py
│   │   ├── hash.py
│   │   ├── local.py
│   │   ├── openrouter.py
│   │   ├── factory.py
│   │   └── __init__.py
│   │
│   ├── graph/
│   │   └── relationship_graph.py
│   │
│   ├── storage/
│   │   └── skill_store.py
│   │
│   ├── database/
│   │   ├── connection.py
│   │   ├── session.py
│   │   ├── manager.py
│   │   ├── bootstrap.py
│   │   ├── migrations.py
│   │   ├── repositories/
│   │   │   ├── base_repository.py
│   │   │   ├── capability_repository.py
│   │   │   ├── trace_repository.py
│   │   │   ├── metrics_repository.py
│   │   │   ├── audit_repository.py
│   │   │   ├── execution_repository.py
│   │   │   ├── recommendation_repository.py
│   │   │   ├── outcome_repository.py
│   │   │   └── __init__.py
│   │   └── sql/
│   │       ├── create_tables.py
│   │       ├── indexes.py
│   │       └── __init__.py
│   │
│   ├── models/
│   │   ├── capability.py
│   │   ├── execution.py
│   │   ├── metrics.py
│   │   ├── outcome.py
│   │   ├── plan.py
│   │   ├── recommendation.py
│   │   ├── trace.py
│   │   └── __init__.py
│   │
│   ├── tracing/
│   │   ├── parser.py
│   │   ├── workflow_extractor.py
│   │   ├── tool_extractor.py
│   │   ├── prompt_extractor.py
│   │   ├── input_output_extractor.py
│   │   ├── skill_generator.py
│   │   ├── duplicate_detector.py
│   │   └── __init__.py
│   │
│   ├── utils/
│   │   ├── logger.py
│   │   └── __init__.py
│   │
│   ├── config.py
│   ├── constants.py
│   ├── exceptions.py
│   └── __init__.py
│
├── benchmarks/
│   ├── harness.py
│   ├── run.py
│   └── __init__.py
│
├── config/
├── docs/
├── examples/
│   └── demo.py
├── tests/
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── requirements.lock.txt
└── README.md
```

---

# Current Progress

All core, API, dashboard, benchmark and pro features are implemented and
covered by a mock-based test suite (**231 tests passing**).

## Completed

### Foundation

- Project Structure
- Configuration Management (JSON + environment overrides)
- Constants
- Exception Handling
- Logging

### Database

- PostgreSQL Integration
- Database Connection / Session Managers
- Database Bootstrap & Migrations
- Schema Creation & Indexes
- Repository Layer
- Outcome Repository (`skill_outcomes` table)

### Models

- Capability (Skill) Model
- Trace Model
- Execution Model
- Metrics Model
- Recommendation Model
- Outcome Model

### Trace Processing

- Trace Parser
- Workflow / Tool / Prompt / Input-Output Extractors
- Skill Generator
- Duplicate Detector
- Framework Adapters (LangGraph, LangChain, LlamaIndex, Haystack, CrewAI,
  AutoGen, Semantic Kernel, PydanticAI, custom)

### Core Engine

- Engine (`SkillGenie`)
- Skill Learner (learn, learn-all, relearn)
- Skill Evaluator (approve / reject / publish / reevaluate)
- Skill Recommender (exact / similar / related / fallback)
- Skill Scorer (confidence & quality)
- Skill Lifecycle Manager (DRAFT → CANDIDATE → APPROVED → PUBLISHED → DEPRECATED → ARCHIVED)
- Skill Evolution Engine (version bump, reopen for review, deprecate degraded, health snapshots)
- Skill Health Engine (EXCELLENT / GOOD / FAIR / POOR / CRITICAL)
- Relationship Graph Builder
- Embedding Engine (hash, sentence-transformers, OpenRouter; pluggable factory)
- Execution Service
- Outcome Feedback Loop (success-rate refresh, drift detection, explainable health)

### Interfaces

- CLI (`skillgenie` console script)
- REST API (FastAPI, `/api/v1/*`, OpenAPI docs)
- Admin Dashboard (`/admin`)
- Monitoring Dashboard (`/monitor`)
- MCP Server (stdio, 6 tools) + Skill Export
- Framework Recording Hooks (LangGraph, CrewAI, custom decorator)
- Benchmark Harness (A/B measures, latency + success deltas)
- Governance (PII redaction, data residency, encrypted secret vault)
- Comprehensive Mock-Based Test Suite (PostgreSQL not required)

### Intelligent & Autonomous Features

- **Compositional Planner** — `TaskDecomposer` + `CompositePlanner` break composite
  tasks into ordered sub-tasks, map them to the best skills, and assemble a
  dependency-aware plan (`framework: "composite"`).
- **Learned Recommendation Ranking** — `LearnedRanker` re-ranks recommendations
  using outcome-based bandit fits, recency decay, latency health and configurable
  fit weights; `ranking.mode` supports `classic | fit | bandit | learned | hybrid`.
- **Skill Validation Harness** — `SkillValidator` grades 10+ checks (progressions,
  outcomes, health, documentation, workflow integrity) into an actionable
  `READY / NEEDS_WORK / INVALID` verdict with `readiness_score`.
- **Autonomous Drift Remediation** — `SkillRemediator` detects failings skills and
  applies low-risk remediation (`flag_review`, `suppress_recommendations`, and
  forced `retrain` / `deprecate`) with full audit trail.
- **Gap & Novelty Discovery** — `SkillGapAnalyzer` surfaces low-coverage
  categories, missing tools vs. recent traces, novelty opportunities and
  redundancy.
- **Skill Marketplace** — publish a catalog index and export any skill as
  Claude (`*.claude.md`), OpenAI (`*.openai.json`), bundle (`*.bundle.json`) or
  MCP (`*.mcp.json`).
- **Provenance & Explainability** — `SkillProvenance` reconstructs a skill's
  lineage (source traces), attribution (audit trail) and outcomes, with a
  human-readable narrative.
- **SkillGenie Arena** — `ArenaAgent` simulates skills under tool-failure stress,
  and `SkillGenieArena` runs head-to-head battles scoring success, efficiency
  and resilience with ELO ratings persisted to a leaderboard.

---

# Pro Features

## Model Context Protocol (MCP)

SkillGenie ships an MCP server exposing skills as conversational tools to any
MCP-compatible client:

```bash
skillgenie mcp --host 127.0.0.1 --port 3100
```

Available tools: `skillgenie_search`, `skillgenie_list`, `skillgenie_recommend`,
`skillgenie_learn`, `skillgenie_export`, `skillgenie_health`.

Any skill can also be exported as a standalone tool definition (via CLI, API or
MCP):

```python
from skillgenie.mcp.server import SkillGenieMCPServer

server = SkillGenieMCPServer(config_file="config/config.json")
tool_definition = server._export({"skill_id": "<skill-uuid>"})
```

## Framework Recording Hooks

Record agentic runs into the SkillGenie trace store with one line:

```python
from skillgenie.integrations.langgraph import LangGraphRecorder
from skillgenie.integrations.crewai import CrewAIRecorder
from skillgenie.integrations.custom import CustomRecorder

# LangGraph: wrap the graph so every invoke() is recorded
graph = LangGraphRecorder(config).wrap(graph)

# CrewAI: record after a crew finishes
CrewAIRecorder(config).after_crew_run(result)

# Custom: decorate any agent function
@CustomRecorder(config).trace(task="Fetch stock prices")
def my_agent():
    ...
```

## Benchmark Harness

Measure what SkillGenie adds to an agent workload (no database required):

```bash
skillgenie benchmark
```

Run an A/B comparison: the same tasks executed with vs. without SkillGenie
recommendations, reporting success-rate delta, latency reduction and effort
saved.

## Outcome Feedback Loop & Drift Detection

Learn from production outcomes and catch regressions automatically:

```bash
skillgenie outcome <skill-id> SUCCESS --time 120
skillgenie drift <skill-id>      # DEGRADED / IMPROVED / STABLE
skillgenie failures <skill-id>
skillgenie explain <skill-id>    # weighted, explainable health score
```

Every outcome refreshes the skill's success rate and health. Drift detection
compares recent vs. historical success rates over a configurable window.

## Enterprise Governance

- **Privacy** — automatic PII redaction (emails, phones, cards, IPs) and
  configurable data residency.
- **Secret vault** — encrypted at-rest storage via `VAULT_KEY` (falls back to a
  local encrypted file or OS keyring).
- **Governance report** — telemetry, residency and vault compliance summary via
  CLI, API (`GET /api/v1/monitor/governance`) or engine:

```python
engine = SkillGenie(config_file="config/config.json")
print(engine.governance_report())
```

## Intelligent & Autonomous Features

### Compositional Multi-Skill Planning

Decompose composite tasks, map steps to skills, and (optionally) execute the
plan end-to-end with learned composite skills:

```bash
skillgenie plan "plan a software project"
skillgenie plan-execute "plan a software project"
```

The engine exposes `engine.compose(task, top_k, status)` returning ordered
sub-tasks, selected skills and an executable plan.

### Learned Recommendation Ranking

Re-rank recommendations from outcome feedback instead of static scores:

```python
from skillgenie import SkillGenie

engine = SkillGenie(config_file="config/config.json")
engine.config.set("ranking.mode", "hybrid")

results = engine.recommend("search the web for product reviews")
for hit in results["results"]:
    print(hit["skill"]["name"], hit["reason"], hit.get("learned_score"))
```

Modes: `classic` (no re-ranking), `fit` (dot-product fit rank), `bandit`
(Thompson-style success pulls), `learned` (hybrid without classic relevance)
and `hybrid` (all signals).

### Skill Validation Harness

Grade a skill against lifecycle, outcomes, health, documentation and workflow
integrity checks into an actionable verdict:

```bash
skillgenie validate <skill-id>       # READY / NEEDS_WORK / INVALID
```

Returns `readiness_score`, per-check results and suggested next actions.

### Autonomous Drift Remediation

When a skill falls behind its `drift_threshold`, remediate automatically with
safe, reversible actions and a full audit trail:

```bash
skillgenie remediate <skill-id> --mode auto
skillgenie remediate <skill-id> --mode review --force   # allows retrain/deprecate
```

### Gap & Novelty Discovery

Analyze registry coverage vs. recent agent traces to find missing categories,
absent tools, novelty opportunities and redundancy:

```bash
skillgenie gaps
```

### Skill Marketplace & Exports

Publish a catalog and export skills to external ecosystems:

```bash
skillgenie export <skill-id> --format bundle --output ./exports
```

Formats: `claude` (`{slug}.claude.md`), `openai` (`{slug}.openai.json`),
`bundle` (`{slug}.bundle.json`), `mcp` (`{slug}.mcp.json`) plus a
`marketplace.index.json` catalog with sha256 digests.

### Provenance & Explainability

Rebuild where a skill came from, who touched it, and why it is (or is not)
trusted:

```bash
skillgenie provenance <skill-id>
```

Returns source traces, audit trail, outcome history and a narrative explanation.

### SkillGenie Arena

Battle two skills head-to-head under tool-failure stress and rank them by ELO:

```bash
skillgenie arena battle "research a topic" --skill-a <id> --skill-b <id> --rounds 5
skillgenie arena rank
```

Scores combine success rate, efficiency and resilience; ratings and battle
counts persist to `arena.leaderboard.json` (configurable via `arena.leaderboard_path`).

---

# Development Status

Current Phase:

**Feature Complete** — core engine, CLI, REST API, dashboards, MCP server,
recording hooks, benchmark harness, feedback/drift loop, governance, and all
eight intelligent features (planning, learned ranking, validation,
remediation, gap discovery, marketplace, provenance, arena) are implemented
with a mock-based test suite (231 tests passing).

Next Milestones:

1. Live PostgreSQL/pgvector integration testing
2. Production Release (v0.1.0)

---

# Vision

Build the world's most advanced autonomous skill learning framework for Agentic AI.

SkillGenie enables AI agents to continuously learn from experience, discover reusable skills, evaluate their effectiveness, recommend the best skills for future tasks, and improve autonomously over time.

---

# License

MIT License

---

# Author

**Sachin Pate**

---

# Contributing

Contributions, issues, feature requests, and pull requests are welcome.