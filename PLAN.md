# Collection Swarm — Implementation Plan

This document captures every design decision made during planning and serves as the
implementation blueprint. It supersedes any conflicting details in SPEC.md.

---

## 1. LLM Access Strategy

### Constraint
No external LLM API keys available. All model access goes through:
- **Cursor SDK** — official `@cursor/sdk` agent API, invoked through the local Node bridge in `cursor_sdk_bridge/`.
- **NVIDIA NIM** — Free tier, OpenAI-compatible API at `https://integrate.api.nvidia.com/v1`. Requires NVIDIA API key (free, phone-verified).

### Three-Tier Model Routing

| Tier | Purpose | Backend | Models | Selection Logic |
|------|---------|---------|--------|-----------------|
| **Tier 1** | Judge Agent | Cursor SDK | `claude-opus-4-7`, `claude-sonnet-4-6`, `gemini-3.1-pro` | Rotate across runs. Always different provider than conversation model. |
| **Tier 2** | Collector & Debtor Agents | Cursor SDK + NVIDIA NIM | **Cursor:** `gpt-5.5`, `gemini-3-flash`. **NIM:** `mistralai/mistral-large-3-675b-instruct-2512`, `meta/llama-4-maverick-17b-128e-instruct`, `minimaxai/minimax-m2.7` | Both agents in a conversation always use the same model. Model tracked as experimental variable. |
| **Tier 3** | Mechanical tasks | NVIDIA NIM (free) | nemotron-mini-4b, gemma-3-27b-it | JSON repair, objection extraction clustering. |

### Multi-Model Strategy: Full Matrix (Option D)
Model assignment is an experimental variable, not just infrastructure. The simulation
matrix is: `profile × strategy × model_combo × repetitions`. Each model combo is a
(conversation_model, judge_model) pair where the judge is always a different provider
than the conversation model.

With 6 conversation models × 3 judge models minus same-provider pairs ≈ 15 valid combos.

---

## 2. Architecture

### LLM Abstraction Layer

```
┌─────────────────────────────────┐
│           LLMRouter             │
│  complete(model, messages) → str│
│  Dispatches based on model config│
└──────┬──────────────┬───────────┘
       │              │
       ▼              ▼
┌──────────────────┐ ┌──────────────┐
│ CursorSdkBackend │ │  NimBackend  │
│ (@cursor/sdk via │ │  (LiteLLM +  │
│  Node bridge)    │ │   HTTP API)  │
└──────────────────┘ └──────────────┘
```

- **NimBackend**: Uses LiteLLM with `base_url=https://integrate.api.nvidia.com/v1`.
  Standard async HTTP. Supports full parallel concurrency.
- **CursorSdkBackend**: Invokes `@cursor/sdk` through `cursor_sdk_bridge/run.mjs`.
  Uses a local agent configured with the selected Cursor model and workspace.
- **LLMRouter**: Unified `async complete(model_id, messages) -> LLMResponse` interface.
  Looks up model_id in `models.yaml` to determine backend. Returns response text +
  token counts + estimated cost.

Both backends return the same `LLMResponse` dataclass:
```python
@dataclass
class LLMResponse:
    content: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    model_id: str
    backend: str  # "cursor_sdk" or "nim"
```

### Concurrency Model
- **NIM conversations**: Full async parallelism via asyncio + LiteLLM. Respect 40 req/min
  rate limit with a semaphore/rate limiter.
- **Cursor SDK conversations**: Each completion invokes the Node bridge and Cursor SDK
  local agent. Limited parallelism is recommended to avoid Cursor throttling.
- **Batch runner**: Assigns conversations to backends based on model config. Manages both
  pools. NIM-model conversations naturally absorb more volume.

---

## 3. Conversation Engine

The engine is a **deep module**: its interface to callers is
`run_simulation(profile, strategy, models) -> SimulationResult`. Its interface to
agents is `generate_turn(messages) -> str`. All end-detection logic is an
implementation detail — no caller or agent needs to understand how conversations
terminate.

