# SimulationStore

> **Module:** `collection_swarm.store`
> **Source:** `src/collection_swarm/store.py`

`SimulationStore` is the persistence layer for Collection Swarm. It uses a
single SQLite database to store simulation results, Elo ratings, tournament
records, evolved strategies/profiles, calibration labels, and judge prompt
variants.

---

## Overview

```python
from collection_swarm.store import SimulationStore

store = SimulationStore("output/collection_swarm.sqlite")
```

The constructor accepts a `Path` or `str` to the database file. Parent
directories are created automatically. On initialization, the store runs
`_init_schema()` to create all tables if they don't already exist and applies
any necessary schema migrations (adding columns to existing tables).

---

## Database Schema

### `runs`

Stores individual simulation results.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `TEXT PK` | Unique simulation ID (e.g., `sim_a1b2c3d4e5f6`). |
| `status` | `TEXT` | `"completed"`, `"failed"`, or `"running"`. |
| `error_message` | `TEXT` | Error message if status is `"failed"`. |
| `profile_id` | `TEXT` | Debtor profile used in this simulation. |
| `strategy_id` | `TEXT` | Collector strategy used. |
| `conversation_model` | `TEXT` | LLM model for collector/debtor agents. |
| `judge_model` | `TEXT` | LLM model for the judge. |
| `started_at` | `TEXT` | ISO 8601 timestamp. |
| `ended_at` | `TEXT` | ISO 8601 timestamp (null if still running). |
| `turn_count` | `INTEGER` | Number of messages in the transcript. |
| `ended_by` | `TEXT` | One of `collector`, `debtor`, `stalemate`, `turn_limit`. |
| `transcript_json` | `TEXT` | JSON array of `{role, content}` message objects. |
| `judge_reasoning` | `TEXT` | Free-text reasoning from the judge. |
| `payment_outcome` | `TEXT` | Enum value from `PaymentOutcome`. |
| `payment_probability` | `REAL` | 0.0–1.0 likelihood of payment. |
| `debtor_satisfaction` | `REAL` | 0.0–1.0 satisfaction score. |
| `compliance_score` | `REAL` | 0.0–1.0 regulatory compliance rating. |
| `conversation_efficiency` | `INTEGER` | Turns needed to reach resolution. |
| `rapport_built` | `REAL` | 0.0–1.0 rapport score. |
| `escalation_risk` | `REAL` | 0.0–1.0 risk of debtor escalation. |
| `end_reason` | `TEXT` | Human-readable reason for conversation end. |
| `constraint_violations_json` | `TEXT` | JSON array of violated constraint descriptions. |
| `total_input_tokens` | `INTEGER` | Cumulative input tokens across all LLM calls. |
| `total_output_tokens` | `INTEGER` | Cumulative output tokens. |
| `estimated_cost_usd` | `REAL` | Estimated dollar cost. |

### `elo_ratings`

Current Elo ratings for strategies and profiles, scoped by model pair.

| Column | Type | Description |
|--------|------|-------------|
| `entity_type` | `TEXT` | `"strategy"` or `"profile"`. |
| `entity_id` | `TEXT` | The strategy or profile ID. |
| `conversation_model` | `TEXT` | Conversation model scope. |
| `judge_model` | `TEXT` | Judge model scope. |
| `rating` | `REAL` | Current Elo rating (default 1500). |
| `games_played` | `INTEGER` | Total games played. |
| `wins` | `INTEGER` | Win count. |
| `losses` | `INTEGER` | Loss count. |
| `draws` | `INTEGER` | Draw count. |
| `updated_at` | `TEXT` | Last update timestamp. |

**Primary key:** `(entity_type, entity_id, conversation_model, judge_model)`

### `elo_history`

