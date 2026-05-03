# Models

> **Module:** `collection_swarm.models`
> **Source:** `src/collection_swarm/models.py`

The models module defines all domain types for Collection Swarm using Pydantic
`BaseModel` classes. It contains enums, data models, configuration schemas,
validators, and utility functions shared across the entire application.

---

## Enums

### `PaymentOutcome`

Classifies the result of a debt collection conversation.

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

| Value | Description |
|-------|-------------|
| `FULL_PAYMENT` | Debtor agrees to pay the full amount. |
| `PARTIAL_PAYMENT` | Debtor agrees to pay a reduced amount. |
| `PAYMENT_PLAN` | Debtor agrees to an installment plan. |
| `PROMISE_TO_PAY` | Debtor verbally commits to future payment. |
| `NO_COMMITMENT` | Conversation ended without any payment commitment. |
| `REFUSAL` | Debtor explicitly refuses to pay. |
| `HANG_UP` | Debtor terminates the call abruptly. |

### `EndedBy`

Indicates which party or mechanism ended the simulation.

```python
class EndedBy(StrEnum):
    COLLECTOR = "collector"
    DEBTOR = "debtor"
    STALEMATE = "stalemate"
    TURN_LIMIT = "turn_limit"
```

| Value | Description |
|-------|-------------|
| `COLLECTOR` | The collector agent emitted `[END_CONVERSATION]`. |
| `DEBTOR` | The debtor agent emitted `[END_CONVERSATION]`. |
| `STALEMATE` | The engine detected repetitive dialogue. |
| `TURN_LIMIT` | The conversation hit `max_turns`. |

---

## Core Domain Models

### `Profile`

Represents a debtor persona used in simulations.

```python
class Profile(BaseModel):
    id: str
    archetype: str
    financial_situation: str
    debt_amount: float          # Field(gt=0)
    debt_age_days: int          # Field(ge=0)
    debt_type: str
    prior_contact_count: int    # Field(ge=0)
    emotional_state: str
    primary_objection: str
    responsiveness: str
    demographics: str
    backstory: str
    constraints: list[Constraint] = []
```

| Field | Type | Constraints | Description |
|-------|------|------------|-------------|
| `id` | `str` | — | Unique identifier. |
| `archetype` | `str` | — | Category label (e.g., `"single_parent"`, `"disputer"`). |
| `financial_situation` | `str` | — | Description of debtor's finances. |
| `debt_amount` | `float` | `> 0` | Outstanding debt in currency units. |
| `debt_age_days` | `int` | `≥ 0` | Days since the debt was incurred. |
| `debt_type` | `str` | — | Category of debt (e.g., `"credit_card"`, `"medical"`). |
| `prior_contact_count` | `int` | `≥ 0` | Number of previous collection attempts. |
| `emotional_state` | `str` | — | Starting emotional state. |
| `primary_objection` | `str` | — | Main reason the debtor resists payment. |
| `responsiveness` | `str` | — | How cooperative the debtor tends to be. |
| `demographics` | `str` | — | Demographic context for the persona. |
| `backstory` | `str` | — | Narrative background for the LLM to embody. |
| `constraints` | `list[Constraint]` | — | Behavioral rules the debtor must follow. |

#### Property: `account_data -> AccountData`

Returns a lightweight `AccountData` object with just the financial fields,
suitable for passing to the collector agent.

```python
account = profile.account_data
# AccountData(debt_amount=2500.0, debt_age_days=90, ...)
```

---

### `AccountData`

Minimal financial data for the collector's context.

```python
class AccountData(BaseModel):
    debt_amount: float      # Field(gt=0)
    debt_age_days: int      # Field(ge=0)
    debt_type: str
    prior_contact_count: int  # Field(ge=0)
```

---

### `Strategy`

Behavioral configuration for the collector agent.