### Turn Structure
- Collector always speaks first (initiates the conversation).
- Turns alternate strictly: Collector → Debtor → Collector → Debtor → ...
- Full conversation history is passed to each agent on every turn (no windowing).
  Typical conversations are <8k tokens total — well within all context windows.

### Conversation End Detection
The engine owns **all** end-detection. No LLM calls — purely mechanical.

1. **Signal detection.** After each agent turn, the engine strips any
   `[END_CONVERSATION]` marker from the response text. The marker is never stored in
   the transcript; the engine records `ended_by` and lets the conversation stop.
2. **Stalemate detection (deterministic).** After each turn pair, the engine compares
   the last `stalemate_window` turn pairs (default 3) using
   `difflib.SequenceMatcher.ratio()`. If all pairs in the window exceed
   `stalemate_similarity_threshold` (default 0.6), the engine terminates with
   `ended_by: "stalemate"`. No LLM call — this is a fast string comparison.
3. **Turn limit.** Configurable `max_turns` (default 20). Engine stops regardless.

Priority: signal > stalemate > turn limit (evaluated in this order each turn).

### End Metadata
The engine tracks `ended_by` with one of:
- `"collector"` — Collector emitted `[END_CONVERSATION]`
- `"debtor"` — Debtor emitted `[END_CONVERSATION]`
- `"stalemate"` — Stalemate heuristic triggered
- `"turn_limit"` — Hit max_turns

The agent who emits `[END_CONVERSATION]` gets the last word. No rebuttal turn.

### Testability
Because end detection is deterministic, the engine can be tested with synthetic
transcript sequences — no LLM mocking required for end-condition coverage. Tests
verify: signal parsing, stalemate triggering at exact thresholds, turn-limit
enforcement, and correct `ended_by` values.

---

## 4. Agent Design

Each agent module is a **deep module** that owns the entire pipeline from domain
objects to parsed output: prompt construction, LLM call, response parsing. There is
no separate `prompts/` package — prompt templates are private implementation details
of each agent module, not a public interface.

Rationale: the old plan put prompts in separate modules, but each prompt was used by
exactly one agent (one adapter at a hypothetical seam). Merging them improves
locality — when a prompt change breaks parsing, the fix is in the same file.

### Collector Agent (`agents/collector.py`)
- **Interface:** `async generate_turn(strategy, account_data, history) -> str`
- **Implementation (private):**
  - Builds system prompt from Strategy parameters and Account Data
  - Injects FDCPA compliance guardrails
  - Calls LLMRouter
  - Returns raw response text (engine handles signal stripping)

### Debtor Agent (`agents/debtor.py`)
- **Interface:** `async generate_turn(profile, history) -> str`
- **Implementation (private):**
  - Builds system prompt from Profile persona, backstory, emotional state
  - Injects hard Constraints as behavioral invariants
  - Calls LLMRouter
  - Returns raw response text

### Judge Agent (`agents/judge.py`)
- **Interface:** `async evaluate(transcript, profile_constraints, account_data) -> Judgment`
- **Implementation (private):**
  - **Pass 1 — Free-text analysis:** reads transcript, produces qualitative reasoning
  - **Pass 2 — Structured scoring:** reads Pass 1 output + rubric, produces JSON scores
  - **Pass 3 — Constraint verification (deterministic):** compares transcript against
    the Profile's structured Constraint Rules to catch violations the LLM missed.
    See §4.1 below.
  - If JSON parsing fails in Pass 2, raw response is sent to Tier 3 for repair
  - Returns a complete Judgment (reasoning + scores + constraint violations)

The two-pass LLM process and the deterministic verification step are implementation
details. Callers see only: transcript in, Judgment out.

### 4.1 Programmatic Constraint Verification

Constraints have both a natural-language `text` (injected into the Debtor’s prompt)
and a structured `rule` (used for deterministic verification).

```yaml
constraints:
  - text: "Will NEVER agree to more than $150/month"
    rule:
      type: max_payment
      amount: 150
      frequency: monthly
  - text: "Will ALWAYS demand written proof before discussing payment"
    rule:
      type: required_action
      action: demand_written_proof
```