Audit log of every Elo rating change.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `INTEGER PK` | Auto-incrementing row ID. |
| `tournament_id` | `TEXT` | Optional link to a tournament. |
| `entity_type` | `TEXT` | `"strategy"` or `"profile"`. |
| `entity_id` | `TEXT` | The entity whose rating changed. |
| `opponent_id` | `TEXT` | The opponent in this game. |
| `conversation_model` | `TEXT` | Conversation model scope. |
| `judge_model` | `TEXT` | Judge model scope. |
| `simulation_id` | `TEXT` | The simulation that produced this update. |
| `rating_before` | `REAL` | Rating before the game. |
| `rating_after` | `REAL` | Rating after the game. |
| `effective_score` | `REAL` | Actual score achieved (0.0–1.0). |
| `expected_score` | `REAL` | Expected score based on rating difference. |
| `timestamp` | `TEXT` | When the update occurred. |

### `tournaments`

Tournament metadata and results.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `TEXT PK` | Tournament ID (e.g., `tourn_a1b2c3d4e5`). |
| `config_json` | `TEXT` | Serialized `TournamentConfig`. |
| `rounds_completed` | `INTEGER` | Number of rounds played. |
| `total_games` | `INTEGER` | Total simulations run. |
| `started_at` | `TEXT` | Start timestamp. |
| `completed_at` | `TEXT` | Completion timestamp. |
| `total_cost_usd` | `REAL` | Aggregate cost. |

### `evolved_strategies`

Strategies created by the evolution system.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `TEXT PK` | Strategy ID. |
| `generation` | `INTEGER` | Generation number (0 = seed). |
| `parent_ids_json` | `TEXT` | JSON array of parent strategy IDs. |
| `mutation_type` | `TEXT` | How the strategy was created (e.g., `"llm"`). |
| `mutation_description` | `TEXT` | Human-readable description. |
| `strategy_json` | `TEXT` | Full serialized `Strategy` object. |
| `created_at` | `TEXT` | Creation timestamp. |
| `culled_at` | `TEXT` | Culling timestamp, or `NULL` if active. |

### `evolved_profiles`

Profiles created by the adversarial hardening system.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `TEXT PK` | Profile ID. |
| `generation` | `INTEGER` | Generation number. |
| `parent_id` | `TEXT` | Parent profile ID. |
| `hardening_type` | `TEXT` | How the profile was hardened. |
| `hardening_description` | `TEXT` | Description. |
| `profile_json` | `TEXT` | Full serialized `Profile` object. |
| `created_at` | `TEXT` | Creation timestamp. |
| `culled_at` | `TEXT` | Culling timestamp, or `NULL` if active. |

### `calibration_labels`

Human-annotated scores for judge calibration.

| Column | Type | Description |
|--------|------|-------------|
| `transcript_id` | `TEXT` | The simulation ID being labeled. |
| `metric` | `TEXT` | Which metric is being scored (e.g., `"compliance_score"`). |
| `human_score` | `REAL` | The human-assigned score. |
| `labeler_id` | `TEXT` | Who provided the label. |
| `labeled_at` | `TEXT` | When the label was recorded. |

**Primary key:** `(transcript_id, metric, labeler_id)`

### `judge_prompt_variants`

Experimental judge prompt versions for A/B testing.

| Column | Type | Description |
|--------|------|-------------|
| `id` | `TEXT PK` | Auto-generated variant ID. |
| `system_prompt` | `TEXT` | The system prompt text. |
| `transcript_prompt` | `TEXT` | The transcript evaluation prompt. |
| `calibration_score` | `REAL` | Correlation with human labels (if measured). |
| `created_at` | `TEXT` | Creation timestamp. |

---

## CRUD Operations

### `save_run` / `save_runs`

```python
store.save_run(result)           # single result
store.save_runs([r1, r2, r3])    # batch insert
```

Persists one or more `SimulationResult` objects using `INSERT OR REPLACE`.
Judgment fields are flattened into individual columns. The transcript is
serialized as a JSON array.

### `get_run`

```python
result = store.get_run("sim_a1b2c3d4e5f6")
```

Retrieves a single `SimulationResult` by ID. Raises `KeyError` if not found.

### `list_runs`

```python
all_completed = store.list_runs()                # status="completed" (default)
all_runs = store.list_runs(status=None)          # no filter
failed_runs = store.list_runs(status="failed")   # specific status
```