```python
class Strategy(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Required fields
    id: str
    tone: str
    opening_approach: str
    negotiation_tactic: str
    escalation_style: str
    concession_willingness: str
    compliance_adherence: str
    follow_up_strategy: str

    # Optional fields (Will Bank / Brazilian context)
    payment_channel: str | None = None
    primary_anchor: str | None = None
    discovery_questions: str | None = None
    framing: str | None = None
    discount_authority: str | None = None
    liquidation_disclosure: str | None = None
    cultural_register: str | None = None
    rationale: str | None = None
```

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique strategy identifier. |
| `tone` | Yes | Communication style (e.g., `"warm"`, `"firm"`, `"neutral"`). |
| `opening_approach` | Yes | How the collector begins the conversation. |
| `negotiation_tactic` | Yes | Primary negotiation method. |
| `escalation_style` | Yes | How pressure is applied if debtor resists. |
| `concession_willingness` | Yes | How readily the collector offers concessions. |
| `compliance_adherence` | Yes | Level of regulatory compliance. |
| `follow_up_strategy` | Yes | Post-conversation follow-up plan. |
| `payment_channel` | No | Preferred payment method (e.g., `"pix_or_boleto"`). |
| `primary_anchor` | No | Initial price anchor for negotiation. |
| `discovery_questions` | No | Type of discovery questions to use. |
| `framing` | No | How the debt situation is framed. |
| `discount_authority` | No | Level of discount the collector can offer. |
| `liquidation_disclosure` | No | Whether to disclose liquidation context. |
| `cultural_register` | No | Cultural and linguistic register. |
| `rationale` | No | Explanation of the strategy's design philosophy. |

!!! note "Extra fields ignored"
    `ConfigDict(extra="ignore")` ensures that legacy or unknown fields in YAML
    do not cause validation errors.

---

### `Constraint` and `ConstraintRule`

Behavioral constraints attached to debtor profiles. The judge uses these to
assess compliance violations.

```python
class Constraint(BaseModel):
    text: str
    rule: ConstraintRule | None = None

class ConstraintRule(BaseModel):
    type: Literal["max_payment", "required_action"]
    amount: float | None = None
    frequency: str | None = None
    action: str | None = None
```

#### `ConstraintRule` Types

| Type | Required Fields | Description |
|------|-----------------|-------------|
| `"max_payment"` | `amount` | The debtor cannot pay more than this amount. |
| `"required_action"` | `action` | An action that must occur before payment discussion. |

#### `ConstraintRule` Validation

A `model_validator` ensures type-specific fields are present:

- `max_payment` rules **must** have `amount` set.
- `required_action` rules **must** have `action` set.

```python
@model_validator(mode="after")
def validate_required_fields(self) -> "ConstraintRule":
    if self.type == "max_payment" and self.amount is None:
        raise ValueError("max_payment constraint rules require amount")
    if self.type == "required_action" and not self.action:
        raise ValueError("required_action constraint rules require action")
    return self
```

#### Supported `action` Values

| Action | Description |
|--------|-------------|
| `demand_written_proof` | Debtor must mention written proof before discussing payment. |
| `cite_liquidator_and_official_channel` | Collector must reference the liquidator or an official channel before requesting payment. |
| `provide_official_boleto_path` | Collector must mention an official boleto or validation channel. |
| `verify_official_channel` | Collector must mention an official channel before debtor engages. |

---

### `Message`

A single message in a conversation transcript.

```python
class Message(BaseModel):
    role: Literal["collector", "debtor", "system", "judge"]
    content: str
```

### `LLMMessage`

A message formatted for LLM API calls (uses standard OpenAI-style roles).

```python
class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
```

---

### `Judgment`

The judge's evaluation of a completed conversation.

```python
class Judgment(BaseModel):
    reasoning: str
    payment_outcome: PaymentOutcome = PaymentOutcome.NO_COMMITMENT
    payment_probability: float      # Field(ge=0.0, le=1.0)
    debtor_satisfaction: float      # Field(ge=0.0, le=1.0)
    compliance_score: float         # Field(ge=0.0, le=1.0)
    conversation_efficiency: int    # Field(ge=0)
    rapport_built: float            # Field(ge=0.0, le=1.0)
    escalation_risk: float          # Field(ge=0.0, le=1.0)
    end_reason: str = "no_resolution"
    constraint_violations: list[str] = []
```

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `reasoning` | `str` | — | Free-text explanation of the judgment. |
| `payment_outcome` | `PaymentOutcome` | enum | Categorized result. |
| `payment_probability` | `float` | 0.0–1.0 | Likelihood the debtor will actually pay. |
| `debtor_satisfaction` | `float` | 0.0–1.0 | How satisfied the debtor feels. |
| `compliance_score` | `float` | 0.0–1.0 | Regulatory compliance rating. |
| `conversation_efficiency` | `int` | ≥ 0 | Number of turns needed. Lower is better. |
| `rapport_built` | `float` | 0.0–1.0 | Quality of relationship established. |
| `escalation_risk` | `float` | 0.0–1.0 | Risk of debtor escalation. Lower is better. |
| `end_reason` | `str` | — | Human-readable description of why the conversation ended. |
| `constraint_violations` | `list[str]` | — | List of violated constraint descriptions. |