After the Judge’s LLM scoring passes, the judge module runs a deterministic
verification step:
1. Parse each Constraint Rule by `type`.
2. For `max_payment` rules: scan debtor turns for agreement patterns containing
   dollar amounts; flag if any exceed the threshold.
3. For `required_action` rules: scan debtor turns for the required action; flag if
   it never occurred before payment discussion began.
4. Merge LLM-detected violations with programmatically-detected ones (union, deduplicated).

Supported rule types are intentionally few at first (`max_payment`,
`required_action`). New types are added as Profiles need them. Rules that
can’t be expressed structurally remain LLM-only — the structured layer is
additive, not a replacement.

### Scoring Dimensions
| Metric | Type | Range | Description |
|--------|------|-------|-------------|
| `payment_outcome` | enum | - | full_payment, partial_payment, payment_plan, promise_to_pay, no_commitment, refusal, hang_up |
| `payment_probability` | float | 0.0–1.0 | Estimated likelihood the debtor would actually pay |
| `debtor_satisfaction` | float | 0.0–1.0 | How the debtor felt about the interaction |
| `compliance_score` | float | 0.0–1.0 | Adherence to fair debt collection regulations |
| `conversation_efficiency` | int | - | Number of turns to reach outcome |
| `rapport_built` | float | 0.0–1.0 | Quality of relationship established |
| `escalation_risk` | float | 0.0–1.0 | Risk of complaint, lawsuit, or brand damage |

---

## 5. Debtor Profiles

### Attributes
| Attribute | Description | Example Values |
|-----------|-------------|----------------|
| `id` | Unique identifier | cooperative_hardship |
| `archetype` | High-level behavioral category | cooperative, avoidant, hostile, disputer, confused |
| `financial_situation` | Ability to pay | can_pay_full, can_pay_partial, hardship, insolvent |
| `debt_amount` | Outstanding balance | 500, 2500, 15000 |
| `debt_age_days` | Days outstanding | 30, 90, 180, 365 |
| `debt_type` | Category of debt | medical, credit_card, utility, auto_loan, student |
| `prior_contact_count` | Previous collection attempts | 0, 1-3, 4+ |
| `emotional_state` | Starting disposition | calm, anxious, angry, indifferent, ashamed |
| `objection_type` | Primary non-payment reason | inability, dispute, forgetfulness, avoidance, refusal |
| `responsiveness` | Likelihood of engaging | high, medium, low |
| `demographics` | Age bracket and context | young_professional, senior, family_provider |
| `backstory` | Free-text personality/situation description | (see examples in SPEC.md §10.1) |
| `constraints` | Hard behavioral rules with structured verification rules | See §4.1 for format |

### Initial Profile Count
Phase 1: 5 profiles covering key archetypes.
Phase 4: Expand to 15+ profiles for full matrix coverage.

---

## 6. Collector Strategies

### Parameters
| Parameter | Description | Example Values |
|-----------|-------------|----------------|
| `id` | Unique identifier | empathetic_payment_plan |
| `tone` | Communication style | empathetic, assertive, neutral, urgent |
| `opening_approach` | How conversation begins | soft_intro, direct_ask, problem_solving, reminder |
| `negotiation_tactic` | Primary lever | payment_plan, settlement_offer, deadline, empathy |
| `escalation_style` | How pressure is applied | gradual, immediate, none |
| `concession_willingness` | Flexibility level | rigid, moderate, flexible |
| `compliance_adherence` | Regulatory adherence | strict, standard |
| `follow_up_strategy` | Proposed next steps | callback, written_agreement, immediate_payment |

### Initial Strategy Count
Phase 1: 4 strategies.
Phase 4: Expand as needed.

---

## 7. Data Storage

### SQLite — Single Denormalized Table