Returns a list of `SimulationResult` objects, ordered by `started_at`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | `str` or `None` | `"completed"` | Filter by status. Pass `None` for all runs. |

---

## Analytics Methods

### `get_strategy_comparison`

```python
stats = store.get_strategy_comparison("struggling_single_parent")
for s in stats:
    print(f"{s.strategy_id}: {s.mean_payment_probability:.2f}")
```

Returns a list of `StrategyStats` for all strategies tested against a given
profile, ordered by `mean_payment_probability` descending.

### `get_matrix_coverage`

```python
coverage = store.get_matrix_coverage()
for cell, count in coverage.items():
    print(f"{cell.profile_id} × {cell.strategy_id}: {count} runs")
```

Returns a dictionary mapping each `MatrixCell` (profile × strategy ×
conversation model × judge model) to the number of completed runs.

### `get_backfill_needed`

```python
cells = build_matrix(config)
needed = store.get_backfill_needed(target_reps=5, cells=cells)
print(f"{len(needed)} additional simulations needed")
```

Compares current coverage against a target repetition count and returns a list
of `MatrixCell` objects that still need to be run.

| Parameter | Type | Description |
|-----------|------|-------------|
| `target_reps` | `int` | Desired number of completed runs per cell. |
| `cells` | `list[MatrixCell]` | The full set of cells to check. |

### `get_best_transcript`

```python
messages = store.get_best_transcript("profile_1", "strategy_1")
for msg in messages:
    print(f"{msg.role}: {msg.content[:80]}...")
```

Returns the transcript from the highest-performing simulation for a given
profile/strategy pair, ranked by `payment_probability DESC, compliance_score
DESC`.

### `get_all_transcripts`

```python
transcripts = store.get_all_transcripts("profile_1", "strategy_1")
print(f"Found {len(transcripts)} transcripts")
```

Returns all transcripts for a profile/strategy pair as a list of message lists.

### `get_compliance_summary`

```python
summary = store.get_compliance_summary("profile_1", "strategy_1")
print(f"Compliance: {summary['compliance_score']:.2f}")
print(f"Escalation risk: {summary['escalation_risk']:.2f}")
```

Returns average compliance score and escalation risk for a profile/strategy pair.

### `get_cost_summary`

```python
costs = store.get_cost_summary()
print(f"Total simulations: {costs['simulations']:.0f}")
print(f"Total cost: ${costs['estimated_cost_usd']:.2f}")
```

Returns aggregate token and cost statistics across all runs.

| Key | Description |
|-----|-------------|
| `simulations` | Total number of runs. |
| `input_tokens` | Sum of all input tokens. |
| `output_tokens` | Sum of all output tokens. |
| `estimated_cost_usd` | Total estimated cost. |

### `count_by_status`

```python
counts = store.count_by_status()
# {"completed": 42, "failed": 3}
```

Returns a dictionary mapping each status to its count.

### `get_combo_runs`

```python
runs = store.get_combo_runs(
    "profile_1", "strategy_1",
    conversation_model="gpt-4o",
    judge_model="gpt-4o",
)
```

Returns completed runs for a specific profile/strategy combination, optionally
filtered by conversation and judge models. Results are ordered by
`compliance_score ASC, escalation_risk DESC, started_at DESC` (worst compliance
first — useful for identifying problem areas).

### `get_performance_by`

```python
by_strategy = store.get_performance_by("strategy_id")
for sid, metrics in by_strategy.items():
    print(f"{sid}: payment={metrics['payment_probability']:.2f}, "
          f"compliance={metrics['compliance_score']:.2f}")
```

Aggregates performance metrics by a specified dimension.

| Allowed dimensions |
|-------------------|
| `"profile_id"` |
| `"strategy_id"` |
| `"conversation_model"` |
| `"judge_model"` |

Raises `ValueError` for unsupported dimensions.

---

## Elo Rating Methods

### `get_elo_ratings`

```python
ratings = store.get_elo_ratings(
    entity_type="strategy",
    conversation_model="gpt-4o",
    judge_model="gpt-4o",
)
for r in ratings:
    print(f"{r.entity_id}: {r.rating:.0f} ({r.games_played} games)")
```

