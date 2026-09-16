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
                   search,api} ...
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

# Serve the REST API + dashboards
skillgenie api --host 0.0.0.0 --port 8000
```

---

# REST API & Dashboards

Start the API with `skillgenie api` (or `uvicorn skillgenie.api.app:create_app --factory`):

| Route | Description |
|-------|-------------|
| `GET /api/v1/health` | Registry health overview |
| `GET /api/v1/capabilities` | List + search skills |
| `POST /api/v1/capabilities/learn` | Learn a skill from a trace |
| `POST /api/v1/capabilities/{id}/recommend` | Recommend skills |
| `GET /api/v1/capabilities/{id}` | Skill detail |
| `PUT /api/v1/capabilities/{id}` | Update capabilities (approve, publish, evolve...) |
| `DELETE /api/v1/capabilities/{id}` | Delete a skill |
| `GET /api/v1/executions` | Execution records |
| `GET /api/v1/recommendations` | Recent recommendations |

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
│   │   ├── execution_service.py
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

All core, API and dashboard features are implemented and covered by a mock-based
test suite (**133 tests passing**).

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

### Models

- Capability (Skill) Model
- Trace Model
- Execution Model
- Metrics Model
- Recommendation Model

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

### Interfaces

- CLI (`skillgenie` console script)
- REST API (FastAPI, `/api/v1/*`, OpenAPI docs)
- Admin Dashboard (`/admin`)
- Monitoring Dashboard (`/monitor`)
- Comprehensive Mock-Based Test Suite (PostgreSQL not required)

---

# Development Status

Current Phase:

**Feature Complete** — core engine, CLI, REST API, dashboards and mock-based
test suite are implemented.

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