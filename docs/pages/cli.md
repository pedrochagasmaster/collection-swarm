---
title: CLI Reference
layout: default
nav_order: 18
---

# CLI Reference
{: .no_toc }

Complete command-line interface documentation.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Source:** `src/collection_swarm/cli.py`

**Entry point:** `collection-swarm` (installed via `pyproject.toml`)

## Global Options

| Option | Default | Description |
|:-------|:--------|:------------|
| `--config-dir` | `config` | Path to configuration directory |
| `--db` | `output/collection_swarm.sqlite` | Path to SQLite database |

---

## Commands

### `simulate`

Run a single simulation and print the transcript and judgment.

```bash
collection-swarm simulate \
  --profile cooperative_hardship \
  --strategy empathetic_payment_plan \
  [--conversation-model nim-mistral-large-3-675b] \
  [--judge-model cursor-claude-4.6-opus-high-thinking] \
  [--no-save]
```

| Option | Required | Description |
|:-------|:---------|:------------|
| `--profile` | Yes | Profile ID to simulate |
| `--strategy` | Yes | Strategy ID to simulate |
| `--conversation-model` | No | Model for collector and debtor (default: first scripted) |
| `--judge-model` | No | Model for the judge (default: first heuristic/scripted) |
| `--no-save` | No | Print only; do not persist to database |

### `run`

Run a matrix of simulations across all combinations of specified parameters.

```bash
collection-swarm run \
  [--profiles cooperative_hardship,written_proof_disputer] \
  [--strategies empathetic_payment_plan,assertive_settlement] \
  [--conversation-models nim-mistral-large-3-675b] \
  [--judge-models cursor-claude-4.6-opus-high-thinking] \
  [--reps 2] \
  [--concurrency 2]
```

| Option | Default | Description |
|:-------|:--------|:------------|
| `--profiles` | All | Comma-separated profile IDs |
| `--strategies` | All | Comma-separated strategy IDs |
| `--conversation-models` | Default model | Comma-separated model IDs |
| `--judge-models` | Default judge | Comma-separated model IDs |
| `--reps` | Config default (1) | Repetitions per matrix cell |
| `--concurrency` | 2 | Max concurrent simulations |

### `tournament`

Run an Elo-rated tournament between strategies and profiles.

```bash
collection-swarm tournament \
  [--format swiss|round_robin] \
  [--rounds 4] \
  [--profiles ...] \
  [--strategies ...] \
  [--conversation-model ...] \
  [--judge-model ...] \
  [--concurrency 2]
```

| Option | Default | Description |
|:-------|:--------|:------------|
| `--format` | Config default (swiss) | Tournament pairing format |
| `--rounds` | Config default (4) | Number of tournament rounds |
| `--profiles` | All | Comma-separated profile IDs |
| `--strategies` | All | Comma-separated strategy IDs |
| `--conversation-model` | Default | Single model for conversations |
| `--judge-model` | Default | Single model for judging |
| `--concurrency` | 2 | Max concurrent simulations |

### `leaderboard`

Display current Elo rankings.

```bash
collection-swarm leaderboard [--type strategy|profile|all]
```

### `reset-elo`

Reset all Elo ratings and history.

```bash
collection-swarm reset-elo
```

### `evolve`

Run tournament-driven strategy evolution.

```bash
collection-swarm evolve \
  [--generations 5] \
  [--population-size 20] \
  [--evolver-model ...] \
  [--tournament-rounds 4] \
  [--profiles ...] \
  [--strategies ...] \
  [--concurrency 2]
```

| Option | Default | Description |
|:-------|:--------|:------------|
| `--generations` | 5 | Number of evolution cycles |
| `--population-size` | 20 | Max active strategies |
| `--evolver-model` | Default conversation model | Model for strategy generation |
| `--tournament-rounds` | 4 | Rounds per tournament |

### `calibrate`

Evaluate judge accuracy against human labels.

```bash
collection-swarm calibrate \
  --labels calibration_labels.json \
  [--optimize]
```

| Option | Required | Description |
|:-------|:---------|:------------|
| `--labels` | Yes | Path to calibration labels JSON file |
| `--optimize` | No | Save the current judge prompt as a scored variant |

### `analyze`

Generate a Markdown playbook from completed simulations.

```bash
collection-swarm analyze [--output output/playbook.md]
```

### `model-report`

Generate a model-role evaluation report.

```bash
collection-swarm model-report \
  [--output docs/cursor-model-role-report.md] \
  [--format markdown|json] \
  [--live-probes] \
  [--cursor-models gpt-5.5,claude-opus-4-7] \
  [--roles collector,debtor,judge] \
  [--profile cooperative_hardship] \
  [--strategy empathetic_payment_plan] \
  [--judge-profile written_proof_disputer] \
  [--concurrency 1]
```

### `list-profiles`

List all configured debtor profiles as a formatted table.

```bash
collection-swarm list-profiles
```

### `list-strategies`

List all configured collector strategies as a formatted table.

```bash
collection-swarm list-strategies
```

### `test-connection`

Verify the default model backend is reachable.

```bash
collection-swarm test-connection
```

### `serve`

Launch the web dashboard.

```bash
collection-swarm serve [--host 127.0.0.1] [--port 8000]
```

### `seed`

Generate realistic demo data for the dashboard.

```bash
collection-swarm seed [--count 24]
```