Returns all Elo ratings, optionally filtered by entity type, conversation model,
and/or judge model. Results are ordered by `rating DESC`.

### `get_elo_rating`

```python
rating = store.get_elo_rating("strategy", "empathetic_negotiator", "gpt-4o", "gpt-4o")
print(f"Rating: {rating.rating}, W/L/D: {rating.wins}/{rating.losses}/{rating.draws}")
```

Returns the Elo rating for a specific entity. If no rating exists, returns a
default `EloRating` with `rating=1500` and zero games played.

### `save_elo_update`

```python
store.save_elo_update(update, tournament_id="tourn_abc123")
```

Applies an `EloUpdate` to the ratings table:

1. Fetches the current rating for the entity.
2. Classifies the game as win/loss/draw based on `effective_score` and `DRAW_THRESHOLD` (±0.05 from 0.5).
3. Upserts the new rating, incrementing the appropriate counter.
4. Appends a record to `elo_history` for audit purposes.

### `get_elo_history`

```python
history = store.get_elo_history("empathetic_negotiator")
for h in history:
    print(f"{h.rating_before:.0f} → {h.rating_after:.0f}")
```

Returns the full Elo history for an entity, ordered chronologically.

### `reset_elo_ratings`

```python
store.reset_elo_ratings()
```

!!! warning
    Deletes **all** rows from both `elo_ratings` and `elo_history`. This is
    irreversible.

---

## Tournament Methods

### `save_tournament`

```python
store.save_tournament(tournament_result)
```

Persists a `TournamentResult` with its serialized config.

### `get_tournament`

```python
tournament = store.get_tournament("tourn_a1b2c3d4e5")
```

Retrieves a tournament by ID. Raises `KeyError` if not found.

### `list_tournaments`

```python
tournaments = store.list_tournaments()
```

Returns all tournaments ordered by `started_at DESC` (most recent first).

---

## Evolution Methods

### Strategy Evolution

```python
store.save_evolved_strategy(strategy, lineage)

strategy = store.get_evolved_strategy("evolved_strat_1")   # Strategy | None

active = store.list_evolved_strategies()                    # active only
all_ = store.list_evolved_strategies(include_culled=True)   # including culled
# Returns list[tuple[Strategy, StrategyLineage]]

store.cull_evolved_strategy("evolved_strat_1")              # marks as culled

pool = store.get_evolved_strategy_pool()                    # dict[str, Strategy]
```

| Method | Description |
|--------|-------------|
| `save_evolved_strategy(strategy, lineage)` | Persists an evolved strategy with its lineage metadata. |
| `get_evolved_strategy(id)` | Returns a `Strategy` or `None`. |
| `list_evolved_strategies(include_culled)` | Returns `(Strategy, StrategyLineage)` tuples. |
| `cull_evolved_strategy(id)` | Sets `culled_at` to the current UTC timestamp. |
| `get_evolved_strategy_pool()` | Convenience method returning active strategies as a `dict`. |

### Profile Evolution

```python
store.save_evolved_profile(profile, lineage)

profile = store.get_evolved_profile("hardened_profile_1")   # Profile | None

active = store.list_evolved_profiles()
all_ = store.list_evolved_profiles(include_culled=True)
# Returns list[tuple[Profile, ProfileLineage]]

store.cull_evolved_profile("hardened_profile_1")

pool = store.get_evolved_profile_pool()                     # dict[str, Profile]
```

| Method | Description |
|--------|-------------|
| `save_evolved_profile(profile, lineage)` | Persists a hardened profile with lineage. |
| `get_evolved_profile(id)` | Returns a `Profile` or `None`. |
| `list_evolved_profiles(include_culled)` | Returns `(Profile, ProfileLineage)` tuples. |
| `cull_evolved_profile(id)` | Sets `culled_at` to the current UTC timestamp. |
| `get_evolved_profile_pool()` | Convenience method returning active profiles as a `dict`. |

---

## Calibration Methods

### `save_calibration_labels`

