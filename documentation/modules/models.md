# `models.py` — domain types

<span class="cs-kicker">collection_swarm/models.py</span>

Pydantic v2 models, enums, and a couple of constants. Every other module
imports from here and nothing inside this module imports from sibling
modules — it is the lowest layer of the stack.

<dl class="cs-summary">
  <dt>Imports</dt><dd>standard library + Pydantic only</dd>
  <dt>Side effects</dt><dd>None</dd>
  <dt>Stability</dt><dd>Stable; new fields added with defaults to preserve schema evolution</dd>
</dl>

## Enums

| Enum            | Members                                                                                         |
| --------------- | ----------------------------------------------------------------------------------------------- |
| `PaymentOutcome`| `full_payment`, `partial_payment`, `payment_plan`, `promise_to_pay`, `no_commitment`, `refusal`, `hang_up` |
| `EndedBy`       | `collector`, `debtor`, `stalemate`, `turn_limit`                                                 |

`PaymentOutcome` follows the order best-to-worst, which is the same order
the Playbook ranks outcomes when there are ties.

## Profile-side models

### `ConstraintRule`

The machine-readable counterpart of a Constraint's natural-language text.

```python
class ConstraintRule(BaseModel):
    type: Literal["max_payment", "required_action"]
    amount: float | None = None
    frequency: str | None = None
    action: str | None = None
```

A `model_validator` enforces:

- `type=max_payment` requires an `amount`.
- `type=required_action` requires a non-empty `action`.

The supported `action` values for the deterministic verifier are
documented inline in the source (`demand_written_proof`,
`cite_liquidator_and_official_channel`, `provide_official_boleto_path`,
`verify_official_channel`).

### `Constraint`

```python
class Constraint(BaseModel):
    text: str
    rule: ConstraintRule | None = None
```

The Debtor agent injects every `text` into the system prompt; the Judge's
deterministic verifier walks the `rule` (when present) over the
transcript.

### `AccountData` and `Profile`

`AccountData` is the slim subset visible to the Collector. `Profile` is
the full record, with constraints and persona fields. `Profile.account_data`
is a property that returns a fresh `AccountData` on each call — there is
no mutation hook.

The `prior_contact_count` is `Field(ge=0)` and `debt_amount` is
`Field(gt=0)`, so a misconfigured YAML fails loudly during
`load_app_config()` rather than at first call.

## Strategy

```python
class Strategy(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    tone: str
    opening_approach: str
    negotiation_tactic: str
    escalation_style: str
    concession_willingness: str
    compliance_adherence: str
    follow_up_strategy: str
    payment_channel: str | None = None
    primary_anchor: str | None = None
    discovery_questions: str | None = None
    framing: str | None = None
    discount_authority: str | None = None
    liquidation_disclosure: str | None = None
    cultural_register: str | None = None
    rationale: str | None = None
```

The first eight fields are the original behavioral knobs. The optional
fields are descriptive refinements added for the Will Bank context, all
gated behind `extra="ignore"` so legacy YAML keeps working unchanged.

## Conversation models

| Model                  | Purpose                                                                                |
| ---------------------- | -------------------------------------------------------------------------------------- |
| `Message`              | Domain-level turn with `role` ∈ {collector, debtor, system, judge} and string content.|
| `LLMMessage`           | Wire-level turn with `role` ∈ {system, user, assistant}, what the backends actually see. |
| `CollectorPromptConfig`, `DebtorPromptConfig`, `JudgePromptConfig`, `CursorSdkPromptConfig`, `PromptConfig` | Pydantic shells around `prompts.yaml` so prompt strings are validated at load time. |

## Settings

```python
class ConversationSettings(BaseModel):
    max_turns: int = 20
    end_signal: str = "[END_CONVERSATION]"
    stalemate_window: int = 3
    stalemate_similarity_threshold: float = 0.6
```

`SimulationSettings` wraps `ConversationSettings`, the default repetition
count, the compliance thresholds, the objection taxonomy, and the
`ArenaSettings`. The CLI default for `max_turns` is overridden in the
shipped `config/simulation.yaml` to `12`, which is plenty for collection
calls.

## Output models

### `Judgment`

```python
class Judgment(BaseModel):
    reasoning: str
    payment_outcome: PaymentOutcome = PaymentOutcome.NO_COMMITMENT
    payment_probability: float = Field(ge=0.0, le=1.0)
    debtor_satisfaction: float = Field(ge=0.0, le=1.0)
    compliance_score: float = Field(ge=0.0, le=1.0)
    conversation_efficiency: int = Field(ge=0)
    rapport_built: float = Field(ge=0.0, le=1.0)
    escalation_risk: float = Field(ge=0.0, le=1.0)
    end_reason: str = "no_resolution"
    constraint_violations: list[str] = Field(default_factory=list)
```

`conversation_efficiency` is an integer turn count, *not* a 0–1 score.
Easy to misread. The Judge module sets it from `len(transcript)`.

### `SimulationResult`

The top-level record. `model_config = ConfigDict(use_enum_values=True)`
so `model_dump_jsonable()` produces stringy enum values, which is what
the SQLite store and the dashboard expect.

The `started_at` / `ended_at` field validators accept ISO strings (so
results re-hydrate cleanly from SQLite) and force tzinfo to UTC if it's
missing.

`SimulationResult.id` defaults to a generated 12-hex-digit `sim_…`
identifier, so the dashboard can show a stable URL even before the row
is persisted.

## Tournament & evolution models

| Model                | Purpose                                                                  |
| -------------------- | ------------------------------------------------------------------------ |
| `MatrixCell`         | `(profile_id, strategy_id, conversation_model, judge_model)` tuple, frozen so it can be a dict key. |
| `EloRating`          | Current rating for a `(entity_type, entity_id, conversation_model, judge_model)` tuple. |
| `EloUpdate`          | A single Elo update event with rating before / after, expected & effective scores. |
| `TournamentConfig`   | Format, rounds, K-factors, scoring mode.                                |
| `TournamentResult`   | Aggregate result of a tournament run.                                   |
| `StrategyLineage`    | Generation, parent IDs, mutation type for an evolved Strategy.           |
| `EvolutionConfig`    | Population size, top-K / bottom-K cuts, mutation / crossover rates, evolver model. |
| `ProfileLineage`     | Generation, parent ID, hardening type for an evolved Profile.            |
| `HardeningConfig`    | Whether profile hardening is enabled, the hardener model, drift / realism guards. |

`DRAW_THRESHOLD = 0.05` is the symmetric band around 0.5 within which an
arena outcome counts as a draw for the win/loss tally.

## Helpers

```python
def utc_now() -> datetime: ...
def model_dump_jsonable(model: BaseModel) -> dict[str, Any]: ...
```

Use `utc_now()` everywhere instead of `datetime.now(timezone.utc)` so
freezing time in tests is a single seam. `model_dump_jsonable()` calls
`.model_dump(mode="json")` so `datetime`, enums, and other non-JSON
types come out as strings — the SQLite store and the dashboard rely on
this.
