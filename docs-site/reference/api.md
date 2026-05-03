# API Reference

Complete reference for every HTTP endpoint exposed by the Collection Swarm web dashboard.

**Base URL:** `http://127.0.0.1:8000` (default)

All JSON endpoints return `application/json`. Error responses use standard HTTP status codes with a `{"detail": "..."}` body.

---

## Dashboard

### `GET /api/dashboard`

Returns aggregate statistics across all completed simulation runs.

**Response:**

```json
{
  "total_runs": 24,
  "completed": 22,
  "failed": 2,
  "profiles": [
    "cooperative_hardship",
    "written_proof_disputer",
    "hostile_avoidant"
  ],
  "strategies": [
    "empathetic_payment_plan",
    "assertive_settlement",
    "neutral_reminder"
  ],
  "outcome_distribution": {
    "payment_plan": 8,
    "promise_to_pay": 6,
    "no_commitment": 5,
    "refusal": 3
  },
  "average_scores": {
    "payment_probability": 0.52,
    "compliance_score": 0.89,
    "debtor_satisfaction": 0.64,
    "escalation_risk": 0.21,
    "rapport_built": 0.58
  },
  "cost": {
    "total_cost_usd": 0.142,
    "total_input_tokens": 34200,
    "total_output_tokens": 25800
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `total_runs` | `int` | Sum of all runs regardless of status |
| `completed` | `int` | Runs with `status == "completed"` |
| `failed` | `int` | Runs with `status == "failed"` |
| `profiles` | `list[str]` | All configured profile IDs |
| `strategies` | `list[str]` | All configured strategy IDs |
| `outcome_distribution` | `dict[str, int]` | Count of each `payment_outcome` value across judged runs |
| `average_scores` | `dict[str, float]` | Mean of each judgment metric across judged runs |
| `cost` | `dict` | Aggregated token and cost data |

---

## Runs

### `GET /api/runs`

List simulation runs with optional filters.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | `str` | `null` | Filter by run status (`completed`, `failed`, `running`) |
| `profile_id` | `str` | `null` | Filter by debtor profile ID |
| `strategy_id` | `str` | `null` | Filter by collector strategy ID |

**Example Request:**

```
GET /api/runs?status=completed&profile_id=cooperative_hardship
```

**Response:** `list[RunSummary]`

```json
[
  {
    "id": "sim_a1b2c3d4",
    "status": "completed",
    "profile_id": "cooperative_hardship",
    "strategy_id": "empathetic_payment_plan",
    "conversation_model": "local-scripted",
    "judge_model": "local-judge",
    "turn_count": 5,
    "ended_by": "collector",
    "started_at": "2026-05-01T12:00:00+00:00",
    "ended_at": "2026-05-01T12:05:30+00:00",
    "total_input_tokens": 1420,
    "total_output_tokens": 980,
    "estimated_cost_usd": 0.0082,
    "error_message": null,
    "judgment": {
      "payment_outcome": "payment_plan",
      "payment_probability": 0.82,
      "compliance_score": 0.95,
      "debtor_satisfaction": 0.88,
      "escalation_risk": 0.08,
      "rapport_built": 0.85,
      "end_reason": "agreement_reached"
    }
  }
]
```

---

### `GET /api/runs/{run_id}`

Retrieve a single simulation run with full transcript and judgment.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `run_id` | `str` | The simulation run ID |

**Response:** Full `SimulationResult` serialized as JSON, including the `transcript` array.

```json
{
  "id": "sim_a1b2c3d4",
  "status": "completed",
  "profile_id": "cooperative_hardship",
  "strategy_id": "empathetic_payment_plan",
  "conversation_model": "local-scripted",
  "judge_model": "local-judge",
  "turn_count": 5,
  "ended_by": "collector",
  "started_at": "2026-05-01T12:00:00+00:00",
  "ended_at": "2026-05-01T12:05:30+00:00",
  "transcript": [
    {"role": "collector", "content": "Hello, this is Sarah from Meridian..."},
    {"role": "debtor", "content": "Hi... yeah, I know about the bill..."}
  ],
  "judgment": {
    "reasoning": "The collector used an empathetic approach...",
    "payment_outcome": "payment_plan",
    "payment_probability": 0.82,
    "compliance_score": 0.95,
    "debtor_satisfaction": 0.88,
    "conversation_efficiency": 5,
    "rapport_built": 0.85,
    "escalation_risk": 0.08,
    "end_reason": "agreement_reached",
    "constraint_violations": []
  },
  "total_input_tokens": 1420,
  "total_output_tokens": 980,
  "estimated_cost_usd": 0.0082,
  "error_message": null
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| `404` | Run ID not found |

---

## Analysis

### `GET /api/profiles/{profile_id}/strategies`

Compare all strategies for a given debtor profile, ranked by composite score.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `profile_id` | `str` | The debtor profile ID |

**Response:**

```json
{
  "profile_id": "cooperative_hardship",
  "recommended": "empathetic_payment_plan",
  "strategies": [
    {
      "strategy_id": "empathetic_payment_plan",
      "run_count": 6,
      "avg_payment_probability": 0.79,
      "avg_compliance_score": 0.94,
      "avg_debtor_satisfaction": 0.86,
      "avg_escalation_risk": 0.09,
      "composite_score": 0.88
    }
  ]
}
```

---

### `GET /api/compliance/exclusions`

Return profile/strategy combinations that fail compliance thresholds.

**Response:**

```json
{
  "thresholds": {
    "min_compliance_score": 0.8,
    "max_escalation_risk": 0.3
  },
  "total_completed_runs": 24,
  "minimum_runs_per_combination": 3,
  "exclusions": [
    {
      "profile_id": "hostile_avoidant",
      "strategy_id": "assertive_settlement",
      "compliance_score": 0.72,
      "escalation_risk": 0.68,
      "reason": "below_compliance_threshold",
      "simulation_count": 4,
      "run_ids": ["sim_x1", "sim_x2", "sim_x3"],
      "model_pairs": [
        {
          "conversation_model": "local-scripted",
          "judge_model": "local-judge"
        }
      ]
    }
  ]
}
```

---

### `GET /api/profiles/{profile_id}/objections`

Extract objection patterns from transcripts for a profile.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `strategy_id` | `str` | `null` | Strategy to analyze. Defaults to the recommended strategy. |

**Response:**

```json
{
  "profile_id": "written_proof_disputer",
  "strategy_id": "problem_solving_callback",
  "objections": {
    "wants_written_proof": 12,
    "disputes_fees": 8,
    "needs_documentation": 5
  }
}
```

---

### `GET /api/playbook`

Generate a strategy playbook from all completed simulation data.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | `str` | `"html"` | Output format: `html` or `markdown` |

**Response:**

```json
{
  "format": "html",
  "content": "<h1>Collection Playbook</h1>...",
  "meta": {
    "simulation_count": 24,
    "conversation_models": ["local-scripted"],
    "judge_models": ["local-judge"],
    "thresholds": {
      "min_compliance_score": 0.8,
      "max_escalation_risk": 0.3
    },
    "generated_at": "2026-05-03T10:00:00+00:00"
  }
}
```

!!! warning "XSS sanitization"
    When `format=html`, the content is sanitized through `bleach.clean()` to strip dangerous HTML constructs. The Markdown source is always available via `format=markdown`.

---

## Configuration

### `GET /api/config/profiles`

List all configured debtor profiles with aggregated performance data.

**Response:** `list[Profile]`

```json
[
  {
    "id": "cooperative_hardship",
    "archetype": "cooperative",
    "financial_situation": "hardship",
    "debt_amount": 850,
    "debt_type": "credito_pessoal_will",
    "primary_objection": "inability_to_pay",
    "emotional_state": "anxious",
    "demographics": "nordeste_classe_c_mae_provedora",
    "performance": {
      "run_count": 6,
      "avg_payment_probability": 0.67,
      "avg_compliance_score": 0.92
    }
  }
]
```

---

### `GET /api/config/strategies`

List all configured collector strategies with aggregated performance data.

**Response:** `list[Strategy]`

```json
[
  {
    "id": "empathetic_payment_plan",
    "tone": "empathetic",
    "opening_approach": "soft_intro",
    "negotiation_tactic": "payment_plan",
    "escalation_style": "none",
    "concession_willingness": "flexible",
    "follow_up_strategy": "written_agreement",
    "performance": {
      "run_count": 4,
      "avg_payment_probability": 0.79,
      "avg_compliance_score": 0.94
    }
  }
]
```

---

### `GET /api/config/models`

List all configured LLM models and their defaults.

**Response:**

```json
{
  "models": [
    {
      "id": "local-scripted",
      "backend": "scripted",
      "model_name": "scripted_echo"
    },
    {
      "id": "nim-mistral-large-3-675b",
      "backend": "nim",
      "model_name": "openai/mistralai/mistral-large-3-675b-instruct-2512"
    }
  ],
  "default_conversation_model": "local-scripted",
  "default_judge_model": "local-judge"
}
```

---

### `GET /api/config/run-options`

Full option set for launching simulations — includes profiles, strategies, models, and defaults. Incorporates evolved entities from the evolution pool.

**Response:**

```json
{
  "profiles": [ ... ],
  "strategies": [ ... ],
  "conversation_models": [ ... ],
  "judge_models": [ ... ],
  "defaults": {
    "conversation_model": "local-scripted",
    "judge_model": "local-judge",
    "reps": 1
  }
}
```

---

## Arena

### `GET /api/arena/leaderboard`

Retrieve Elo rankings for strategies and/or profiles.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entity_type` | `str` | `null` | Filter: `"strategy"`, `"profile"`, or `null` for both |
| `conversation_model` | `str` | default model | Filter ratings by conversation model |
| `judge_model` | `str` | default model | Filter ratings by judge model |

**Response:**

```json
{
  "strategies": [
    {
      "entity_type": "strategy",
      "entity_id": "empathetic_payment_plan",
      "rating": 1542.3,
      "games_played": 12,
      "wins": 8,
      "losses": 3,
      "draws": 1,
      "conversation_model": "local-scripted",
      "judge_model": "local-judge"
    }
  ],
  "profiles": [
    {
      "entity_type": "profile",
      "entity_id": "cooperative_hardship",
      "rating": 1480.1,
      "games_played": 12,
      "wins": 4,
      "losses": 7,
      "draws": 1,
      "conversation_model": "local-scripted",
      "judge_model": "local-judge"
    }
  ]
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| `400` | `entity_type` is not `strategy`, `profile`, or `null` |

---

### `GET /api/arena/history/{entity_id}`

Retrieve the Elo rating history for a specific entity (strategy or profile).

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `entity_id` | `str` | Strategy or profile ID |

**Response:** `list[EloUpdate]`

```json
[
  {
    "entity_type": "strategy",
    "entity_id": "empathetic_payment_plan",
    "opponent_id": "cooperative_hardship",
    "simulation_id": "sim_abc123",
    "rating_before": 1500.0,
    "rating_after": 1516.2,
    "effective_score": 0.82,
    "expected_score": 0.50,
    "conversation_model": "local-scripted",
    "judge_model": "local-judge"
  }
]
```

---

### `GET /api/arena/tournaments`

List all completed tournaments.

**Response:** `list[TournamentResult]`

```json
[
  {
    "id": "tourn_abc123",
    "config": {
      "format": "swiss",
      "rounds": 4,
      "reps_per_pairing": 1
    },
    "rounds_completed": 4,
    "total_games": 16,
    "total_cost_usd": 0.045,
    "completed_at": "2026-05-02T18:30:00+00:00"
  }
]
```

---

### `GET /api/arena/tournaments/{tournament_id}`

Get detailed information about a specific tournament.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `tournament_id` | `str` | Tournament ID |

**Error Responses:**

| Status | Condition |
|--------|-----------|
| `404` | Tournament not found |

---

## Evolution

### `GET /api/evolution/pool`

Retrieve all evolved strategies and profiles with their lineage metadata.

**Response:**

```json
{
  "strategies": [
    {
      "id": "evo_empathetic_v2",
      "tone": "empathetic",
      "negotiation_tactic": "payment_plan",
      "lineage": {
        "strategy_id": "evo_empathetic_v2",
        "parent_id": "empathetic_payment_plan",
        "generation": 3,
        "mutation_description": "Added rapport-building opener"
      }
    }
  ],
  "profiles": [
    {
      "id": "evo_hardship_v1",
      "archetype": "cooperative",
      "lineage": {
        "profile_id": "evo_hardship_v1",
        "parent_id": "cooperative_hardship",
        "generation": 1
      }
    }
  ]
}
```

---

## Calibration

### `GET /api/calibration/results`

Retrieve calibration metrics comparing judge scores against human labels.

**Response:**

```json
{
  "label_count": 15,
  "overall_score": 0.84,
  "metric_scores": {
    "payment_probability": 0.88,
    "compliance_score": 0.92,
    "debtor_satisfaction": 0.78,
    "escalation_risk": 0.80
  }
}
```

---

### `POST /api/calibration/labels`

Upload human calibration labels.

**Request Body:** `list[CalibrationLabel]`

```json
[
  {
    "transcript_id": "sim_abc123",
    "human_scores": {
      "payment_probability": 0.7,
      "compliance_score": 0.9,
      "debtor_satisfaction": 0.65
    },
    "labeler_id": "analyst_1"
  }
]
```

**Response:**

```json
{
  "saved": 1
}
```

---

### `POST /api/jobs/calibration`

Launch an asynchronous calibration evaluation job.

**Request Body:**

```json
{
  "labels": [],
  "optimize": true
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `labels` | `list[dict]` | `[]` | Additional labels to save before evaluation |
| `optimize` | `bool` | `true` | Store the current judge prompt as a scored variant |

**Response:** `WebRunJob` snapshot (see [Jobs](#jobs)).

---

### `GET /api/calibration/variants`

List all stored judge prompt variants with their calibration scores.

**Response:** `list[dict]`

```json
[
  {
    "id": "variant_001",
    "system_prompt_hash": "abc123",
    "calibration_score": 0.84,
    "created_at": "2026-05-02T10:00:00+00:00"
  }
]
```

---

## Model Benchmarks

### `GET /api/model-benchmarks/options`

Returns available models, roles, and defaults for configuring a benchmark run.

**Response:**

```json
{
  "cursor_models": ["gpt-5.5", "gpt-5.4-high", "claude-opus-4-7-thinking-high"],
  "default_cursor_models": ["gpt-5.5", "claude-opus-4-7-thinking-high"],
  "roles": ["collector", "debtor", "judge"],
  "profiles": [ ... ],
  "strategies": [ ... ],
  "defaults": {
    "profile_ids": ["cooperative_hardship"],
    "strategy_ids": ["empathetic_payment_plan"],
    "judge_profile_ids": ["written_proof_disputer"],
    "concurrency": 1
  }
}
```

---

### `GET /api/model-benchmarks`

List all completed benchmark reports (newest first).

**Response:**

```json
[
  {
    "job_id": "bench_a1b2c3",
    "title": "Production Cursor Model Role Benchmark",
    "generated_at": "2026-05-02T14:00:00+00:00",
    "recommendations": {
      "collector": "gpt-5.5",
      "debtor": "gpt-5.5",
      "judge": "claude-opus-4-7-thinking-high"
    },
    "probe_count": 12
  }
]
```

---

### `GET /api/model-benchmarks/{job_id}`

Retrieve the full benchmark report for a specific job.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | `str` | Benchmark job ID |

**Response:** Full benchmark report including per-model, per-role probe results, scores, and recommendations.

**Error Responses:**

| Status | Condition |
|--------|-----------|
| `404` | Benchmark report not found |

---

### `POST /api/jobs/model-benchmarks`

Launch a model benchmark job.

**Request Body:**

```json
{
  "cursor_model_names": ["gpt-5.5", "claude-opus-4-7-thinking-high"],
  "roles": ["collector", "debtor", "judge"],
  "profile_ids": ["cooperative_hardship"],
  "strategy_ids": ["empathetic_payment_plan"],
  "judge_profile_ids": ["written_proof_disputer"],
  "concurrency": 1
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `cursor_model_names` | `list[str]` | default probe models | Cursor SDK model IDs to benchmark |
| `roles` | `list[str]` | `["collector", "debtor", "judge"]` | Roles to probe |
| `profile_ids` | `list[str]` | `["cooperative_hardship"]` | Profiles for conversation scenarios |
| `strategy_ids` | `list[str]` | `["empathetic_payment_plan"]` | Strategies for conversation scenarios |
| `judge_profile_ids` | `list[str]` | `["written_proof_disputer"]` | Profiles for judge evaluation scenarios |
| `concurrency` | `int` | `1` | Parallel probe limit (1–4) |

**Response:** `WebRunJob` snapshot.

**Error Responses:**

| Status | Condition |
|--------|-----------|
| `400` | Empty profile, strategy, judge profile, or model list |
| `400` | Unknown profile, strategy, or model ID |

---

## Jobs

### `POST /api/jobs/simulations`

Launch a single simulation as a background job.

**Request Body:**

```json
{
  "profile_id": "cooperative_hardship",
  "strategy_id": "empathetic_payment_plan",
  "conversation_model": "local-scripted",
  "judge_model": "local-judge"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `profile_id` | `str` | Yes | Debtor profile ID |
| `strategy_id` | `str` | Yes | Collector strategy ID |
| `conversation_model` | `str` | No | Defaults to config default |
| `judge_model` | `str` | No | Defaults to config default |

**Response:** `WebRunJob` snapshot.

**Error Responses:**

| Status | Condition |
|--------|-----------|
| `400` | Unknown profile, strategy, or model ID |

---

### `POST /api/jobs/matrix`

Launch a matrix sweep across profiles × strategies × models × reps.

**Request Body:**

```json
{
  "profile_ids": ["cooperative_hardship", "hostile_avoidant"],
  "strategy_ids": ["empathetic_payment_plan", "neutral_reminder"],
  "conversation_models": ["local-scripted"],
  "judge_models": ["local-judge"],
  "reps": 2,
  "concurrency": 2
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `profile_ids` | `list[str]` | all profiles | Profiles to include |
| `strategy_ids` | `list[str]` | all strategies | Strategies to include |
| `conversation_models` | `list[str]` | `[default]` | Conversation model IDs |
| `judge_models` | `list[str]` | `[default]` | Judge model IDs |
| `reps` | `int` | `1` | Repetitions per cell (1–100) |
| `concurrency` | `int` | `2` | Parallel simulation limit (1–10) |

**Response:** `WebRunJob` snapshot with `total = profiles × strategies × conv_models × judge_models × reps`.

**Error Responses:**

| Status | Condition |
|--------|-----------|
| `400` | Empty profile, strategy, or model list |
| `400` | Unknown profile, strategy, or model ID |

---

### `POST /api/jobs/tournaments`

Launch an Elo-rated tournament.

**Request Body:**

```json
{
  "format": "swiss",
  "rounds": 4,
  "profile_ids": ["cooperative_hardship", "hostile_avoidant"],
  "strategy_ids": ["empathetic_payment_plan", "neutral_reminder"],
  "conversation_model": "local-scripted",
  "judge_model": "local-judge",
  "reps_per_pairing": 1,
  "concurrency": 2
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `format` | `str` | `"swiss"` | Tournament format: `swiss` or `round_robin` |
| `rounds` | `int` | `4` | Number of rounds (1–20) |
| `profile_ids` | `list[str]` | all profiles + evolved | Profile pool |
| `strategy_ids` | `list[str]` | all strategies + evolved | Strategy pool |
| `conversation_model` | `str` | default | Conversation model |
| `judge_model` | `str` | default | Judge model |
| `reps_per_pairing` | `int` | `1` | Repetitions per pairing (1–10) |
| `concurrency` | `int` | `2` | Parallel simulation limit (1–10) |

**Response:** `WebRunJob` snapshot.

**Error Responses:**

| Status | Condition |
|--------|-----------|
| `400` | Invalid format, empty profile/strategy list, or unknown IDs |

---

### `GET /api/jobs`

List all jobs, newest first.

**Response:** `list[WebRunJob]` snapshots.

---

### `GET /api/jobs/{job_id}`

Get current status and progress of a specific job.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | `str` | Job ID |

**Response:** `WebRunJob` snapshot.

```json
{
  "id": "job_a1b2c3d4e5",
  "kind": "matrix",
  "status": "running",
  "total": 8,
  "completed": 5,
  "failed": 0,
  "current_run": { ... },
  "result_ids": ["sim_1", "sim_2", "sim_3", "sim_4", "sim_5"],
  "errors": [],
  "artifacts": {},
  "benchmark_report": null,
  "message": "5/8 simulations finished.",
  "started_at": "2026-05-03T10:00:00+00:00",
  "ended_at": null
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| `404` | Job not found |

---

### `POST /api/jobs/{job_id}/cancel`

Cancel a running or queued job.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `job_id` | `str` | Job ID |

**Response:** Updated `WebRunJob` snapshot with `status: "cancelled"`.

**Error Responses:**

| Status | Condition |
|--------|-----------|
| `404` | Job not found |

!!! note
    Cancelling an already-completed or failed job returns the current snapshot without modification.

---

## Manual Sessions

### `POST /api/manual-sessions`

Create a new human-in-the-loop session.

**Request Body:**

```json
{
  "profile_id": "cooperative_hardship",
  "strategy_id": "empathetic_payment_plan",
  "human_role": "debtor",
  "conversation_model": "local-scripted",
  "judge_model": "local-judge"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `profile_id` | `str` | Yes | Debtor profile ID |
| `strategy_id` | `str` | Yes | Collector strategy ID |
| `human_role` | `str` | Yes | `"collector"` or `"debtor"` |
| `conversation_model` | `str` | No | Defaults to config default |
| `judge_model` | `str` | No | Defaults to config default |

**Response:** `ManualSession` snapshot.

!!! info "First turn"
    When `human_role` is `"debtor"`, the AI collector generates the first message automatically before returning the session. The response will already contain the collector's opening in the transcript.

**Error Responses:**

| Status | Condition |
|--------|-----------|
| `400` | Invalid `human_role`, unknown profile/strategy/model |

---

### `GET /api/manual-sessions/{session_id}`

Get the current state of a manual session.

**Response:**

```json
{
  "id": "manual_a1b2c3d4e5",
  "status": "waiting_for_human",
  "human_role": "debtor",
  "message": "Waiting for human debtor turn.",
  "run": {
    "transcript": [
      {"role": "collector", "content": "Hello, this is Sarah..."}
    ],
    "turn_count": 1
  },
  "ended_at": null
}
```

**Error Responses:**

| Status | Condition |
|--------|-----------|
| `404` | Session not found |

---

### `POST /api/manual-sessions/{session_id}/turn`

Submit the human's turn in the conversation.

**Request Body:**

```json
{
  "content": "I can do $75 per month starting next month."
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `content` | `str` | Yes | The human's message text (min 1 char). Include `[END_CONVERSATION]` to signal end. |

**Response:** Updated `ManualSession` snapshot. After the human turn, the AI counterpart responds automatically, and the session returns to `waiting_for_human` — unless an end condition is met.

**Error Responses:**

| Status | Condition |
|--------|-----------|
| `400` | Session is already completed |
| `404` | Session not found |
| `409` | Session is not in `waiting_for_human` state (e.g. `ai_thinking`) |

---

### `POST /api/manual-sessions/{session_id}/finish`

Force-finish a session and trigger judgment.

**Response:** Final `ManualSession` snapshot with `status: "completed"` and judgment attached.

**Error Responses:**

| Status | Condition |
|--------|-----------|
| `400` | Session has no turns to judge |
| `404` | Session not found |
| `409` | Session is not in `waiting_for_human` state |

---

## Static

### `GET /`

Serves the SPA entry point (`index.html`). The single-page application handles all client-side routing.

**Response:** `text/html`