```sql
CREATE TABLE runs (
    id                      TEXT PRIMARY KEY,
    status                  TEXT NOT NULL,       -- "completed", "failed"
    error_message           TEXT,                -- null if completed
    profile_id              TEXT NOT NULL,
    strategy_id             TEXT NOT NULL,
    conversation_model      TEXT NOT NULL,
    judge_model             TEXT NOT NULL,
    started_at              TIMESTAMP NOT NULL,
    ended_at                TIMESTAMP,
    turn_count              INTEGER,
    ended_by                TEXT,                -- "collector", "debtor", "stalemate", "turn_limit"
    transcript_json         TEXT,                -- full message array as JSON
    judge_reasoning         TEXT,                -- free-text analysis from Judge pass 1
    payment_outcome         TEXT,
    payment_probability     REAL,
    debtor_satisfaction     REAL,
    compliance_score        REAL,
    conversation_efficiency INTEGER,
    rapport_built           REAL,
    escalation_risk         REAL,
    total_input_tokens      INTEGER,
    total_output_tokens     INTEGER,
    estimated_cost_usd      REAL
);
```

Design rationale:
- Single table, denormalized for analytical query speed.
- No joins needed for `GROUP BY profile_id, strategy_id, conversation_model`.
- Transcript stored as JSON text column (atomic per run).
- Judge reasoning stored separately for human review.
- Failed runs saved with `status="failed"` and `error_message`.
- Cost tracked per run from day one.

### Deep Store Interface

The store is a **deep module** — it owns analytical query patterns so that SQL
knowledge doesn’t leak into callers. Callers get domain objects, not raw rows.

| Method | Returns | Used by |
|--------|---------|---------|
| `save_run(run_result)` | `None` | Engine |
| `get_run(run_id)` | `RunResult` | CLI |
| `get_strategy_comparison(profile_id)` | `list[StrategyStats]` | Analyzer — scores grouped by strategy |
| `get_matrix_coverage()` | `dict[MatrixCell, int]` | Runner — how many completed per cell |
| `get_backfill_needed(target_reps)` | `list[MatrixCell]` | Runner — cells below target |
| `get_best_transcript(profile_id, strategy_id)` | `Transcript` | Playbook — highest-scoring exemplar |
| `get_all_transcripts(profile_id, strategy_id)` | `list[Transcript]` | Objection extraction |
| `get_compliance_summary(profile_id, strategy_id)` | `ComplianceStats` | Compliance module |
| `get_cost_summary()` | `CostSummary` | CLI reporting |
| `count_by_status()` | `dict[str, int]` | Batch end-of-run report |

All query methods filter to `status="completed"` unless explicitly told otherwise.
Schema changes stay in `store.py`; callers never write SQL.

---

## 8. Configuration

### File Structure
```
config/
├── debtor_profiles.yaml       # All debtor persona definitions
├── collector_strategies.yaml  # All collector strategy definitions
├── models.yaml                # Model pools, tiers, backends, concurrency
└── simulation.yaml            # Turn limits, reps, thresholds, objection taxonomy
```

### `models.yaml` Structure
```yaml
backends:
  nim:
    base_url: https://integrate.api.nvidia.com/v1
    # API key from NVIDIA_NIM_API_KEY env var
    max_concurrent_requests: 10
    rate_limit_rpm: 40
  cursor_sdk:
    # Auth from CURSOR_API_KEY env var
    # Bridge deps live in cursor_sdk_bridge/

tiers:
  judge:  # Tier 1
    models:
      - id: cursor-claude-opus-4.7
        backend: cursor_sdk
        provider: anthropic
        model_name: claude-opus-4-7
        input_cost_per_m: 0
        output_cost_per_m: 0
      - id: cursor-claude-sonnet-4.6
        backend: cursor_sdk
        provider: anthropic
        model_name: claude-sonnet-4-6
        input_cost_per_m: 0
        output_cost_per_m: 0
      - id: cursor-gemini-3.1-pro
        backend: cursor_sdk
        provider: google
        model_name: gemini-3.1-pro
        input_cost_per_m: 0
        output_cost_per_m: 0

  conversation:  # Tier 2
    models:
      - id: cursor-gpt-5.5
        backend: cursor_sdk
        provider: openai
        model_name: gpt-5.5
        input_cost_per_m: 0
        output_cost_per_m: 0
      - id: cursor-gemini-3-flash
        backend: cursor_sdk
        provider: google
        model_name: gemini-3-flash
        input_cost_per_m: 0
        output_cost_per_m: 0
      - id: nim-mistral-large-3-675b
        backend: nim
        provider: mistral
        model_name: openai/mistralai/mistral-large-3-675b-instruct-2512
        input_cost_per_m: 0
        output_cost_per_m: 0
      - id: nim-llama-4-maverick
        backend: nim
        provider: meta
        model_name: openai/meta/llama-4-maverick-17b-128e-instruct
        input_cost_per_m: 0
        output_cost_per_m: 0
      - id: nim-minimax-m2.7
        backend: nim
        provider: minimax
        model_name: openai/minimaxai/minimax-m2.7
        input_cost_per_m: 0
        output_cost_per_m: 0

  mechanical:  # Tier 3
    models:
      - id: nim-nemotron-3-super-120b
        backend: nim
        provider: nvidia
        model_name: openai/nvidia/nemotron-3-super-120b-a12b
        input_cost_per_m: 0
        output_cost_per_m: 0
      - id: nim-gemma-4-31b-it
        backend: nim
        provider: google
        model_name: openai/google/gemma-4-31b-it
        input_cost_per_m: 0
        output_cost_per_m: 0
```