---

### `SimulationResult`

The complete output of a single simulation run.

```python
class SimulationResult(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str                              # default: "sim_{uuid}"
    status: Literal["completed", "failed", "running"] = "completed"
    error_message: str | None = None
    profile_id: str
    strategy_id: str
    conversation_model: str
    judge_model: str
    started_at: datetime                 # default: utc_now()
    ended_at: datetime | None = None
    turn_count: int = 0
    ended_by: EndedBy | None = None
    transcript: list[Message] = []
    judgment: Judgment | None = None
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    estimated_cost_usd: float = 0.0
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Auto-generated UUID-based ID (e.g., `"sim_a1b2c3d4e5f6"`). |
| `status` | `str` | `"completed"`, `"failed"`, or `"running"`. |
| `error_message` | `str \| None` | Error details if `status == "failed"`. |
| `profile_id` | `str` | The debtor profile used. |
| `strategy_id` | `str` | The collector strategy used. |
| `conversation_model` | `str` | Model ID for collector/debtor agents. |
| `judge_model` | `str` | Model ID for the judge. |
| `started_at` | `datetime` | UTC timestamp when the simulation began. |
| `ended_at` | `datetime \| None` | UTC timestamp when the simulation ended. |
| `turn_count` | `int` | Total number of messages. |
| `ended_by` | `EndedBy \| None` | What caused the simulation to end. |
| `transcript` | `list[Message]` | Ordered conversation messages. |
| `judgment` | `Judgment \| None` | Judge's evaluation (null if not yet judged). |
| `total_input_tokens` | `int` | Cumulative input tokens. |
| `total_output_tokens` | `int` | Cumulative output tokens. |
| `estimated_cost_usd` | `float` | Running cost estimate. |

#### Validators

**`parse_datetime`** — Accepts ISO 8601 strings and converts them to `datetime`:

```python
@field_validator("started_at", "ended_at", mode="before")
@classmethod
def parse_datetime(cls, value):
    if isinstance(value, str):
        return datetime.fromisoformat(value)
    return value
```

**`ensure_timezone`** — Adds UTC timezone if missing:

```python
@field_validator("started_at", "ended_at")
@classmethod
def ensure_timezone(cls, value):
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
```

---

## Analytics Models

### `StrategyStats`

Aggregated performance metrics for a strategy against a specific profile.

```python
class StrategyStats(BaseModel):
    profile_id: str
    strategy_id: str
    simulation_count: int
    mean_payment_probability: float
    mean_compliance_score: float
    mean_escalation_risk: float
```

### `MatrixCell`

Represents a single combination in the simulation matrix. Frozen (hashable) for
use as dictionary keys.

```python
class MatrixCell(BaseModel, frozen=True):
    profile_id: str
    strategy_id: str
    conversation_model: str
    judge_model: str
```

---

## Elo Rating Models

### `EloRating`

Current Elo state for a strategy or profile.

```python
class EloRating(BaseModel):
    entity_type: Literal["strategy", "profile"]
    entity_id: str
    conversation_model: str = ""
    judge_model: str = ""
    rating: float = 1500.0
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    draws: int = 0
```

The default rating of **1500** is the standard Elo starting point. Ratings are
scoped by `(entity_type, entity_id, conversation_model, judge_model)` so that
the same strategy can have different ratings when evaluated by different model
combinations.

### `EloUpdate`

A single rating change event.

```python
class EloUpdate(BaseModel):
    entity_type: Literal["strategy", "profile"]
    entity_id: str
    opponent_id: str
    conversation_model: str = ""
    judge_model: str = ""
    simulation_id: str
    rating_before: float
    rating_after: float
    effective_score: float
    expected_score: float
    timestamp: datetime     # default: utc_now()
