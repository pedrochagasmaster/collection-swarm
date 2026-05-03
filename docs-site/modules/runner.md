# Runner

> **Module:** `collection_swarm.runner`
> **Source:** `src/collection_swarm/runner.py`

The runner module provides high-level orchestration for executing simulations at
scale. It offers three tiers of execution — **matrix runs** for exhaustive
parameter sweeps, **tournaments** for competitive Elo-rated matchups, and
**evolution cycles** for multi-generation strategy optimization.

---

## Overview

```
build_matrix()          → list[MatrixCell]
        │
        ▼
run_matrix()            → RunSummary
        │
        ▼
run_tournament()        → TournamentResult     (Swiss / Round-Robin)
        │
        ▼
run_evolution_cycle()   → list[TournamentResult] (multi-generation loop)
```

---

## `RunSummary`

A frozen dataclass returned by `run_matrix` that summarizes batch execution
results.

```python
@dataclass(frozen=True)
class RunSummary:
    completed: int
    failed: int
    total: int
    results: list[SimulationResult]
```

| Field | Type | Description |
|-------|------|-------------|
| `completed` | `int` | Number of simulations that finished with `status == "completed"`. |
| `failed` | `int` | Number of simulations that finished with a non-completed status. |
| `total` | `int` | Total number of simulations executed (`completed + failed`). |
| `results` | `list[SimulationResult]` | The full list of result objects for further inspection. |

---

## `build_matrix`

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

Generates the Cartesian product of all parameter dimensions into a list of
`MatrixCell` objects, each representing one simulation to execute.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | `AppConfig` | *required* | The loaded application configuration. Used to resolve defaults and validate IDs. |
| `profile_ids` | `list[str]` or `None` | `None` | Debtor profile IDs to include. Defaults to **all** profiles in the config. |
| `strategy_ids` | `list[str]` or `None` | `None` | Collector strategy IDs to include. Defaults to **all** strategies in the config. |
| `conversation_models` | `list[str]` or `None` | `None` | Model IDs for the collector/debtor agents. Defaults to `[config.default_conversation_model]`. |
| `judge_models` | `list[str]` or `None` | `None` | Model IDs for the judge. Defaults to `[config.default_judge_model]`. |
| `reps` | `int` | `1` | Number of repetitions per unique combination. Useful for statistical significance. |

**Returns:** `list[MatrixCell]` — one entry per simulation to run.

### Validation

Each ID is validated against the config during matrix construction. If a
profile, strategy, or model ID does not exist, a `KeyError` is raised before
any simulation starts.

### Example

```python
from collection_swarm.config import load_app_config
from collection_swarm.runner import build_matrix

config = load_app_config("config")

# Full matrix: all profiles × all strategies × default models × 3 reps
cells = build_matrix(config, reps=3)
print(f"Total simulations to run: {len(cells)}")

# Targeted matrix: specific profiles and strategies
cells = build_matrix(
    config,
    profile_ids=["struggling_single_parent", "dispute_debtor"],
    strategy_ids=["empathetic_negotiator"],
    conversation_models=["gpt-4o", "claude-sonnet"],
    reps=5,
)
```

---

## `run_matrix`

```python
async def run_matrix(
    config: AppConfig,
    store: SimulationStore,
    cells: list[MatrixCell],
    concurrency: int = 2,
) -> RunSummary
```

Executes all cells concurrently (bounded by a semaphore) and persists the
results to the store.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | `AppConfig` | *required* | Application configuration. |
| `store` | `SimulationStore` | *required* | SQLite store for persisting results. |
| `cells` | `list[MatrixCell]` | *required* | The cells to execute (typically from `build_matrix`). |
| `concurrency` | `int` | `2` | Maximum number of simulations running in parallel. |

**Returns:** `RunSummary`

### Execution Details

1. Creates an `LLMRouter` from the model configuration.
2. Creates an `asyncio.Semaphore(concurrency)` to limit parallelism.
3. For each cell, constructs a fresh `SimulationEngine` with agents and settings
   from the config.
4. Runs all cells concurrently via `asyncio.gather`.
5. Persists all results in a single `store.save_runs()` call.
6. Returns a `RunSummary` with completed/failed counts.

### Example

```python
import asyncio
from collection_swarm.config import load_app_config
from collection_swarm.runner import build_matrix, run_matrix
from collection_swarm.store import SimulationStore

async def main():
    config = load_app_config("config")
    store = SimulationStore("output/results.sqlite")

    cells = build_matrix(config, reps=3)
    summary = await run_matrix(config, store, cells, concurrency=4)

    print(f"Completed: {summary.completed}/{summary.total}")
    print(f"Failed:    {summary.failed}/{summary.total}")

asyncio.run(main())
```