### `simulation.yaml` Structure
```yaml
conversation:
  max_turns: 20
  end_signal: "[END_CONVERSATION]"
  stalemate:
    window: 3                     # consecutive turn pairs to compare
    similarity_threshold: 0.6     # SequenceMatcher ratio above this = repetitive

matrix:
  default_repetitions: 10
  adaptive_reps:
    enabled: true
    max_repetitions: 30
    significance_level: 0.05    # p-value threshold for Mann-Whitney U

compliance:
  min_compliance_score: 0.8     # below this → excluded from playbook
  max_escalation_risk: 0.3      # above this → excluded from playbook

retry:
  max_retries: 3
  backoff_base_seconds: 2       # exponential: 2s, 4s, 8s
  acp_crash_retries: 2
  judge_parse_retries: 2

objection_taxonomy:
  - inability_to_pay
  - disputes_debt
  - already_paid
  - needs_time
  - wants_written_proof
  - spouse_decision
  - threatens_legal_action
  - emotional_distress
  - avoidance
  - requests_callback
  - claims_identity_error
  - requests_supervisor
```

### Environment Variables
```
NVIDIA_NIM_API_KEY=...          # Free tier key from build.nvidia.com
CURSOR_API_KEY=...              # From Cursor dashboard (or use CURSOR_AUTH_TOKEN)
```

---

## 9. Analysis & Playbook

The old plan put all analysis in a single `analyzer.py`. That module would have
combined four unrelated concerns with different dependencies, change rates, and test
strategies. It is split into an `analysis/` package of **deep modules**, each with a
compact interface and focused implementation.

### Module: `analysis/statistics.py`
**Interface:** `compare_strategies(profile_id, store) -> StrategyRanking`

- Mann-Whitney U test (non-parametric, pairwise) to compare strategies per profile.
- Significance level: p < 0.05 (configurable).
- Bootstrap 95% confidence intervals reported alongside means.
- Strategies that cannot be separated after maximum reps are reported as
  **statistically tied** — no false winner forced.
- Adaptive resampling detection: identifies cells where the top two strategies are
  not yet significantly different, returns them as "needs more data."

**Dependencies:** scipy, numpy. No LLM calls. Fully deterministic.
**Test strategy:** synthetic score arrays with known statistical properties.

### Module: `analysis/objections.py`
**Interface:** `extract_objections(transcripts, taxonomy, router) -> ObjectionReport`

- Sends top-scoring transcripts to a Tier 2 model with an extraction prompt.
- Extracts structured objection/response pairs.
- Classifies each objection against the seeded taxonomy (~12 categories).
- Novel objections that don’t fit get a new category label from the LLM.
- Ranks responses per objection by the outcome score of their source conversation.
- Novel categories appear under “Other Objections Observed.”

