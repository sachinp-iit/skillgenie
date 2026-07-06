# 🧞 SkillGenie

> **Autonomous Capability Discovery, Learning, Evolution & Recommendation Framework for Agentic AI**

SkillGenie is an open-source Python library that enables AI agents to automatically learn reusable capabilities from execution traces, evaluate them, recommend them for future tasks, monitor their health, and continuously evolve over time.

Instead of manually creating workflows, SkillGenie observes successful executions and converts them into reusable capabilities that improve future agent performance.

---

# Features

- Autonomous Capability Discovery
- Execution Trace Learning
- Capability Recommendation
- Capability Lifecycle Management
- Confidence & Quality Scoring
- Capability Evolution
- Capability Health Monitoring
- Relationship Graph
- PostgreSQL + pgvector Support
- Framework Agnostic
- Human Approval Workflow
- Versioning
- Semantic Search

---

# Supported Frameworks

- LangGraph
- LangChain
- CrewAI
- AutoGen
- Haystack
- LlamaIndex
- Microsoft Semantic Kernel
- PydanticAI
- Custom Agent Frameworks

---

# Installation

Clone the repository.

```bash
git clone git@github.com:sachinp-iit/skillgenie.git

cd skillgenie
```

Create virtual environment.

```bash
python -m venv .venv
```

Activate virtual environment.

Windows

```bash
.venv\Scripts\activate
```

Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies.

```bash
pip install -r requirements.txt
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

Update

- PostgreSQL
- Embedding Model
- OpenRouter API Key

---

# Project Structure

```text
skillgenie/
│
├── skillgenie/
├── config/
├── docs/
├── examples/
├── tests/
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

# Roadmap

- Capability Discovery
- Capability Recommendation
- Capability Evolution
- Capability Registry
- Capability Health Monitoring
- Capability Lifecycle
- Admin Dashboard
- Human Approval Workflow
- Framework Integrations
- Enterprise Features

---

# License

MIT License

---

# Author

**Sachin Pate**

---

# Contributing

Contributions, issues, feature requests, and ideas are welcome.

---

# Vision

> Build the world's first autonomous capability operating system for AI agents.
