---
title: Home
layout: home
nav_order: 1
---

# Collection Swarm Documentation
{: .fs-9 }

AI-driven simulator for testing debt-collection strategies before they ever touch a real customer.
{: .fs-6 .fw-300 }

---

## What is Collection Swarm?

Collection Swarm runs **synthetic multi-turn conversations** between three AI roles — **Collector**, **Debtor**, and **Judge** — to measure what actually works across debtor archetypes, negotiation strategies, and model providers.

Results are persisted to SQLite, surfaced in a web dashboard, and distilled into a Markdown playbook that ranks strategies, flags compliance risk, and highlights the best-performing approaches.

## Why It Exists

Collection teams need to improve outcomes **without experimenting on real people**. There is no scalable way to A/B test conversation strategies against every debtor archetype. Collection Swarm solves that by simulating the entire space with fully synthetic data.

Use it to answer questions like:

- Which strategy works best for hardship profiles?
- Which approaches trigger compliance risk?
- Which model is better at role-playing debtors versus judging outcomes?
- What transcripts should become training examples?
- How do strategy changes affect payment probability and debtor satisfaction?

## Key Capabilities

| Capability | Description |
|:-----------|:------------|
| **Single Simulation** | Run one collector-debtor conversation with a judge evaluation |
| **Matrix Runs** | Sweep all combinations of profiles × strategies × models |
| **Tournaments** | Elo-rated competitions between strategies and profiles |
| **Strategy Evolution** | LLM-driven genetic evolution of collection strategies |
| **Profile Hardening** | Adversarial generation of tougher debtor profiles |
| **Judge Calibration** | Compare judge scores against human labels |
| **Model Evaluation** | Probe multiple LLMs for role fitness across collector, debtor, and judge |
| **Playbook Generation** | Auto-generate Markdown playbooks with rankings and compliance alerts |
| **Web Dashboard** | Browser-based UI for running simulations and exploring results |

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────┐
│  config/                                                │
│  profiles · strategies · models · prompts · simulation  │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
                 SimulationEngine
                    │    │    │
        ┌───────────┘    │    └───────────┐
        ▼                ▼                ▼
  CollectorAgent    DebtorAgent        Judge
        │                │                │
        └───────┬────────┘                │
                ▼                         ▼
            LLMRouter ────────────────────┘
           ╱    │    ╲
     Scripted  NIM  Cursor SDK
                         │
                         ▼
                 SimulationResult
                    │         │
           ┌────────┘         └────────┐
           ▼                           ▼
     SQLite Store              Web Dashboard
           │
           ▼
  Analysis Pipeline
   ├── Statistics
   ├── Compliance
   ├── Objections
   └── Playbook
```

## Technology Stack

| Layer | Technology |
|:------|:-----------|
| Language | Python 3.12+ |
| Models | Pydantic v2 |
| CLI | Click + Rich |
| Web | FastAPI + Uvicorn |
| Database | SQLite (via stdlib `sqlite3`) |
| LLM Routing | LiteLLM (NIM), `@cursor/sdk` (Cursor) |
| Templates | Jinja2, YAML |
| Sanitization | Bleach + Python Markdown |
| Testing | pytest + pytest-asyncio + httpx |
| Bridge | Node.js 22+ (Cursor SDK) |

## Quick Navigation

Browse the documentation sections in the sidebar, or jump directly to:

- [Getting Started]({% link getting-started.md %}) — Installation and first simulation
- [Concepts]({% link concepts.md %}) — Core domain concepts explained
- [Simulation Engine]({% link engine.md %}) — How conversations are orchestrated
- [Agents]({% link agents.md %}) — Collector, Debtor, and Judge agents
- [LLM Backends]({% link backends.md %}) — Scripted, NIM, and Cursor SDK backends
- [Configuration]({% link configuration.md %}) — YAML configuration reference
- [Data Models]({% link models.md %}) — Pydantic domain models
- [Persistence]({% link store.md %}) — SQLite schema and queries
- [Analysis Pipeline]({% link analysis.md %}) — Statistics, compliance, objections, and playbooks
- [Tournaments & Elo]({% link arena.md %}) — Tournament system and Elo ratings
- [Strategy Evolution]({% link evolution.md %}) — Genetic evolution of strategies
- [Adversarial Hardening]({% link adversarial.md %}) — Profile hardening
- [Calibration]({% link calibration.md %}) — Judge calibration against human labels
- [Model Evaluation]({% link model-evaluation.md %}) — Cross-model role fitness probing
- [Runner & Orchestration]({% link runner.md %}) — Matrix runs and batch orchestration
- [Web Dashboard]({% link web-dashboard.md %}) — FastAPI web interface
- [CLI Reference]({% link cli.md %}) — Command-line interface
- [Testing]({% link testing.md %}) — Test suite overview