**Dependencies:** LLMRouter (Tier 2 calls). This is the only analysis module with
an LLM dependency.
**Test strategy:** mock LLM responses, verify classification and ranking logic.

### Module: `analysis/compliance.py`
**Interface:** `check_exclusions(store, thresholds) -> list[ComplianceExclusion]`

- Any strategy scoring `compliance_score < min_compliance_score` (default 0.8)
  or `escalation_risk > max_escalation_risk` (default 0.3) for a given profile is
  excluded entirely from the playbook.
- Exclusion is per-(Profile, Strategy) pair, not global.
- Returns a list of exclusions with the triggering scores.

**Dependencies:** store only. Pure threshold logic.
**Test strategy:** synthetic score data, verify threshold boundaries.

### Module: `analysis/playbook.py`
**Interface:** `generate_playbook(rankings, objections, exclusions, store) -> str`

Takes the outputs of the other three modules and produces the Markdown playbook.
Owns only formatting — no statistical computation, no LLM calls, no business rules.

#### Playbook Structure
```markdown
# Collection Playbook
Generated: {date} | Runs analyzed: {n} | Statistical method: Mann-Whitney U

## Compliance Notice
Strategies excluded from this playbook due to compliance risk:
- {strategy_id} for {profile_id}: compliance={score}, escalation_risk={score}

## Profile: {profile_id}
### Recommended Strategy: {strategy_id}
**Payment Probability:** {mean}% (95% CI: {low}%–{high}%)
**Statistical Comparison:**
- vs {strategy_2}: p={p_value} (significant/not significant)
- vs {strategy_3}: p={p_value}

### Key Tactics
- {tactic_1}
- {tactic_2}

### Objection Playbook
| Objection | Best Response | Source Run | Outcome |
|-----------|--------------|------------|---------|
| "I can't afford it" | "I understand. Let's look at..." | run_abc | payment_plan, 82% prob |
| "I already paid this" | "I appreciate you telling me..." | run_def | promise_to_pay, 71% prob |

### What to Avoid
- {anti_pattern_1} (drops probability to {x}%)

### Example Transcript (Best Scoring)
> **Collector:** ...
> **Debtor:** ...
```

**Dependencies:** none beyond the data passed in.
**Test strategy:** snapshot tests — verify Markdown output against expected strings.

---

## 10. Error Handling & Resilience

### Retry Policy
| Error Type | Retries | Backoff | Action |
|-----------|---------|---------|--------|
| NIM rate limit (429) | 3 | Exponential (2s, 4s, 8s) | Retry same call |
| NIM timeout/network | 3 | Exponential | Retry same call |
| Cursor SDK bridge failure | 2 | Exponential | Retry current turn |
| Judge malformed JSON | 2 | None | Retry Judge call |
| Judge repair fallback | 1 | None | Send to Tier 3 for JSON repair |