```python
store.save_calibration_labels(labels)
```

Persists a list of `CalibrationLabel` objects. Each label's `human_scores`
dictionary is exploded into individual rows keyed by `(transcript_id, metric,
labeler_id)`.

### `list_calibration_labels`

```python
labels = store.list_calibration_labels()
for label in labels:
    print(f"{label.transcript_id}: {label.human_scores}")
```

Reconstructs `CalibrationLabel` objects by grouping rows back into per-metric
score dictionaries.

### `save_judge_variant`

```python
variant_id = store.save_judge_variant(
    system_prompt="You are a fair judge...",
    transcript_prompt="Evaluate the following transcript...",
    calibration_score=0.87,
)
print(f"Saved variant: {variant_id}")
```

Creates a new judge prompt variant for A/B testing. Returns an auto-generated
ID in the format `judge_YYYYMMDDHHMMSSffffff`.

### `list_judge_variants`

```python
variants = store.list_judge_variants()
for v in variants:
    print(f"{v['id']}: score={v['calibration_score']}")
```

Returns all judge prompt variants as raw dictionaries, ordered by `created_at
DESC`.

---

## Internal Helpers

The module includes several private helper functions for row conversion:

| Function | Purpose |
|----------|---------|
| `_run_row(result)` | Converts a `SimulationResult` into a tuple for SQL insertion. |
| `_result_from_row(row)` | Reconstructs a `SimulationResult` from a database row. |
| `_elo_update_from_row(row)` | Reconstructs an `EloUpdate` from a history row. |
| `_tournament_from_row(row)` | Reconstructs a `TournamentResult` from a database row. |
| `_strategy_from_evolved_row(row)` | Deserializes a `Strategy` from its JSON column. |
| `_strategy_lineage_from_row(row)` | Reconstructs a `StrategyLineage` from a row. |
| `_profile_from_evolved_row(row)` | Deserializes a `Profile` from its JSON column. |
| `_profile_lineage_from_row(row)` | Reconstructs a `ProfileLineage` from a row. |
| `_enum_value(value)` | Safely extracts `.value` from enums, returning `None` for `None`. |

---

## Schema Migrations

The store uses `_ensure_column` to add columns that may be missing from older
database files:

```python
def _ensure_column(self, connection, table, column, definition):
    columns = {row["name"] for row in connection.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()}
    if column not in columns:
        connection.execute(
            f"ALTER TABLE {table} ADD COLUMN {column} {definition}"
        )
```

Currently applied migrations:

- `elo_ratings.conversation_model` (`TEXT NOT NULL DEFAULT ''`)
- `elo_ratings.judge_model` (`TEXT NOT NULL DEFAULT ''`)
- `elo_history.conversation_model` (`TEXT NOT NULL DEFAULT ''`)
- `elo_history.judge_model` (`TEXT NOT NULL DEFAULT ''`)

---

## Complete Usage Example

```python
from collection_swarm.store import SimulationStore

store = SimulationStore("output/my_project.sqlite")

# After running simulations
counts = store.count_by_status()
print(f"Completed: {counts.get('completed', 0)}")
print(f"Failed: {counts.get('failed', 0)}")

# Compare strategies for a profile
stats = store.get_strategy_comparison("struggling_single_parent")
for s in stats:
    print(f"  {s.strategy_id}: "
          f"payment={s.mean_payment_probability:.2f}, "
          f"compliance={s.mean_compliance_score:.2f}, "
          f"escalation={s.mean_escalation_risk:.2f}")

# Check coverage gaps
from collection_swarm.runner import build_matrix
from collection_swarm.config import load_app_config

config = load_app_config()
cells = build_matrix(config)
needed = store.get_backfill_needed(target_reps=5, cells=cells)
print(f"\n{len(needed)} simulations needed to reach 5 reps per cell")

# Cost audit
costs = store.get_cost_summary()
print(f"\nTotal cost: ${costs['estimated_cost_usd']:.2f}")
print(f"Tokens: {costs['input_tokens']:.0f} in / {costs['output_tokens']:.0f} out")
```
