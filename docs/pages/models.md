---
title: Data Models
layout: default
nav_order: 8
---

# Data Models
{: .no_toc }

Pydantic domain models that define every data structure in Collection Swarm.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Source:** `src/collection_swarm/models.py`

## Overview

All domain objects are defined as **Pydantic v2 models** with strict validation, type coercion, and JSON serialization. The models module is the single source of truth for every data structure used across the application.

---

## Enumerations

### PaymentOutcome

```python
class PaymentOutcome(StrEnum):
    FULL_PAYMENT = "full_payment"
    PARTIAL_PAYMENT = "partial_payment"
    PAYMENT_PLAN = "payment_plan"
    PROMISE_TO_PAY = "promise_to_pay"
    NO_COMMITMENT = "no_commitment"
    REFUSAL = "refusal"
    HANG_UP = "hang_up"
```

### EndedBy

```python
class EndedBy(StrEnum):
    COLLECTOR = "collector"
    DEBTOR = "debtor"
    STALEMATE = "stalemate"
    TURN_LIMIT = "turn_limit"
```

---

## Profile Domain

### ConstraintRule

Machine-readable profile invariant for deterministic verification:

| Field | Type | Condition |
|:------|:-----|:----------|
| `type` | `"max_payment"` or `"required_action"` | Required |
| `amount` | `float` or `None` | Required when `type == "max_payment"` |
| `frequency` | `str` or `None` | Optional (e.g., "monthly") |
| `action` | `str` or `None` | Required when `type == "required_action"` |

Supported `action` values: `demand_written_proof`, `cite_liquidator_and_official_channel`, `provide_official_boleto_path`, `verify_official_channel`.

### Constraint

Combines human-readable text with an optional machine-readable rule:

```python
class Constraint(BaseModel):
    text: str
    rule: ConstraintRule | None = None
```

### AccountData

Financial data visible to the collector:

```python
class AccountData(BaseModel):
    debt_amount: float       # Must be > 0
    debt_age_days: int       # Must be >= 0
    debt_type: str
    prior_contact_count: int # Must be >= 0
```

### Profile

Full debtor persona. The `account_data` property extracts just the financial fields for the collector agent.

### Strategy

Collector behavioral configuration with 8 required core fields and 8 optional context fields. Uses `ConfigDict(extra="ignore")` for backward compatibility.

---

## Conversation Models

### Message

Simulation-level message with domain roles:

```python
class Message(BaseModel):
    role: Literal["collector", "debtor", "system", "judge"]
    content: str
```

### LLMMessage

Backend-level message with LLM roles:

```python
class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
```

The distinction between `Message` and `LLMMessage` is important: agents translate between the two during prompt construction.

---

## Prompt Configuration

| Class | Fields |
|:------|:-------|
| `CollectorPromptConfig` | `system`, `history_empty`, `history` |
| `DebtorPromptConfig` | `system`, `constraints_empty`, `history_message` |
| `JudgePromptConfig` | `system`, `transcript` |
| `CursorSdkPromptConfig` | `preamble` |
| `PromptConfig` | Container for all four above |

---

## Model Configuration

### ModelConfig

```python
class ModelConfig(BaseModel):
    id: str
    backend: str                       # "scripted", "nim", "cursor_sdk", etc.
    provider: str = "local"
    input_cost_per_m: float = 0.0
    output_cost_per_m: float = 0.0
    model_name: str | None = None      # Provider-facing name

    @property
    def litellm_model(self) -> str:    # Returns model_name or id
```

---

## Simulation Settings

### ConversationSettings

| Field | Type | Default | Constraint |
|:------|:-----|:--------|:-----------|
| `max_turns` | int | 20 | >= 2 |
| `end_signal` | str | `[END_CONVERSATION]` | — |
| `stalemate_window` | int | 3 | >= 1 |
| `stalemate_similarity_threshold` | float | 0.6 | 0.0–1.0 |

### ArenaSettings