---

## `run_tournament`

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
    on_round_complete: Callable[[TournamentResult], Awaitable[None]] | None = None,
) -> TournamentResult
```

Runs a multi-round tournament where strategies compete against debtor profiles,
updating Elo ratings after each game.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | `AppConfig` | *required* | Application configuration. |
| `store` | `SimulationStore` | *required* | Persistence layer. |
| `tournament_config` | `TournamentConfig` | *required* | Tournament settings (format, rounds, scoring, K-factors). |
| `profile_ids` | `list[str]` or `None` | `None` | Profiles to include. Defaults to all configured profiles. |
| `strategy_ids` | `list[str]` or `None` | `None` | Strategies to include. Defaults to all configured strategies. |
| `conversation_model` | `str` or `None` | `None` | Model for collector/debtor agents. Defaults to `config.default_conversation_model`. |
| `judge_model` | `str` or `None` | `None` | Model for the judge. Defaults to `config.default_judge_model`. |
| `concurrency` | `int` | `2` | Maximum parallel simulations per round. |
| `on_round_complete` | `Callable` or `None` | `None` | Async callback invoked at the end of each round with the updated `TournamentResult`. |

**Returns:** `TournamentResult`

### Tournament Formats

| Format | Description |
|--------|-------------|
| `"round_robin"` | Every strategy is paired against every profile in each round. Exhaustive but expensive. |
| `"swiss"` | Strategies are paired against profiles of similar Elo rating. Efficient convergence with fewer rounds. |

### Round Flow

```
for each round (1 → tournament_config.rounds):
    1. Fetch current Elo ratings for all strategies and profiles
    2. Generate pairings (round_robin or swiss)
    3. Expand pairings by reps_per_pairing
    4. Run all games concurrently (bounded by semaphore)
    5. Persist simulation results
    6. For each completed game with a judgment:
       a. Fetch current Elo ratings for the strategy and profile
       b. Compute Elo updates via arena.update_ratings()
       c. Persist Elo updates (linked to tournament ID)
    7. Update tournament metadata (rounds_completed, total_games, cost)
    8. Invoke on_round_complete callback (if provided)

After all rounds:
    • Set completed_at timestamp
    • Persist final TournamentResult
```

### Strategy + Profile Pools

The tournament merges **config-defined** entities with **evolved** entities from
the store. This allows evolved strategies and hardened profiles to compete
alongside seed configurations.

```python
strategy_pool = {**config.strategies, **store.get_evolved_strategy_pool()}
profile_pool = {**config.profiles, **store.get_evolved_profile_pool()}
```

### Example

```python
import asyncio
from collection_swarm.config import load_app_config
from collection_swarm.models import TournamentConfig
from collection_swarm.runner import run_tournament
from collection_swarm.store import SimulationStore

async def main():
    config = load_app_config("config")
    store = SimulationStore("output/results.sqlite")

    tournament = await run_tournament(
        config,
        store,
        TournamentConfig(
            format="swiss",
            rounds=6,
            reps_per_pairing=2,
            scoring="payment_x_compliance",
        ),
        concurrency=4,
    )

    print(f"Rounds:     {tournament.rounds_completed}")
    print(f"Games:      {tournament.total_games}")
    print(f"Total cost: ${tournament.total_cost_usd:.2f}")

asyncio.run(main())
```

---

## `run_evolution_cycle`

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
    on_generation_complete: Callable[[int, TournamentResult], Awaitable[None]] | None = None,
) -> list[TournamentResult]
```

Runs a multi-generation evolutionary loop that alternates between tournament
play, strategy evolution, culling, and optional profile hardening.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | `AppConfig` | *required* | Application configuration. |
| `store` | `SimulationStore` | *required* | Persistence layer. |
| `evolution_config` | `EvolutionConfig` | *required* | Controls population size, selection counts, mutation/crossover rates. |
| `tournament_config` | `TournamentConfig` | *required* | Configuration for each generation's tournament. |
| `generations` | `int` | `5` | Number of evolutionary generations to run. |
| `profile_ids` | `list[str]` or `None` | `None` | Starting profile pool. |
| `strategy_ids` | `list[str]` or `None` | `None` | Starting strategy pool. |
| `hardening_config` | `HardeningConfig` or `None` | `None` | If provided and `enabled=True`, profiles are hardened each generation. |
| `conversation_model` | `str` or `None` | `None` | Model for agents. |
| `judge_model` | `str` or `None` | `None` | Model for judge. |
| `concurrency` | `int` | `2` | Maximum parallel simulations. |
| `on_generation_complete` | `Callable` or `None` | `None` | Async callback invoked after each generation with `(generation_number, tournament_result)`. |

