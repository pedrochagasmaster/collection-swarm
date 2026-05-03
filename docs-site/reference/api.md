# HTTP API reference

Everything under `/api/` returns JSON. Routes are defined in
[`web/app.py`](../modules/web/app.md). Long-running operations are
dispatched as `WebRunJob`s and polled at `/api/jobs/{id}`.

## Read-side

| Method | Path                                              | Response                                                          |
| ------ | ------------------------------------------------- | ------------------------------------------------------------------ |
| GET    | `/api/dashboard`                                  | Aggregate counts, outcome distribution, average scores, cost summary. |
| GET    | `/api/runs?status=&profile_id=&strategy_id=`      | List of `SimulationResult` summaries.                              |
| GET    | `/api/runs/{run_id}`                              | Full `SimulationResult` JSON.                                      |
| GET    | `/api/profiles/{profile_id}/strategies`           | `StrategyRanking` for one Profile.                                 |
| GET    | `/api/profiles/{profile_id}/objections?strategy_id=` | `ObjectionReport` for the recommended (or chosen) Strategy.    |
| GET    | `/api/compliance/exclusions`                      | Current exclusions plus thresholds and run-count hint.             |
| GET    | `/api/playbook?format=html\|markdown`             | Rendered Playbook + metadata.                                       |

## Configuration introspection

| Method | Path                                | Response                                                   |
| ------ | ----------------------------------- | ----------------------------------------------------------- |
| GET    | `/api/config/profiles`              | Profiles with rolled-up performance.                       |
| GET    | `/api/config/strategies`            | Strategies with rolled-up performance.                     |
| GET    | `/api/config/models`                | Model catalogue with defaults.                             |
| GET    | `/api/config/run-options`           | Combined Profile / Strategy / Model payload for launchers. |

## Arena & evolution

| Method | Path                                       | Response                                        |
| ------ | ------------------------------------------ | ----------------------------------------------- |
| GET    | `/api/arena/leaderboard?entity_type=&conversation_model=&judge_model=` | `EloRating` lists per entity type. |
| GET    | `/api/arena/history/{entity_id}`           | `EloUpdate` history for one entity.            |
| GET    | `/api/arena/tournaments`                   | `TournamentResult` list.                        |
| GET    | `/api/arena/tournaments/{tournament_id}`   | One `TournamentResult`.                         |
| GET    | `/api/evolution/pool`                      | Active evolved Strategies and Profiles with lineage. |

## Calibration

| Method | Path                                 | Body                                | Response                          |
| ------ | ------------------------------------ | ----------------------------------- | --------------------------------- |
| POST   | `/api/calibration/labels`            | `[CalibrationLabel]` JSON           | `{"saved": N}`                   |
| GET    | `/api/calibration/results`           | —                                   | `CalibrationResult` JSON         |
| POST   | `/api/jobs/calibration`              | `CalibrationJobRequest`             | `WebRunJob` snapshot              |
| GET    | `/api/calibration/variants`          | —                                   | `[judge_prompt_variants]`        |

## Model benchmarks

| Method | Path                                       | Response                                          |
| ------ | ------------------------------------------ | -------------------------------------------------- |
| GET    | `/api/model-benchmarks/options`            | Known Cursor model IDs and defaults.              |
| GET    | `/api/model-benchmarks`                    | List of saved benchmark report headers.           |
| GET    | `/api/model-benchmarks/{job_id}`           | Saved benchmark report payload.                   |
| POST   | `/api/jobs/model-benchmarks`               | `WebRunJob` snapshot for a live benchmark.        |

## Job control

| Method | Path                              | Body                       | Notes                                          |
| ------ | --------------------------------- | -------------------------- | ----------------------------------------------- |
| POST   | `/api/jobs/simulations`           | `SimulationLaunchRequest`  | Launch one Simulation.                          |
| POST   | `/api/jobs/matrix`                | `MatrixLaunchRequest`      | Launch a matrix sweep.                          |
| POST   | `/api/jobs/tournaments`           | `TournamentLaunchRequest`  | Launch a multi-round tournament.                |
| GET    | `/api/jobs`                       | —                          | All jobs in reverse chronological order.        |
| GET    | `/api/jobs/{job_id}`              | —                          | One job snapshot.                               |
| POST   | `/api/jobs/{job_id}/cancel`       | —                          | Mark cancellation; cooperatively aborts.        |

