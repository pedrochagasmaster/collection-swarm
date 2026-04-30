# Collection Swarm

![Collection Swarm project infographic](assets/collection-swarm-infographic.png)

Collection Swarm is an AI-driven simulator for testing debt-collection strategies before they ever touch a real customer.

It runs synthetic conversations between three roles:

- **Collector**: follows a configured collection strategy.
- **Debtor**: follows a synthetic profile, financial situation, objection pattern, and hard constraints.
- **Judge**: scores the transcript for payment outcome, compliance, rapport, escalation risk, and other adoption-critical metrics.

Results are saved to SQLite and can be turned into a Markdown playbook that ranks strategies, filters risky behavior, and highlights what actually worked.

## Why It Exists

Collection teams need to improve outcomes without experimenting on real people. This project gives you a repeatable way to test conversations across debtor archetypes, collector strategies, and model providers while keeping the data fully synthetic.

Use it to answer questions like:

- Which strategy works best for hardship profiles?
- Which approaches trigger compliance risk?
- Which model is better at role-playing debtors versus judging outcomes?
- What transcripts should become training examples?
- How do strategy changes affect payment probability and debtor satisfaction?

## Current Status

The project is usable in two modes:

- **Offline mode**: deterministic local backends for demos, development, and CI.
- **Live mode**: NVIDIA NIM conversation models plus Cursor SDK judge/conversation models.

The live path has been validated end-to-end with:

- `nim-mistral-large-3-675b` as the conversation model.
- `cursor-claude-4.6-opus-high-thinking` as the judge model.
- A full `collection-swarm simulate ... --no-save` run completing successfully with parsed judgment output.

## Quick Start

### 1. Install

Requires Python 3.12+.

```bash
pip install -e ".[dev]"
```

### 2. Run Offline

No API keys are required for the default deterministic path.

```bash
collection-swarm list-profiles
collection-swarm list-strategies

collection-swarm simulate \
  --profile cooperative_hardship \
  --strategy empathetic_payment_plan
```

You should see a transcript and a judgment table printed in the terminal.

### 3. Run Live Models

For live models, create a `.env` file in the repo root:

```bash
NVIDIA_NIM_API_KEY=your_nvidia_key
CURSOR_API_KEY=your_cursor_key
```

Install the Cursor SDK bridge:

```bash
cd cursor_sdk_bridge
npm install
cd ..
```

Then run a live simulation:

```bash
collection-swarm simulate \
  --profile cooperative_hardship \
  --strategy empathetic_payment_plan \
  --conversation-model nim-mistral-large-3-675b \
  --judge-model cursor-claude-4.6-opus-high-thinking \
  --no-save
```

Remove `--no-save` when you want the result stored in SQLite.

## What You Get

Each simulation produces:

- A full collector/debtor transcript.
- Termination metadata: who ended the conversation and how many turns it took.
- A structured judgment:
  - `payment_outcome`
  - `payment_probability`
  - `debtor_satisfaction`
  - `compliance_score`
  - `conversation_efficiency`
  - `rapport_built`
  - `escalation_risk`
  - `constraint_violations`
- Token and cost metadata where providers expose it.

By default, saved runs go to:

```text
output/collection_swarm.sqlite
```

## Core Workflow

### Explore Inputs

```bash
collection-swarm list-profiles
collection-swarm list-strategies
```

Included debtor profiles:

- `cooperative_hardship`: anxious medical-debt profile with a strict `$150/month` maximum.
- `written_proof_disputer`: guarded credit-card profile that requires written proof first.
- `hostile_avoidant`: angry utility-debt profile that reacts poorly to pressure.

Included collector strategies:

- `empathetic_payment_plan`
- `assertive_settlement`
- `neutral_reminder`
- `problem_solving_callback`

### Run One Simulation

```bash
collection-swarm simulate \
  --profile written_proof_disputer \
  --strategy problem_solving_callback \
  --conversation-model cursor-gpt-5.5-medium \
  --judge-model cursor-claude-4.6-opus-high-thinking
```

### Run a Matrix

```bash
collection-swarm run \
  --profiles cooperative_hardship,written_proof_disputer \
  --strategies empathetic_payment_plan,problem_solving_callback \
  --conversation-models nim-mistral-large-3-675b,cursor-gpt-5.5-medium \
  --judge-models cursor-claude-4.6-opus-high-thinking,cursor-claude-opus-4-7-thinking-high \
  --reps 2 \
  --concurrency 2
```

### Generate a Playbook

```bash
collection-swarm analyze --output output/playbook.md
```

The playbook summarizes strategy performance and excludes risky combinations using the configured compliance thresholds.

## Model Configuration

Models live in `config/models.yaml`. The user-facing `id` is what you pass to the CLI. The provider-facing `model_name` is the exact string sent to the backend.

Current live conversation models:

