# 🧞 SkillGenie

> **Autonomous Skill Discovery, Learning, Evolution & Recommendation Framework for Agentic AI**

SkillGenie is an open-source Python library that enables AI agents to automatically discover, learn, evolve, recommend, and manage reusable skills from execution traces.

Instead of manually hardcoding workflows, SkillGenie continuously learns from successful executions and builds a reusable skill library that improves future agent performance.

---

# Features

- Autonomous Skill Discovery
- Skill Learning from Execution Traces
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
| Configuration | JSON + .env |
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
│   ├── config.py
│   ├── constants.py
│   ├── exceptions.py
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
│   ├── models/
│   │   ├── capability.py
│   │   ├── execution.py
│   │   ├── metrics.py
│   │   ├── recommendation.py
│   │   ├── trace.py
│   │   └── __init__.py
│   ├── utils/
│   │   └── logger.py
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

- Project Structure
- Configuration Management
- Constants
- Exception Handling
- Logging
- PostgreSQL Integration
- Database Connection Manager
- Database Session Manager
- Database Bootstrap
- Database Migration
- Database Schema Creation
- Database Indexes
- Repository Layer
- Pydantic Models

## In Progress

- Core Engine
- Skill Learning Engine
- Skill Recommendation Engine
- Embedding Engine
- Skill Relationship Graph

## Planned

- Automatic Skill Generation
- Skill Evolution Engine
- Skill Evaluation Engine
- Skill Registry
- Admin Dashboard
- Monitoring Dashboard
- Framework Integrations
- REST API
- CLI Support

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