## Manual sessions

| Method | Path                                          | Body                  | Notes                                          |
| ------ | --------------------------------------------- | --------------------- | ----------------------------------------------- |
| POST   | `/api/manual-sessions`                        | `ManualSessionRequest`| Create the session.                            |
| GET    | `/api/manual-sessions/{session_id}`           | —                     | Snapshot.                                       |
| POST   | `/api/manual-sessions/{session_id}/turn`      | `ManualTurnRequest`   | Submit a human turn; AI replies on the same response. |
| POST   | `/api/manual-sessions/{session_id}/finish`    | —                     | Force the session into the Judge.               |

## Static & root

| Method | Path                  | Notes                                                                     |
| ------ | --------------------- | -------------------------------------------------------------------------- |
| GET    | `/`                   | Returns `web/static/index.html` directly.                                  |
| GET    | `/static/{path}`      | Mounted via `StaticFiles`. Holds the SPA, the CSS, and the self-hosted fonts. |

## Request schemas (Pydantic)

### `SimulationLaunchRequest`

```json
{
  "profile_id": "cooperative_hardship",
  "strategy_id": "empathetic_payment_plan",
  "conversation_model": "cursor-gpt-5.5-medium",
  "judge_model": "cursor-claude-4.6-opus-high-thinking"
}
```

### `MatrixLaunchRequest`

```json
{
  "profile_ids": ["cooperative_hardship", "written_proof_disputer"],
  "strategy_ids": ["empathetic_payment_plan", "problem_solving_callback"],
  "conversation_models": ["cursor-gpt-5.5-medium"],
  "judge_models": ["cursor-claude-4.6-opus-high-thinking"],
  "reps": 2,
  "concurrency": 2
}
```

### `TournamentLaunchRequest`

```json
{
  "format": "swiss",
  "rounds": 4,
  "profile_ids": null,
  "strategy_ids": null,
  "conversation_model": null,
  "judge_model": null,
  "reps_per_pairing": 1,
  "concurrency": 2
}
```

### `BenchmarkLaunchRequest`

```json
{
  "cursor_model_names": ["gpt-5.5", "claude-opus-4-7"],
  "roles": ["collector", "debtor", "judge"],
  "profile_ids": ["cooperative_hardship"],
  "strategy_ids": ["empathetic_payment_plan"],
  "judge_profile_ids": ["written_proof_disputer"],
  "concurrency": 1
}
```

### `ManualSessionRequest`

```json
{
  "profile_id": "cooperative_hardship",
  "strategy_id": "empathetic_payment_plan",
  "human_role": "collector",
  "conversation_model": "cursor-gpt-5.5-medium",
  "judge_model": "cursor-claude-4.6-opus-high-thinking"
}
```

### `ManualTurnRequest`

```json
{ "content": "Olá, falo em nome do liquidante do Will Bank..." }
```

### `CalibrationJobRequest`

```json
{
  "labels": [{ "transcript_id": "sim_...", "human_scores": {"compliance_score": 0.9}, "labeler_id": "alice" }],
  "optimize": true
}
```

## Job snapshot shape

Returned by every `/api/jobs/...` endpoint.

```json
{
  "id": "job_a1b2c3d4e5",
  "kind": "matrix",
  "status": "running",
  "total": 12,
  "completed": 4,
  "failed": 1,
  "current_run": { "id": "sim_...", "status": "running", ... },
  "result_ids": ["sim_...", "sim_..."],
  "errors": ["..."],
  "artifacts": {},
  "benchmark_report": null,
  "message": "5/12 simulations finished.",
  "started_at": "2026-05-03T10:39:00+00:00",
  "ended_at": null
}
```

`status` ∈ `queued | running | completed | failed | cancelled`.