### Failed Runs
- If a conversation fails irrecoverably mid-way, save partial transcript.
- Mark run as `status: "failed"` with `error_message` in database.
- Schedule a replacement run with the same config (same profile/strategy/model combo).
- Do NOT retry the whole conversation (LLM randomness means it's a different conversation).

### Batch Continuation
- Batch always continues on failure. Never halts.
- End-of-batch report: "{completed}/{total} runs completed, {failed} failed."
- Summary of failure reasons printed.
- Analyzer ignores failed runs.

---

## 11. CLI Interface

```bash
# Single conversation (interactive, prints transcript + scores)
collection-swarm simulate \
    --profile cooperative_hardship \
    --strategy empathetic_payment_plan \
    --conversation-model cursor-gemini-3-flash \
    --judge-model cursor-claude-sonnet-4.6

# Batch run with matrix slicing
collection-swarm run \
    --profiles cooperative_hardship,hostile_disputer \
    --strategies empathetic_payment_plan,assertive_settlement \
    --conversation-models cursor-gemini-3-flash,nim-mistral-large-3-675b \
    --judge-models cursor-claude-sonnet-4.6,cursor-gemini-3.1-pro \
    --reps 10 \
    --concurrency 4

# Full matrix (no filters = all × all × all)
collection-swarm run --reps 10

# Analyze results and generate playbook
collection-swarm analyze --output output/playbook.md

# Test backend connectivity
collection-swarm test-connection

# List available configs
collection-swarm list-profiles
collection-swarm list-strategies
```

---

## 12. Project Structure (Updated)

```
collection-swarm/
├── CONTEXT.md                     # Domain language
├── SPEC.md                        # Original specification
├── PLAN.md                        # This file — implementation decisions
├── pyproject.toml
├── requirements.txt
│
├── config/
│   ├── debtor_profiles.yaml
│   ├── collector_strategies.yaml
│   ├── models.yaml
│   └── simulation.yaml
│
├── src/
│   └── collection_swarm/
│       ├── __init__.py
│       ├── cli.py                 # Click CLI entry point
│       ├── models.py              # Pydantic data models
│       ├── config.py              # YAML config loading & validation
│       ├── backends/
│       │   ├── __init__.py
│       │   ├── base.py            # LLMResponse dataclass, Backend protocol
│       │   ├── nim.py             # NimBackend (LiteLLM + NVIDIA NIM)
│       │   ├── cursor_sdk.py      # CursorSdkBackend (@cursor/sdk bridge)
│       │   └── router.py          # LLMRouter (dispatches to backends)
│       ├── agents/                    # Each agent owns its prompts (no prompts/ package)
│       │   ├── __init__.py
│       │   ├── collector.py       # Prompt construction + LLM call + response handling
│       │   ├── debtor.py          # Prompt construction + LLM call + response handling
│       │   └── judge.py           # Two-pass LLM scoring + constraint verification
│       ├── engine.py              # Conversation loop, all end-detection (deterministic)
│       ├── runner.py              # Batch runner, matrix generation, concurrency
│       ├── store.py               # Deep store: CRUD + analytical query methods
│       └── analysis/              # Split from single analyzer.py
│           ├── __init__.py
│           ├── statistics.py      # Mann-Whitney U, CIs, strategy ranking
│           ├── objections.py      # LLM-driven extraction, taxonomy management
│           ├── compliance.py      # Exclusion threshold logic (pure functions)
│           └── playbook.py        # Markdown generation from analyzed results
│
├── output/                        # Generated playbooks (gitignored)
│
└── tests/
    ├── __init__.py
    ├── test_models.py             # Pydantic model validation (incl. structured constraints)
    ├── test_config.py             # Config loading and validation
    ├── test_engine.py             # Conversation loop, stalemate heuristic, end-detection
    ├── test_store.py              # CRUD + analytical queries
    ├── test_runner.py             # Matrix generation, slicing, backfill
    ├── test_statistics.py         # Mann-Whitney U, CIs, tie detection
    ├── test_objections.py         # Extraction, taxonomy classification
    ├── test_compliance.py         # Threshold boundaries, per-pair exclusion
    ├── test_playbook.py           # Markdown snapshot tests
    ├── test_judge.py              # Constraint verification logic
    └── test_backends.py           # Router dispatch, NIM integration
```

---

## 13. Testing Strategy

### Methodology
**Red-Green TDD with vertical slices.** One test → one implementation → repeat.
No horizontal slicing (all tests first, then all code).

### What We Test (Deterministic, Through Public Interfaces)

Each module is tested through its own public interface. The test file mirrors the
module it covers. No test crosses module seams except through the public interface.

| Test file | Module interface under test | LLM mocking? |
|-----------|---------------------------|---------------|
| `test_models.py` | Pydantic validation, structured constraint rules | No |
| `test_config.py` | YAML parsing, model pool construction, validation | No |
| `test_engine.py` | Turn alternation, signal parsing, stalemate heuristic, `ended_by` | Yes (agent calls) |
| `test_store.py` | CRUD + all analytical query methods, domain object returns | No |
| `test_runner.py` | Matrix generation, CLI slicing, backfill detection | No |
| `test_statistics.py` | Mann-Whitney U, CIs, tie detection, adaptive rep detection | No |
| `test_objections.py` | Extraction prompt → classification → ranking pipeline | Yes (Tier 2 calls) |
| `test_compliance.py` | Threshold boundaries, per-(Profile, Strategy) exclusion | No |
| `test_playbook.py` | Markdown output from pre-computed analysis results | No |
| `test_judge.py` | Programmatic constraint verification (deterministic) | No (verification step only) |
| `test_backends.py` | Router dispatch, correct backend selected per model | No |

Key improvement: 6 of 11 test files need **zero LLM mocking**. The old structure
would have required mocking in engine, analyzer, and judge tests. Splitting the
analysis modules and making end-detection deterministic isolates the LLM boundary.

### What We Don't Test in CI
- LLM response quality (non-deterministic)
- Judge scoring calibration (non-deterministic)
- Cursor SDK live agent behavior (integration, manual)

### Integration Testing
- `collection-swarm test-connection` CLI command: one quick exchange against each
  configured backend to verify connectivity.

---

## 14. Development Phases

### Phase 1 — Foundation (TDD, NIM-first)
Build and test the entire core against NVIDIA NIM (free, HTTP, easy to test).

1. **Pydantic data models** — Profile (with structured Constraint Rules), Strategy,
   ModelConfig, Message, Transcript, Judgment, RunResult
2. **Config loading** — YAML parsing for profiles (including constraint rules),
   strategies, models, simulation settings
3. **NimBackend** — LiteLLM + NVIDIA NIM integration, LLMResponse
4. **LLMRouter** — dispatch to NimBackend (CursorSdkBackend added in Phase 2)
5. **Agent modules** — Collector, Debtor, Judge (each owns its prompts internally;
   no separate prompts/ package)
6. **Constraint verification** — deterministic verification step inside Judge module;
   tested independently via `test_judge.py`
7. **Conversation engine** — turn loop, full history, signal parsing, deterministic
   stalemate heuristic (SequenceMatcher), `ended_by` tracking
8. **SQLite store** — CRUD + analytical query methods (strategy comparison, matrix
   coverage, best transcript, compliance summary, cost summary)
9. **`simulate` CLI command** — single run, print transcript + scores

### Phase 2 — Cursor SDK + Scale
Add Cursor model access and batch execution.

10. **CursorSdkBackend** — invoke `@cursor/sdk` through the Node bridge and integrate into LLMRouter
11. **Batch runner** — matrix generation, CLI slicing filters, hybrid concurrency
    (async NIM + Cursor SDK calls). Uses store’s `get_backfill_needed()` for
    replacement scheduling.
12. **Retry/resilience** — exponential backoff, partial saves, continue-on-failure
13. **`run` CLI command** — batch execution with Rich progress bars
14. **`test-connection` CLI command**

### Phase 3 — Analysis & Playbook
Four focused modules instead of one monolithic analyzer.

15. **`analysis/statistics.py`** — Mann-Whitney U, bootstrap CIs, adaptive rep detection
16. **`analysis/compliance.py`** — per-(Profile, Strategy) exclusion logic
17. **`analysis/objections.py`** — LLM-driven transcript mining, taxonomy management
18. **`analysis/playbook.py`** — Markdown generation from analyzed results
19. **`analyze` CLI command** — orchestrates all four modules

### Phase 4 — Polish
20. Expand to 15+ profiles, refine strategies
21. Conversation guardrails (off-topic detection)
22. `list-profiles`, `list-strategies` CLI commands
23. Documentation and README

---

## 15. Key Constraints & Principles

- **Minimal external API keys.** Cursor SDK uses `CURSOR_API_KEY`; NVIDIA NIM uses its free-tier API key.
- **FDCPA compliance baked in.** All collector prompts include compliance guardrails.
  Non-compliant strategies are excluded from playbook output.
- **No real consumer data.** All profiles are synthetic.
- **TDD vertical slices.** Never write all tests first. One behavior at a time.
- **Test behavior, not implementation.** Tests use public interfaces, survive refactors.
- **Cost-aware but not cost-blocked.** Track spending, use cheaper models where sufficient,
  but never compromise simulation quality to save money.
