---
title: Getting Started
layout: default
nav_order: 2
---

# Getting Started
{: .no_toc }

Install Collection Swarm and run your first simulation in under a minute.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

## Prerequisites

| Dependency | Version | Required for |
|:-----------|:--------|:-------------|
| Python | 3.12+ | All modes |
| Node.js | 22+ | Cursor SDK backend only |
| NVIDIA NIM API key | — | NIM backend only |
| Cursor API key | — | Cursor SDK backend only |

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/pedrochagasmaster/collection-swarm.git
cd collection-swarm
```

### 2. Install Python Dependencies

```bash
pip install -e ".[dev]"
```

This installs the `collection-swarm` CLI tool and all runtime dependencies including FastAPI, Click, Pydantic, LiteLLM, Rich, and the test suite tools.

### 3. (Optional) Install Cursor SDK Bridge

If you plan to use Cursor SDK models:

```bash
cd cursor_sdk_bridge && npm install && cd ..
```

## Running Your First Simulation

No API keys needed — the scripted backend works fully offline:

```bash
collection-swarm simulate \
  --profile cooperative_hardship \
  --strategy empathetic_payment_plan
```

You will see a full collector-debtor transcript in Portuguese followed by a judgment table with metrics like payment probability, compliance score, and escalation risk.

### What Happens Under the Hood

1. **Configuration loads** from `config/` — the debtor profile, collector strategy, prompt templates, model config, and simulation settings.
2. **SimulationEngine** creates `CollectorAgent`, `DebtorAgent`, and `Judge`, all routed through the `LLMRouter` to the `ScriptedBackend`.
3. The engine alternates collector and debtor turns until an end signal, stalemate, or turn limit.
4. The **Judge** evaluates the full transcript and produces a structured `Judgment` with 8 scored metrics.
5. The result is saved to `output/collection_swarm.sqlite` (unless `--no-save` is passed).

## Running with Live Models

### Setting Up API Keys

Create a `.env` file in the repository root:

```bash
NVIDIA_NIM_API_KEY=your_nvidia_key
CURSOR_API_KEY=your_cursor_key
```

The application loads `.env` automatically without overriding already-exported environment variables.

### Running a Live Simulation

```bash
collection-swarm simulate \
  --profile cooperative_hardship \
  --strategy empathetic_payment_plan \
  --conversation-model nim-mistral-large-3-675b \
  --judge-model cursor-claude-4.6-opus-high-thinking \
  --no-save
```

Remove `--no-save` to persist results to the database.

## Exploring Profiles and Strategies

```bash
collection-swarm list-profiles
collection-swarm list-strategies
```

These commands print formatted tables of all configured debtor profiles and collector strategies.

## Launching the Web Dashboard

```bash
# Seed demo data (optional, creates 24 synthetic simulation results)
collection-swarm seed --count 24

# Start the dashboard
collection-swarm serve
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) to browse results, launch simulations, run matrix sweeps, and generate reports.

## Running the Test Suite

```bash
pytest -q
```

The test suite covers configuration loading, domain models, the conversation engine, judge parsing, SQLite persistence, matrix generation, playbook output, CLI commands, web API routes, and more.

## Project Layout

```
collection-swarm/
├── src/collection_swarm/       # Main application package
│   ├── agents/                 # Collector, Debtor, Judge agents
│   ├── analysis/               # Compliance, statistics, objections, playbook
│   ├── backends/               # LLM backends: scripted, NIM, Cursor SDK
│   ├── web/                    # FastAPI dashboard + static assets
│   ├── cli.py                  # CLI entry point
│   ├── config.py               # YAML config loader
│   ├── engine.py               # Simulation engine
│   ├── models.py               # Domain models (Pydantic)
│   ├── runner.py               # Matrix runner
│   ├── store.py                # SQLite store
│   ├── arena.py                # Elo rating system
│   ├── evolution.py            # Strategy evolution
│   ├── adversarial.py          # Profile hardening
│   ├── calibration.py          # Judge calibration
│   ├── model_evaluation.py     # Model role evaluation
│   └── env.py                  # .env file loader
├── config/                     # YAML configuration files
│   ├── debtor_profiles.yaml
│   ├── collector_strategies.yaml
│   ├── models.yaml
│   ├── prompts.yaml
│   └── simulation.yaml
├── cursor_sdk_bridge/          # Node.js bridge for Cursor SDK
├── tests/                      # Test suite (17 files)
├── docs/                       # Reports and documentation
└── pyproject.toml              # Package definition
```