```

### `DRAW_THRESHOLD`

```python
DRAW_THRESHOLD = 0.05
```

Games where `effective_score` is within ±0.05 of 0.5 are classified as draws.

---

## Tournament Models

### `TournamentConfig`

Configuration for a tournament run.

```python
class TournamentConfig(BaseModel):
    format: Literal["round_robin", "swiss"] = "swiss"
    rounds: int = 4                # Field(ge=1)
    reps_per_pairing: int = 1      # Field(ge=1)
    k_factor_initial: float = 32.0
    k_factor_stable: float = 16.0
    k_factor_threshold: int = 30
    scoring: Literal["payment_x_compliance", "payment_only"] = "payment_x_compliance"
```

| Field | Default | Description |
|-------|---------|-------------|
| `format` | `"swiss"` | Pairing algorithm. |
| `rounds` | `4` | Number of tournament rounds. |
| `reps_per_pairing` | `1` | Simulations per pairing per round. |
| `k_factor_initial` | `32.0` | Elo K-factor for new entities. |
| `k_factor_stable` | `16.0` | Elo K-factor after threshold games. |
| `k_factor_threshold` | `30` | Games before switching from initial to stable K-factor. |
| `scoring` | `"payment_x_compliance"` | Score formula: either `payment_probability × compliance_score` or `payment_probability` alone. |

### `TournamentResult`

Output of a completed tournament.

```python
class TournamentResult(BaseModel):
    id: str                     # default: "tourn_{uuid}"
    config: TournamentConfig
    rounds_completed: int = 0
    total_games: int = 0
    started_at: datetime        # default: utc_now()
    completed_at: datetime | None = None
    total_cost_usd: float = 0.0
```

---

## Evolution Models

### `EvolutionConfig`

Controls the evolutionary strategy optimization loop.

```python
class EvolutionConfig(BaseModel):
    population_size: int = 20       # Field(ge=1)
    top_k: int = 3                  # Field(ge=1)
    bottom_k: int = 3              # Field(ge=1)
    cull_bottom_n: int = 3         # Field(ge=0)
    mutation_rate: float = 0.5     # Field(ge=0.0, le=1.0)
    crossover_rate: float = 0.3    # Field(ge=0.0, le=1.0)
    evolver_model_id: str | None = None
```

| Field | Default | Description |
|-------|---------|-------------|
| `population_size` | `20` | Target population after evolution and culling. |
| `top_k` | `3` | Number of top performers selected as parents. |
| `bottom_k` | `3` | Number of bottom performers analyzed for failure patterns. |
| `cull_bottom_n` | `3` | Number of weakest evolved strategies to remove each generation. |
| `mutation_rate` | `0.5` | Probability of mutating individual strategy fields. |
| `crossover_rate` | `0.3` | Probability of combining fields from two parent strategies. |
| `evolver_model_id` | `None` | LLM to use for generating mutations. Falls back to default. |

### `StrategyLineage`

Tracks the evolutionary history of a strategy.

```python
class StrategyLineage(BaseModel):
    strategy_id: str
    parent_ids: list[str] = []
    generation: int = 0
    mutation_type: str = "seed"
    mutation_description: str = ""
    created_at: datetime        # default: utc_now()
    culled_at: datetime | None = None
```

### `ProfileLineage`

Tracks the hardening history of a profile.

```python
class ProfileLineage(BaseModel):
    profile_id: str
    parent_id: str | None = None
    generation: int = 0
    hardening_type: str = "seed"
    hardening_description: str = ""
    created_at: datetime        # default: utc_now()
    culled_at: datetime | None = None
```

### `HardeningConfig`

Controls adversarial profile hardening.

```python
class HardeningConfig(BaseModel):
    enabled: bool = False
    hardener_model_id: str | None = None
    max_drift: float = 200.0
    realism_check: bool = False
```

| Field | Default | Description |
|-------|---------|-------------|
| `enabled` | `False` | Whether profile hardening runs during evolution cycles. |
| `hardener_model_id` | `None` | LLM for generating harder profiles. |
| `max_drift` | `200.0` | Maximum allowed deviation from the parent profile. |
| `realism_check` | `False` | Whether to validate hardened profiles for realism. |

---

## Configuration Models

### `ModelConfig`

LLM model definition.

```python
class ModelConfig(BaseModel):
    id: str
    backend: str
    provider: str = "local"
    input_cost_per_m: float = 0.0
    output_cost_per_m: float = 0.0
    model_name: str | None = None
