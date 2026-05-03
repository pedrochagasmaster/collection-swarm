---
title: Configuration
layout: default
nav_order: 7
---

# Configuration
{: .no_toc }

YAML-based configuration for profiles, strategies, models, prompts, and simulation parameters.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Source:** `src/collection_swarm/config.py` and `config/`

## Overview

All runtime configuration is stored in YAML files under the `config/` directory. The `config.py` module loads and validates these files into a single `AppConfig` object that is passed throughout the application.

```
config/
├── debtor_profiles.yaml        # Debtor personas and constraints
├── collector_strategies.yaml   # Collector behavioral configurations
├── models.yaml                 # LLM model routing and backend mapping
├── prompts.yaml                # Prompt templates for all three roles
└── simulation.yaml             # Engine parameters and thresholds
```

## AppConfig

The central configuration container that holds all loaded configuration:

```python
class AppConfig(BaseModel):
    profiles: dict[str, Profile]
    strategies: dict[str, Strategy]
    models: dict[str, ModelConfig]
    prompts: PromptConfig
    simulation: SimulationSettings
```

### Lookup Methods

| Method | Returns | Raises |
|:-------|:--------|:-------|
| `config.profile(profile_id)` | `Profile` | `KeyError` if not found |
| `config.strategy(strategy_id)` | `Strategy` | `KeyError` if not found |
| `config.model(model_id)` | `ModelConfig` | `KeyError` if not found |

### Default Model Selection

| Property | Selection Logic |
|:---------|:---------------|
| `default_conversation_model` | First model with `backend == "scripted"`, else first model |
| `default_judge_model` | First `"heuristic"` backend, then `"scripted"`, then first model |

## Loading Process

`load_app_config(config_dir)` orchestrates loading all five YAML files:

```python
def load_app_config(config_dir: Path = Path("config")) -> AppConfig:
    return AppConfig(
        profiles=load_profiles(base / "debtor_profiles.yaml"),
        strategies=load_strategies(base / "collector_strategies.yaml"),
        models=load_models(base / "models.yaml"),
        prompts=load_prompts(base / "prompts.yaml"),
        simulation=load_simulation_settings(base / "simulation.yaml"),
    )
```

### YAML Item Parsing

The `_items_by_id()` helper handles two YAML formats:

1. **List format** — items as a YAML list with `id` fields
2. **Mapping format** — items as a YAML map where the key becomes the `id`

This flexibility means you can write profiles as either:

```yaml
profiles:
  - id: cooperative_hardship
    archetype: cooperative
```

or:

```yaml
profiles:
  cooperative_hardship:
    archetype: cooperative
```

---

## Debtor Profiles (`debtor_profiles.yaml`)

Each profile defines a synthetic debtor persona. The bundled catalog includes 14 profiles calibrated to the Will Bank / Brazilian post-liquidation context.

### Profile Fields

| Field | Type | Description |
|:------|:-----|:------------|
| `id` | string | Unique identifier |
| `archetype` | string | Behavioral archetype (cooperative, hostile, disputer, etc.) |
| `financial_situation` | string | Financial capacity (hardship, can_pay_partial, stable, etc.) |
| `debt_amount` | float | Outstanding balance in R$ |
| `debt_age_days` | int | Days since the debt was due |
| `debt_type` | string | Product type (cartao_credito_will, credito_pessoal_will, etc.) |
| `prior_contact_count` | int | Previous collection contacts |
| `emotional_state` | string | Current emotional disposition |
| `primary_objection` | string | Main objection category |
| `responsiveness` | string | How responsive to contact (high, medium, low) |
| `demographics` | string | Demographic tag for cultural/regional context |
| `backstory` | string | Narrative paragraph in Portuguese |
| `constraints` | list | Machine-readable behavioral constraints |

### Bundled Profiles

| ID | Archetype | Debt (R$) | Primary Objection |
|:---|:----------|:----------|:------------------|
| `cooperative_hardship` | cooperative | 850 | inability_to_pay |
| `written_proof_disputer` | disputer | 612 | wants_written_proof |
| `hostile_avoidant` | hostile | 1,900 | avoidance |
| `liquidation_confused` | confused | 540 | questions_validity |
| `scam_suspicious` | skeptical | 1,280 | suspects_scam |
| `feirao_serial_renegotiator` | strategic | 2,750 | demands_deep_discount |
| `consignado_payroll_steady` | cooperative | 4,200 | needs_reassurance |
| `superendividado_chronic` | overwhelmed | 980 | over_indebted |
| `young_first_credit_card` | cooperative | 320 | forgetful_disorganized |
| `willbank_blocked_balance_hardship` | anxious_hardship | 930 | money_blocked |
| `willbank_micro_merchant_cashflow` | pragmatic | 1,480 | irregular_cashflow |
| `willbank_benefit_dependent_household` | vulnerable | 760 | basic_needs_priority |
| `willbank_fgc_waiting_high_balance` | angry | 3,900 | waiting_for_reimbursement |
| `willbank_low_digital_access` | low_digital | 520 | cannot_access_app |

---

## Collector Strategies (`collector_strategies.yaml`)

Each strategy defines how the Collector agent behaves during a conversation.

### Strategy Fields

