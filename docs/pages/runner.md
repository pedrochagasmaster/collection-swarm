---
title: Runner & Orchestration
layout: default
nav_order: 16
---

# Runner & Orchestration
{: .no_toc }

Matrix runs, tournament orchestration, and multi-generation evolution cycles.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Source:** `src/collection_swarm/runner.py`

## Overview

The runner module orchestrates large-scale simulation campaigns. It provides three levels of execution:

1. **Matrix runs** — sweep all combinations of profiles × strategies × models.
2. **Tournaments** — Elo-rated competitions with configurable pairing.
3. **Evolution cycles** — multi-generation strategy evolution with optional profile hardening.

All execution uses `asyncio.gather()` with configurable concurrency via semaphores.

## Matrix Runs

### build_matrix

```python
def build_matrix(
    config: AppConfig,
    profile_ids: list[str] | None = None,
    strategy_ids: list[str] | None = None,
    conversation_models: list[str] | None = None,
    judge_models: list[str] | None = None,
    reps: int = 1,
) -> list[MatrixCell]
```

Builds a list of `MatrixCell` objects for every combination:

```
cells = profiles × strategies × conversation_models × judge_models × reps
```

Defaults to all configured profiles, strategies, and the default models when parameters are `None`. Validates all IDs against the config.

### run_matrix

```python
async def run_matrix(
    config: AppConfig,
    store: SimulationStore,
    cells: list[MatrixCell],
    concurrency: int = 2,
) -> RunSummary
```

1. Creates a shared `LLMRouter`.
2. Uses an `asyncio.Semaphore` to limit concurrent simulations.
3. For each cell, constructs a `SimulationEngine` with the appropriate agents and settings.
4. Runs all cells concurrently via `asyncio.gather()`.
5. Batch-saves all results to the store.
6. Returns a `RunSummary` with completed/failed counts.

### RunSummary

```python
@dataclass(frozen=True)
class RunSummary:
    completed: int
    failed: int
    total: int
    results: list[SimulationResult]
```

## Tournament Execution

### run_tournament

```python
async def run_tournament(
    config: AppConfig,
    store: SimulationStore,
    tournament_config: TournamentConfig,
    profile_ids: list[str] | None = None,
    strategy_ids: list[str] | None = None,
    conversation_model: str | None = None,
    judge_model: str | None = None,
    concurrency: int = 2,
    on_round_complete: Callable | None = None,
) -> TournamentResult
```

**Tournament lifecycle:**

1. **Initialize** — resolve models, load strategy/profile pools (including evolved entities), create router.
2. **For each round:**
   - Get current Elo ratings for all strategies and profiles.
   - Generate pairings using the configured format (Swiss or round-robin).
   - Run all pairings as simulations with concurrency limits.
   - Save simulation results.
   - Update Elo ratings for each completed simulation.
   - Track matchup history to avoid repeats in Swiss mode.
   - Invoke the `on_round_complete` callback if provided.
3. **Finalize** — record completion time and save the tournament result.

### Strategy and Profile Pools

Tournaments operate on **merged pools** that include both configured and evolved entities:

```python
strategy_pool = {**config.strategies, **store.get_evolved_strategy_pool()}
profile_pool = {**config.profiles, **store.get_evolved_profile_pool()}
```

This means evolved strategies and hardened profiles compete alongside seed entities.

## Evolution Cycles

### run_evolution_cycle

```python
async def run_evolution_cycle(
    config: AppConfig,
    store: SimulationStore,
    evolution_config: EvolutionConfig,
    tournament_config: TournamentConfig,
    generations: int = 5,
    profile_ids: list[str] | None = None,
    strategy_ids: list[str] | None = None,
    hardening_config: HardeningConfig | None = None,
    conversation_model: str | None = None,
    judge_model: str | None = None,
    concurrency: int = 2,
    on_generation_complete: Callable | None = None,
) -> list[TournamentResult]
```

**Per-generation lifecycle:**

1. **Tournament** — run a full tournament with the current strategy/profile pool.
2. **Ranking** — sort strategies by Elo rating.
3. **Selection** — pick top-k winners and bottom-k losers.
4. **Transcript collection** — gather failure transcripts from bottom-k strategies.
5. **Evolution** — call `evolve_strategies()` with parents and failure examples.
6. **Integration** — save evolved strategies with lineage tracking, add to active pool.
7. **Culling** — if `cull_bottom_n > 0`, remove underperformers while protecting seed strategies.
8. **Hardening** (optional) — generate tougher profiles and add to the pool.
9. **Callback** — notify generation completion.

### Pool Management

The runner maintains active lists (`active_strategy_ids`, `active_profile_ids`) that grow as new entities are evolved and shrink as underperformers are culled:

```python
for strategy in evolved:
    store.save_evolved_strategy(strategy, lineage)
    if strategy.id not in active_strategy_ids:
        active_strategy_ids.append(strategy.id)
```

Culled strategies are removed from the active list and marked in the database:

```python
store.cull_evolved_strategy(strategy.id)
if strategy.id in active_strategy_ids:
    active_strategy_ids.remove(strategy.id)
```

## Concurrency Model

All runner functions use an `asyncio.Semaphore` to control parallelism:

```python
semaphore = asyncio.Semaphore(concurrency)

async def run_cell(cell: MatrixCell) -> SimulationResult:
    async with semaphore:
        # Build engine and run simulation
```

The default concurrency of 2 is conservative for live model calls. Increase for scripted backends; keep low for expensive API calls.