| Field | Type | Default |
|:------|:-----|:--------|
| `default_format` | `"swiss"` or `"round_robin"` | `"swiss"` |
| `default_rounds` | int | 4 |
| `k_factor_initial` | float | 32.0 |
| `k_factor_stable` | float | 16.0 |
| `k_factor_threshold` | int | 30 |
| `scoring` | `"payment_x_compliance"` or `"payment_only"` | `"payment_x_compliance"` |

### SimulationSettings

Aggregates conversation settings, matrix defaults, compliance thresholds, objection taxonomy, and arena settings.

---

## Outcome Models

### Judgment

The structured evaluation output from the Judge (8 scored metrics + reasoning + constraint violations). See [Core Concepts]({% link concepts.md %}#judgment) for the full field listing.

### SimulationResult

The complete output of a simulation:

| Field | Type | Description |
|:------|:-----|:------------|
| `id` | str | Auto-generated UUID-based identifier |
| `status` | `"completed"`, `"failed"`, `"running"` | Current status |
| `error_message` | str or None | Error details if failed |
| `profile_id` | str | Debtor profile used |
| `strategy_id` | str | Collector strategy used |
| `conversation_model` | str | Model ID for collector/debtor |
| `judge_model` | str | Model ID for the judge |
| `started_at` | datetime | UTC start time |
| `ended_at` | datetime or None | UTC end time |
| `turn_count` | int | Total messages in transcript |
| `ended_by` | EndedBy or None | What terminated the conversation |
| `transcript` | list[Message] | Full conversation transcript |
| `judgment` | Judgment or None | Judge evaluation |
| `total_input_tokens` | int | Cumulative input tokens |
| `total_output_tokens` | int | Cumulative output tokens |
| `estimated_cost_usd` | float | Cumulative estimated cost |

DateTime fields accept ISO format strings and auto-add UTC timezone if missing.

---

## Analytics Models

### StrategyStats

Aggregated metrics for a strategy-profile combination:

```python
class StrategyStats(BaseModel):
    profile_id: str
    strategy_id: str
    simulation_count: int
    mean_payment_probability: float
    mean_compliance_score: float
    mean_escalation_risk: float
```

### MatrixCell

An immutable combination identifying a unique simulation configuration:

```python
class MatrixCell(BaseModel, frozen=True):
    profile_id: str
    strategy_id: str
    conversation_model: str
    judge_model: str
```

---

## Elo and Tournament Models

### EloRating

Current rating state for a strategy or profile:

| Field | Description |
|:------|:------------|
| `entity_type` | `"strategy"` or `"profile"` |
| `entity_id` | Strategy or profile ID |
| `conversation_model` | Model context for the rating |
| `judge_model` | Judge model context |
| `rating` | Current Elo rating (starts at 1500) |
| `games_played` | Total matches |
| `wins` / `losses` / `draws` | Win-loss-draw record |

### EloUpdate

A single rating change event from one simulation.

### TournamentConfig

Tournament parameters: format, rounds, reps per pairing, K-factor settings, scoring mode.

### TournamentResult

Outcome of a completed tournament: rounds completed, total games, cost, timestamps.

---

## Evolution Models

### StrategyLineage

Tracks the evolutionary history of a strategy:

| Field | Description |
|:------|:------------|
| `strategy_id` | The evolved strategy ID |
| `parent_ids` | IDs of parent strategies |
| `generation` | Generation number (0 = seed) |
| `mutation_type` | `"seed"`, `"llm"` |
| `mutation_description` | Human-readable description |
| `culled_at` | When the strategy was removed from the pool |

### EvolutionConfig

Evolution parameters: population size, top-k, bottom-k, cull count, mutation/crossover rates, evolver model.

### ProfileLineage

Similar to `StrategyLineage` but for hardened profiles.

### HardeningConfig

Profile hardening parameters: enabled flag, hardener model, max drift, realism check.

---

## Utility Functions

| Function | Description |
|:---------|:------------|
| `utc_now()` | Returns current UTC datetime |
| `model_dump_jsonable(model)` | Serializes a Pydantic model to a JSON-compatible dict |