| Field | Type | Required | Description |
|:------|:-----|:---------|:------------|
| `id` | string | Yes | Unique identifier |
| `tone` | string | Yes | Communication tone |
| `opening_approach` | string | Yes | How to start the conversation |
| `negotiation_tactic` | string | Yes | Core negotiation method |
| `escalation_style` | string | Yes | Escalation behavior |
| `concession_willingness` | string | Yes | Flexibility in making concessions |
| `compliance_adherence` | string | Yes | Regulatory compliance level |
| `follow_up_strategy` | string | Yes | Post-conversation follow-up |
| `payment_channel` | string | No | Payment method (boleto_registrado, etc.) |
| `primary_anchor` | string | No | Key point to anchor the negotiation |
| `discovery_questions` | string | No | Question style for information gathering |
| `framing` | string | No | Behavioral economics framing approach |
| `discount_authority` | string | No | Level of discount authority |
| `liquidation_disclosure` | string | No | When/how to disclose liquidation |
| `cultural_register` | string | No | Language register for Brazilian context |
| `rationale` | string | No | Why this strategy is recommended |

The `model_config = ConfigDict(extra="ignore")` setting means legacy strategies that omit optional fields work without changes.

### Bundled Strategies

| ID | Tone | Tactic |
|:---|:-----|:-------|
| `empathetic_payment_plan` | empathetic | Payment plan |
| `assertive_settlement` | assertive | Settlement offer |
| `neutral_reminder` | neutral | Payment reminder |
| `problem_solving_callback` | empathetic | Empathy then planning |
| `liquidation_explainer` | calm_informative | Defer until validated |
| `whatsapp_self_service` | friendly_brief | Link to portal |
| `superendividamento_referral` | empathetic | Legal referral |
| `consignado_confirmation` | calm_informative | Confirm and inform |
| `blocked_balance_hardship_plan` | empathetic_practical | Micro-installment |
| `micro_merchant_cashflow_alignment` | collaborative | Cashflow-aligned |
| `overindebtedness_stabilization` | nonjudgmental | One default option |
| `reimbursement_milestone_callback` | calm_respectful | Bridge agreement |
| `low_digital_access_guidance` | patient | Step-by-step guidance |

---

## Models (`models.yaml`)

Model configuration uses a **tiered structure** separating conversation and judge models.

### Model Fields

| Field | Type | Description |
|:------|:-----|:------------|
| `id` | string | CLI-facing identifier |
| `backend` | string | Backend type: `scripted`, `heuristic`, `nim`, `cursor_sdk` |
| `provider` | string | Provider name (local, openai, anthropic, etc.) |
| `model_name` | string | Provider-facing model identifier |
| `input_cost_per_m` | float | Cost per million input tokens |
| `output_cost_per_m` | float | Cost per million output tokens |

### Tiered YAML Structure

```yaml
tiers:
  conversation:
    models:
      - id: local-scripted
        backend: scripted
        provider: local
      - id: cursor-gpt-5.5-medium
        backend: cursor_sdk
        provider: openai
        model_name: gpt-5.5
  judge:
    models:
      - id: local-judge
        backend: heuristic
        provider: local
```

The `load_models()` function detects the `tiers` key and flattens all models into a single dictionary.

---

## Prompts (`prompts.yaml`)

Contains prompt templates for all three roles plus the Cursor SDK preamble.

### Sections

| Section | Class | Fields |
|:--------|:------|:-------|
| `collector` | `CollectorPromptConfig` | `system`, `history_empty`, `history` |
| `debtor` | `DebtorPromptConfig` | `system`, `constraints_empty`, `history_message` |
| `judge` | `JudgePromptConfig` | `system`, `transcript` |
| `cursor_sdk` | `CursorSdkPromptConfig` | `preamble` |

Prompt templates use Python's `str.format()` syntax with domain objects passed as variables.

---

## Simulation Settings (`simulation.yaml`)

Controls engine behavior, compliance thresholds, and arena defaults.

### Settings Structure

```yaml
conversation:
  max_turns: 12
  end_signal: '[END_CONVERSATION]'
  stalemate:
    window: 3
    similarity_threshold: 0.86

matrix:
  default_repetitions: 1

compliance:
  min_compliance_score: 0.8
  max_escalation_risk: 0.3

arena:
  default_format: swiss
  default_rounds: 4
  k_factor_initial: 32
  k_factor_stable: 16
  k_factor_threshold: 30
  scoring: payment_x_compliance

objection_taxonomy:
  - inability_to_pay
  - disputes_debt
  - wants_written_proof
  # ... 16 total categories
```

### Objection Taxonomy

The full taxonomy of recognized objection categories:

`inability_to_pay`, `disputes_debt`, `already_paid`, `needs_time`, `wants_written_proof`, `avoidance`, `requests_callback`, `liquidation_confusion`, `scam_concern`, `overindebtedness`, `bank_mistrust`, `privacy_concern`, `official_channel_request`, `blocked_balance_hardship`, `irregular_cashflow`, `low_digital_access`

---

## Environment Variables

Loaded from `.env` by `src/collection_swarm/env.py`:

| Variable | Required For | Description |
|:---------|:-------------|:------------|
| `NVIDIA_NIM_API_KEY` | NIM backend | NVIDIA NIM API key |
| `CURSOR_API_KEY` | Cursor SDK backend | Cursor API key |
| `CURSOR_SDK_WORKSPACE` | Cursor SDK (optional) | Workspace path for SDK agent |

The `.env` loader is minimal: it reads `KEY=VALUE` pairs, strips quotes, and **never overrides** already-exported environment variables.
