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
│   │   └── __init__.py
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
├── tests/
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── requirements.lock.txt
└── README.md
```

---

# Current Progress

## Completed

### Foundation

- Project Structure
- Configuration Management
- Constants
- Exception Handling
- Logging

### Database

- PostgreSQL Integration
- Database Connection Manager
- Database Session Manager
- Database Bootstrap
- Database Migration
- Database Schema Creation
- Database Indexes
- Repository Layer

### Models

- Skill Model
- Trace Model
- Execution Model
- Metrics Model
- Recommendation Model

### Trace Processing

- Trace Parser
- Workflow Extractor
- Tool Extractor
- Prompt Extractor
- Input / Output Extractor
- Skill Generator
- Duplicate Detector

---

## In Progress

### Core Engine

- Engine
- Skill Learner
- Skill Evaluator
- Skill Recommender
- Skill Scorer
- Skill Lifecycle Manager

---

## Planned

- Embedding Engine
- Relationship Graph
- Skill Registry
- Skill Evolution Engine
- Skill Health Engine
- Framework Adapters
- CLI
- REST API
- Monitoring Dashboard
- Admin Dashboard
- Comprehensive Test Suite

---

# Development Status

Current Phase:

**Core Engine Development**

Next Milestones:

1. Complete Core Module
2. Build Embedding Engine
3. Build Relationship Graph
4. Implement Recommendation Pipeline
5. Framework Integrations
6. Production Release (v0.1.0)

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