```

| Field | Default | Description |
|-------|---------|-------------|
| `id` | — | Unique model identifier. |
| `backend` | — | Backend type: `"litellm"`, `"scripted"`, `"heuristic"`, etc. |
| `provider` | `"local"` | Provider name (e.g., `"openai"`, `"anthropic"`). |
| `input_cost_per_m` | `0.0` | Cost per million input tokens. |
| `output_cost_per_m` | `0.0` | Cost per million output tokens. |
| `model_name` | `None` | Override for the LiteLLM model string. |

#### Property: `litellm_model -> str`

Returns `model_name` if set, otherwise falls back to `id`.

### `ConversationSettings`

```python
class ConversationSettings(BaseModel):
    max_turns: int = 20                         # Field(ge=2)
    end_signal: str = "[END_CONVERSATION]"
    stalemate_window: int = 3                   # Field(ge=1)
    stalemate_similarity_threshold: float = 0.6 # Field(ge=0.0, le=1.0)
```

### `ArenaSettings`

```python
class ArenaSettings(BaseModel):
    default_format: Literal["swiss", "round_robin"] = "swiss"
    default_rounds: int = 4                      # Field(ge=1)
    k_factor_initial: float = 32.0
    k_factor_stable: float = 16.0
    k_factor_threshold: int = 30
    scoring: Literal["payment_x_compliance", "payment_only"] = "payment_x_compliance"
```

### `SimulationSettings`

Top-level simulation configuration.

```python
class SimulationSettings(BaseModel):
    conversation: ConversationSettings
    default_repetitions: int = 1    # Field(ge=1)
    min_compliance_score: float = 0.8
    max_escalation_risk: float = 0.3
    objection_taxonomy: list[str] = []
    arena: ArenaSettings
```

---

## Prompt Configuration Models

### `CollectorPromptConfig`

```python
class CollectorPromptConfig(BaseModel):
    system: str
    history_empty: str
    history: str
```

### `DebtorPromptConfig`

```python
class DebtorPromptConfig(BaseModel):
    system: str
    constraints_empty: str = "- None"
    history_message: str
```

### `JudgePromptConfig`

```python
class JudgePromptConfig(BaseModel):
    system: str
    transcript: str
```

### `CursorSdkPromptConfig`

```python
class CursorSdkPromptConfig(BaseModel):
    preamble: str
```

### `PromptConfig`

Aggregates all prompt configurations.

```python
class PromptConfig(BaseModel):
    collector: CollectorPromptConfig
    debtor: DebtorPromptConfig
    judge: JudgePromptConfig
    cursor_sdk: CursorSdkPromptConfig
```

---

## Utility Functions

### `utc_now`

```python
def utc_now() -> datetime:
    return datetime.now(timezone.utc)
```

Returns the current UTC datetime. Used throughout the codebase as the canonical
timestamp factory to ensure consistent timezone handling.

### `model_dump_jsonable`

```python
def model_dump_jsonable(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
```

Serializes a Pydantic model to a JSON-compatible dictionary. Uses `mode="json"`
to ensure all types (datetimes, enums, etc.) are converted to JSON-native types.

```python
>>> from collection_swarm.models import Message, model_dump_jsonable
>>> msg = Message(role="collector", content="Hello")
>>> model_dump_jsonable(msg)
{'role': 'collector', 'content': 'Hello'}
```

---

## Model Hierarchy

```
BaseModel
├── PaymentOutcome (StrEnum)
├── EndedBy (StrEnum)
├── ConstraintRule
├── Constraint
├── AccountData
├── Profile
├── Strategy
├── Message
├── LLMMessage
├── Judgment
├── SimulationResult
├── StrategyStats
├── MatrixCell (frozen)
├── EloRating
├── EloUpdate
├── TournamentConfig
├── TournamentResult
├── StrategyLineage
├── ProfileLineage
├── EvolutionConfig
├── HardeningConfig
├── ModelConfig
├── ConversationSettings
├── ArenaSettings
├── SimulationSettings
├── CollectorPromptConfig
├── DebtorPromptConfig
├── JudgePromptConfig
├── CursorSdkPromptConfig
└── PromptConfig
```