**Returns:** `list[TournamentResult]` — one result per generation.

### Generation Loop

```
for each generation (1 → generations):

    ┌─ 1. Tournament ────────────────────────────────┐
    │  Run a full tournament with the active pools.   │
    │  Produces Elo ratings for all participants.     │
    └─────────────────────────────────────────────────┘
                    │
    ┌─ 2. Evolve Strategies ─────────────────────────┐
    │  Sort strategies by Elo rating.                 │
    │  Select top_k performers and bottom_k laggards. │
    │  Feed failure transcripts from bottom strategies │
    │  to evolve_strategies() for LLM-based mutation. │
    │  Save evolved strategies with lineage metadata. │
    │  Add new strategy IDs to the active pool.       │
    └─────────────────────────────────────────────────┘
                    │
    ┌─ 3. Cull (optional) ───────────────────────────┐
    │  If cull_bottom_n > 0:                          │
    │    Use cull_strategies() to remove the weakest  │
    │    evolved strategies, respecting population_    │
    │    size. Seed strategies are never culled.       │
    │    Culled strategies are marked in the store     │
    │    and removed from the active pool.             │
    └─────────────────────────────────────────────────┘
                    │
    ┌─ 4. Harden Profiles (optional) ────────────────┐
    │  If hardening_config.enabled:                   │
    │    Generate harder debtor profiles from the     │
    │    bottom-performing seed profiles.              │
    │    Save with ProfileLineage metadata.            │
    │    Add new profile IDs to the active pool.       │
    └─────────────────────────────────────────────────┘
                    │
    ┌─ 5. Callback ──────────────────────────────────┐
    │  Invoke on_generation_complete(gen, tournament). │
    └─────────────────────────────────────────────────┘
```

### Lineage Tracking

Every evolved strategy and hardened profile is saved with lineage metadata:

**StrategyLineage:**
- `parent_ids` — IDs of the top-performing strategies used as parents.
- `generation` — The generation number when the strategy was created.
- `mutation_type` — Always `"llm"` for LLM-generated mutations.
- `mutation_description` — Human-readable description of the mutation.

**ProfileLineage:**
- `parent_id` — ID of the seed profile used as the basis.
- `generation` — The generation number.
- `hardening_type` — Always `"llm"` for LLM-generated hardening.

### Example

```python
import asyncio
from collection_swarm.config import load_app_config
from collection_swarm.models import EvolutionConfig, HardeningConfig, TournamentConfig
from collection_swarm.runner import run_evolution_cycle
from collection_swarm.store import SimulationStore

async def main():
    config = load_app_config("config")
    store = SimulationStore("output/results.sqlite")

    results = await run_evolution_cycle(
        config,
        store,
        evolution_config=EvolutionConfig(
            population_size=20,
            top_k=3,
            bottom_k=3,
            cull_bottom_n=3,
            mutation_rate=0.5,
            crossover_rate=0.3,
        ),
        tournament_config=TournamentConfig(
            format="swiss",
            rounds=4,
            reps_per_pairing=2,
        ),
        hardening_config=HardeningConfig(enabled=True),
        generations=5,
        concurrency=4,
    )

    for i, tournament in enumerate(results, 1):
        print(f"Gen {i}: {tournament.total_games} games, "
              f"${tournament.total_cost_usd:.2f}")

asyncio.run(main())
```

---

## Concurrency Model

All runner functions use `asyncio.Semaphore` to limit the number of
simultaneous LLM calls. This prevents rate-limit errors and controls cost:

```python
semaphore = asyncio.Semaphore(concurrency)

async def run_cell(cell: MatrixCell) -> SimulationResult:
    async with semaphore:
        engine = SimulationEngine(...)
        return await engine.run_simulation(...)

results = await asyncio.gather(*(run_cell(c) for c in cells))
```

!!! tip "Choosing concurrency"
    Start with `concurrency=2` for development and increase to 4–8 for
    production runs. Higher values speed up execution but may hit API rate
    limits depending on your LLM provider.