- `cursor-composer-2` -> Cursor SDK `composer-2`
- `cursor-gpt-5.5-medium` -> Cursor SDK `gpt-5.5-medium`
- `cursor-gpt-5.4-high` -> Cursor SDK `gpt-5.4-high`
- `cursor-gpt-5.4-high-fast` -> Cursor SDK `gpt-5.4-high-fast`
- `cursor-gpt-5.3-codex-high` -> Cursor SDK `gpt-5.3-codex-high`
- `cursor-gpt-5.3-codex-high-fast` -> Cursor SDK `gpt-5.3-codex-high-fast`
- `nim-mistral-large-3-675b` -> NVIDIA NIM `mistralai/mistral-large-3-675b-instruct-2512`
- `nim-llama-4-maverick` -> NVIDIA NIM `meta/llama-4-maverick-17b-128e-instruct`
- `nim-minimax-m2.7` -> NVIDIA NIM `minimaxai/minimax-m2.7`

Current live judge models:

- `cursor-claude-4.6-opus-high-thinking` -> Cursor SDK `claude-4.6-opus-high-thinking`
- `cursor-claude-4.6-opus-high-thinking-fast` -> Cursor SDK `claude-4.6-opus-high-thinking-fast`
- `cursor-claude-opus-4-7-thinking-high` -> Cursor SDK `claude-opus-4-7-thinking-high`

Local defaults:

- `local-scripted`: deterministic conversation backend for offline runs.
- `local-judge`: deterministic heuristic judge for offline runs.

## Live Backend Setup

### NVIDIA NIM

The NIM backend uses LiteLLM against:

```text
https://integrate.api.nvidia.com/v1
```

Set:

```bash
NVIDIA_NIM_API_KEY=...
```

NIM model names in `config/models.yaml` use LiteLLM's OpenAI-compatible prefix, for example:

```yaml
model_name: openai/mistralai/mistral-large-3-675b-instruct-2512
```

### Cursor SDK

The Cursor backend uses the official `[@cursor/sdk](https://github.com/cursor/cookbook)` through the local Node bridge in `cursor_sdk_bridge/`.

Requirements:

- Node.js 22+
- `CURSOR_API_KEY`
- `npm install` run inside `cursor_sdk_bridge/`

Optional:

```bash
CURSOR_SDK_WORKSPACE=C:\path\to\workspace
```

If `CURSOR_SDK_WORKSPACE` is not set, the backend uses the current working directory.

## Configuration Files

```text
config/
  collector_strategies.yaml  # Strategy definitions for Collector behavior
  debtor_profiles.yaml       # Synthetic debtor profiles, constraints, objections
  models.yaml                # Local, NIM, and Cursor SDK model routing
  simulation.yaml            # Turn limits, repetitions, compliance thresholds
```

The most important design choice is that debtor profiles include machine-readable constraints. For example, `cooperative_hardship` will never agree above `$150/month`; the Judge verifies that constraint deterministically in addition to LLM scoring.

## Architecture

```text
Profiles + Strategies + Models
          |
          v
SimulationEngine
          |
          +--> CollectorAgent ----+
          |                       |
          +--> DebtorAgent -------+--> LLMRouter --> scripted / heuristic / NIM / Cursor SDK
          |                       |
          +--> Judge -------------+
          |
          v
SimulationResult --> SQLite Store --> Analysis --> Playbook
```

Key modules:

- `src/collection_swarm/engine.py`: conversation loop, turn limit, end-signal parsing, stalemate detection.
- `src/collection_swarm/agents/`: collector, debtor, and judge prompt logic.
- `src/collection_swarm/backends/`: model backend implementations and router.
- `src/collection_swarm/store.py`: SQLite persistence.
- `src/collection_swarm/analysis/`: compliance filters, statistics, and playbook generation.

## Development

Run the full test suite:

```bash
pytest -q
```

The tests cover:

- config loading
- domain model validation
- conversation engine behavior
- router/backend wiring
- judge parsing and constraint checks
- storage
- runner matrix generation
- playbook generation

Current expected result:

```text
21 passed
```

## Troubleshooting

### `CURSOR_API_KEY is required`

Add `CURSOR_API_KEY` to `.env` or export it in your shell. The backends automatically load `.env` from the repo root without overriding already-exported environment variables.

### `NVIDIA_NIM_API_KEY is required`

Add `NVIDIA_NIM_API_KEY` to `.env` or export it in your shell.

### Cursor SDK calls fail immediately

Check:

- Node.js is version 22 or newer.
- `npm install` has been run inside `cursor_sdk_bridge/`.
- `CURSOR_API_KEY` is valid.
- The `model_name` exists in Cursor SDK's model list.

### NIM returns 404

The NIM model string is probably stale. Query NVIDIA's `/v1/models` endpoint and update `config/models.yaml`. The current checked strings are listed in the Model Configuration section above.

### Live simulations are slow

Live runs make multiple model calls: collector turns, debtor turns, and a judge call. Cursor SDK calls can take longer than NIM calls. Use lower `--reps`, lower `--concurrency`, or the local scripted models while iterating.

## Data And Safety

Collection Swarm is for synthetic testing only.

- Do not use real consumer data in profiles or transcripts.
- Do not treat Judge output as legal advice.
- Keep compliance guardrails in collector strategies.
- Review generated playbooks before using them for policy or training decisions.
- Confirm applicable debt-collection law and internal policy with qualified counsel.

## Repository Hygiene

Generated and local-only files are intentionally ignored:

- `.env`
- `output/`
- SQLite databases
- Python build artifacts
- `cursor_sdk_bridge/node_modules/`

Commit config, code, tests, and docs. Do not commit API keys or generated local databases.
