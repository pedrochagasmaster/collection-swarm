# Database schema

The store is a single SQLite file with eight tables. The schema lives in
[`store.SimulationStore._init_schema`](../modules/store.md#tables).

Default location: `output/collection_swarm.sqlite`. Override via the
top-level `--db` CLI flag or the `db_path` argument to
`create_app(...)` / `SimulationStore(...)`.

## `runs`

The substrate every report is built on. One row per `SimulationResult`.

| Column                         | Type    | Notes                                              |
| ------------------------------ | ------- | --------------------------------------------------- |
| `id`                           | TEXT PK | `sim_<12 hex>` for engine-generated runs.          |
| `status`                       | TEXT    | `completed`, `failed`, or `running`.               |
| `error_message`                | TEXT    | Set when `status='failed'`.                        |
| `profile_id`                   | TEXT    | FK semantic; not enforced at the schema level.     |
| `strategy_id`                  | TEXT    | Same.                                              |
| `conversation_model`           | TEXT    | The configured model ID, not the provider name.    |
| `judge_model`                  | TEXT    | Same.                                              |
| `started_at`, `ended_at`       | TEXT    | ISO 8601 strings (UTC).                            |
| `turn_count`                   | INTEGER | Number of `Message`s in the transcript.             |
| `ended_by`                     | TEXT    | `collector` / `debtor` / `stalemate` / `turn_limit`. |
| `transcript_json`              | TEXT    | JSON-encoded `[Message, ...]`.                     |
| `judge_reasoning`              | TEXT    | The Judge's free-text reasoning.                   |
| `payment_outcome`              | TEXT    | One of the `PaymentOutcome` values.                |
| `payment_probability`          | REAL    | 0–1.                                               |
| `debtor_satisfaction`          | REAL    | 0–1.                                               |
| `compliance_score`             | REAL    | 0–1.                                               |
| `conversation_efficiency`      | INTEGER | Turn count from the engine.                         |
| `rapport_built`                | REAL    | 0–1.                                               |
| `escalation_risk`              | REAL    | 0–1.                                               |
| `end_reason`                   | TEXT    | Free-form Judge classification.                     |
| `constraint_violations_json`   | TEXT    | JSON-encoded `[str, ...]`.                         |
| `total_input_tokens`           | INTEGER | Summed across the whole simulation.                |
| `total_output_tokens`          | INTEGER | Same.                                              |
| `estimated_cost_usd`           | REAL    | Sum of `_estimate_cost(...)` for each turn.         |

The `INSERT OR REPLACE` pattern in `save_runs` means re-saving a result
with the same ID overwrites the row.

## `elo_ratings`

Current Elo per `(entity_type, entity_id, conversation_model, judge_model)` tuple.

| Column                | Type    | Notes                                            |
| --------------------- | ------- | ------------------------------------------------ |
| `entity_type`         | TEXT    | `strategy` or `profile`.                         |
| `entity_id`           | TEXT    | The ID of the strategy / profile.                |
| `conversation_model`  | TEXT    | Empty string for backward-compat rows.            |
| `judge_model`         | TEXT    | Same.                                            |
| `rating`              | REAL    | Current Elo.                                      |
| `games_played`        | INTEGER | Count of finished games for K-factor selection.   |
| `wins`, `losses`, `draws` | INTEGER | Tally; "draw" is `effective_score ∈ [0.45, 0.55]`. |
| `updated_at`          | TEXT    | ISO 8601 (UTC).                                  |

PK: `(entity_type, entity_id, conversation_model, judge_model)`.

## `elo_history`

Append-only log of every `EloUpdate` ever applied.

| Column                | Type     | Notes                                            |
| --------------------- | -------- | ------------------------------------------------ |
| `id`                  | INTEGER  | Auto-increment PK.                               |
| `tournament_id`       | TEXT     | Optional FK to `tournaments.id`.                 |
| `entity_type`         | TEXT     | `strategy` / `profile`.                          |
| `entity_id`           | TEXT     | Same.                                            |
| `opponent_id`         | TEXT     | The opposing entity ID.                          |
| `conversation_model`, `judge_model` | TEXT | Same as `elo_ratings`.                |
| `simulation_id`       | TEXT     | The Simulation that triggered the update.         |
| `rating_before`, `rating_after` | REAL | Pre/post Elo values.                       |
| `effective_score`     | REAL     | Result of `arena.effective_score(judgment, scoring)`. |
| `expected_score`      | REAL     | Pre-game Elo expectation.                        |
| `timestamp`           | TEXT     | ISO 8601 (UTC).                                  |

## `tournaments`

| Column                | Type     | Notes                                                  |
| --------------------- | -------- | ------------------------------------------------------ |
| `id`                  | TEXT PK  | `tourn_<10 hex>`.                                      |
| `config_json`         | TEXT     | JSON-encoded `TournamentConfig`.                       |
| `rounds_completed`    | INTEGER  | Updated as rounds finish.                              |
| `total_games`         | INTEGER  | Total Simulations in the tournament so far.            |
| `started_at`          | TEXT     | ISO 8601 (UTC).                                        |
| `completed_at`        | TEXT     | ISO 8601 (UTC) when the loop ends.                     |
| `total_cost_usd`      | REAL     | Summed across all member simulations.                  |

## `evolved_strategies`

| Column                  | Type     | Notes                                              |
| ----------------------- | -------- | --------------------------------------------------- |
| `id`                    | TEXT PK  | `evo_<...>`.                                        |
| `generation`            | INTEGER  | Generation it was minted in.                        |
| `parent_ids_json`       | TEXT     | JSON-encoded list of parent Strategy IDs.           |
| `mutation_type`         | TEXT     | `llm`, `seed`, `fallback`, etc.                    |
| `mutation_description`  | TEXT     | Free-form text.                                     |
| `strategy_json`         | TEXT     | Full `Strategy.model_dump_json()`.                  |
| `created_at`, `culled_at` | TEXT  | ISO 8601 (UTC); `culled_at` is null while active.   |

## `evolved_profiles`

Mirror of `evolved_strategies` for Profile hardening:

| Column                   | Type     | Notes                                             |
| ------------------------ | -------- | -------------------------------------------------- |
| `id`                     | TEXT PK  | `hard_<...>`.                                      |
| `generation`             | INTEGER  | Same.                                              |
| `parent_id`              | TEXT     | Single parent Profile ID.                          |
| `hardening_type`         | TEXT     | `llm`, `seed`, `fallback`.                         |
| `hardening_description`  | TEXT     | Free-form.                                         |
| `profile_json`           | TEXT     | Full `Profile.model_dump_json()`.                 |
| `created_at`, `culled_at` | TEXT   | Same.                                              |

## `calibration_labels`

| Column            | Type     | Notes                                              |
| ----------------- | -------- | --------------------------------------------------- |
| `transcript_id`   | TEXT     | Matches `runs.id`.                                  |
| `metric`          | TEXT     | A `Judgment` field name.                           |
| `human_score`     | REAL     | 0–1.                                                |
| `labeler_id`      | TEXT     | Free-form.                                          |
| `labeled_at`      | TEXT     | ISO 8601 (UTC).                                    |

PK: `(transcript_id, metric, labeler_id)`. Two labelers can disagree on
the same metric without one overwriting the other.

## `judge_prompt_variants`

| Column                | Type    | Notes                                                            |
| --------------------- | ------- | ----------------------------------------------------------------- |
| `id`                  | TEXT PK | `judge_<YYYYMMDDHHMMSSffffff>`.                                   |
| `system_prompt`       | TEXT    | Full Judge system template at the time of snapshot.               |
| `transcript_prompt`   | TEXT    | Full Judge transcript template.                                   |
| `calibration_score`   | REAL    | The `overall_score` from the calibration that snapshotted it.     |
| `created_at`          | TEXT    | ISO 8601 (UTC).                                                   |

## Schema migrations

The store does not use Alembic. Two patterns instead:

- New tables are added with `CREATE TABLE IF NOT EXISTS`. Re-running
  `_init_schema` is idempotent.
- New columns are added through `_ensure_column(connection, table,
  column, definition)`, which checks `PRAGMA table_info` and `ALTER
  TABLE` only when needed. Currently used for the
  `conversation_model` / `judge_model` columns on the Elo tables.

If you need a destructive migration, do it manually with `sqlite3` or
delete the file and start over.
