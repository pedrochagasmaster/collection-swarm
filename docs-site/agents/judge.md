# Judge

**Module:** `src/collection_swarm/agents/judge.py`

The `Judge` is the **evaluator agent** in the simulation. After a conversation between the Collector and Debtor completes, the Judge reads the full transcript and produces a structured `Judgment` containing scores, outcome classification, and constraint violation analysis.

The Judge uses a **two-pass evaluation pipeline**: an LLM-based qualitative scoring pass followed by a deterministic constraint verification pass.

---

## Class: `Judge`

### Constructor

```python
class Judge:
    def __init__(
        self,
        router: LLMRouter,
        model_id: str,
        prompts: JudgePromptConfig,
    ) -> None
```

| Parameter | Type | Description |
|---|---|---|
| `router` | `LLMRouter` | Backend dispatcher — routes completions to the configured LLM backend |
| `model_id` | `str` | Identifier for the model to use (must exist in the router's model registry) |
| `prompts` | `JudgePromptConfig` | Prompt templates for the system message and transcript formatting |

The Judge also maintains a `last_response` attribute (`LLMResponse | None`) that stores the raw LLM response from the most recent evaluation, useful for debugging and inspection.

### `JudgePromptConfig`

Defined in `models.py`:

```python
class JudgePromptConfig(BaseModel):
    system: str       # System prompt — defines the judge's evaluation criteria
    transcript: str   # Transcript template — interpolated with {account}, {constraints}, {transcript}
```

---

## Method: `evaluate`

```python
async def evaluate(
    self,
    transcript: list[Message],
    profile: Profile,
) -> Judgment
```

The primary evaluation method. Performs a two-pass analysis:

1. **LLM scoring pass** — sends the transcript to the LLM for qualitative evaluation
2. **Deterministic constraint verification** — runs static rule checks against the transcript

| Parameter | Type | Description |
|---|---|---|
| `transcript` | `list[Message]` | The complete conversation transcript |
| `profile` | `Profile` | The debtor profile (used for constraint rules and account data) |

**Returns:** A `Judgment` object with merged violations from both passes.

### Evaluation Pipeline

```
┌────────────────────┐     ┌─────────────────────┐
│  LLM Scoring Pass  │     │ Deterministic Check  │
│                    │     │                     │
│ system + transcript│     │ verify_constraints() │
│ → JSON judgment    │     │ → violation list     │
└────────┬───────────┘     └──────────┬──────────┘
         │                            │
         └──────────┬─────────────────┘
                    │
            ┌───────▼────────┐
            │  Merge & Dedup │
            │  violations    │
            └───────┬────────┘
                    │
              ┌─────▼──────┐
              │  Judgment   │
              └────────────┘
```

```python
async def evaluate(self, transcript, profile) -> Judgment:
    # Pass 1: LLM scoring
    response = await self.router.complete(self.model_id, [
        LLMMessage(role="system", content=_system_prompt(self.prompts)),
        LLMMessage(role="user", content=_transcript_prompt(
            self.prompts, transcript, profile
        )),
    ])
    self.last_response = response
    judgment = _parse_judgment(response.content, len(transcript))

    # Pass 2: Deterministic constraint verification
    violations = verify_constraints(transcript, profile)

    # Merge: LLM-found violations + deterministic violations, deduplicated
    merged = list(dict.fromkeys([
        *judgment.constraint_violations,
        *violations,
    ]))
    return judgment.model_copy(update={"constraint_violations": merged})
```

!!! tip "Deduplication via `dict.fromkeys`"
    The merge uses `dict.fromkeys` to preserve insertion order while removing duplicates. LLM-found violations appear first, followed by any deterministic violations not already present.

---

## Prompt Construction

### System Prompt

```python
def _system_prompt(prompts: JudgePromptConfig) -> str:
    return prompts.system.strip()
```

The system prompt is used as-is (no interpolation) — it defines the judge's persona and evaluation rubric.

### Transcript Prompt

```python
def _transcript_prompt(prompts, transcript, profile) -> str:
    lines = "\n".join(
        f"{turn.role.title()}: {turn.content}" for turn in transcript
    )
    constraints = "\n".join(
        f"- {constraint.text}" for constraint in profile.constraints
    ) or "- none"
    account = profile.account_data
    return prompts.transcript.format(
        account=account,
        constraints=constraints,
        transcript=lines,
    ).strip()
```

The transcript prompt includes three pieces of information:

| Variable | Source | Content |
|---|---|---|
| `{account}` | `profile.account_data` | `AccountData` — debt amount, age, type, prior contacts |
| `{constraints}` | `profile.constraints` | Bulleted list of constraint texts (or `"- none"`) |
| `{transcript}` | Formatted transcript | `"Role: content"` lines for each turn |

!!! info "Information boundaries"
    The Judge sees the `AccountData`, `constraints`, and `transcript` — but **never** sees the collector's `Strategy`. This ensures the judge evaluates the conversation's outcome and compliance without bias toward the intended collection approach.

---

## Function: `verify_constraints`

```python
def verify_constraints(
    transcript: list[Message],
    profile: Profile,
) -> list[str]
```

A **static function** (not a method on Judge) that performs deterministic constraint checking. This runs independently of the LLM and catches violations that the LLM might miss.

### Supported Constraint Rules

#### `max_payment` — Payment Amount Limits

Checks whether the debtor agreed to pay more than the allowed amount.

```python
ConstraintRule(type="max_payment", amount=150.0, frequency="monthly")
```

**How it works:**

1. Extracts all debtor text from the transcript
2. Applies a regex pattern to find agreement utterances with amounts
3. Parses amounts using Brazilian or US number format
4. Flags any amount exceeding `rule.amount`

**Agreement Detection Regex:**

The regex matches agreement phrases in both English and Brazilian Portuguese:

| Language | Matched Phrases |
|---|---|
| English | `i can`, `i could`, `i will`, `i'll`, `i agree`, `agree to`, `can do`, `will pay` |
| Portuguese | `posso pagar`, `consigo pagar`, `aceito pagar`, `topo`, `combinado em`, `fechado em`, `vou pagar`, `pago` |

Amounts are extracted after optional currency symbols (`R$`, `$`) and support the `reais` suffix.

**Number Parsing (`_parse_brazilian_or_us_number`):**

| Format | Example | Parsed As |
|---|---|---|
| US with thousands | `1,234.56` | `1234.56` |
| Brazilian with thousands | `1.234,56` | `1234.56` |
| Brazilian decimal only | `80,00` | `80.00` |
| Comma as thousands only | `1,234` | `1234.0` |
| Plain integer | `200` | `200.0` |

!!! example "Detection example"
    Given debtor text: `"Posso pagar R$ 200 por mês"` with a `max_payment` constraint of `150.0`:

    - The regex matches `"posso pagar"` followed by `"R$ 200"`
    - `200.0 > 150.0` → violation: `"Debtor agreed to 200, exceeding max payment constraint of 150."`

#### `required_action` — Mandatory Behavioral Checks

Checks whether required conversational actions occurred.

| Action | Who Must Act | Keywords Checked |
|---|---|---|
| `demand_written_proof` | Debtor | `written proof`, `written validation`, `validate`, `validation notice`, `fatura detalhada`, `contrato`, `comprovante`, `documentação`, `prova documental`, `por escrito` |
| `cite_liquidator_and_official_channel` | Collector | `liquidante`, `liquidação`, `efb regimes`, `willbank.com.br`, `bcb.gov.br`, `banco central`, `boleto registrado`, `canal oficial`, `canais oficiais` |
| `provide_official_boleto_path` | Collector | _(same as above)_ |
| `verify_official_channel` | Collector | _(same as above)_ |

!!! warning "Actor distinction"
    - `demand_written_proof` checks the **debtor's** text — the debtor must have demanded proof.
    - The other three actions check the **collector's** text — the collector must have cited official channels.

    The violation messages reflect who failed to act:

    - `"Debtor never demanded written proof despite required_action constraint."`
    - `"Collector never disclosed an official validation or payment channel."`

---

## JSON Parsing: `_parse_judgment`

```python
def _parse_judgment(content: str, turn_count: int) -> Judgment
```

Extracts a `Judgment` from the LLM's response text.

### Parsing Steps

1. **Extract JSON** — finds the first `{` and last `}` in the response to isolate the JSON object
2. **Normalize data** — applies alias resolution and score scaling
3. **Set turn count** — overrides `conversation_efficiency` with the actual turn count
4. **Validate** — runs Pydantic validation to produce a `Judgment`

### Payment Outcome Alias Resolution

The LLM may return various strings for `payment_outcome`. These are normalized to the `PaymentOutcome` enum:

| LLM Output | Normalized To |
|---|---|
| `payment_plan_agreed`, `payment_plan_accepted`, `payment_arrangement` | `payment_plan` |
| `promise`, `promise_made`, `promised`, `promised_callback` | `promise_to_pay` |
| `paid_in_full`, `settled_in_full` | `full_payment` |
| `partial` | `partial_payment` |
| `pending`, `pending_verification`, `verification_pending`, `in_progress`, `ongoing`, `no_resolution`, `none`, `no_payment` | `no_commitment` |
| `refused` | `refusal` |
| `hangup` | `hang_up` |

Additionally, fuzzy matching handles unlisted values:

| Contains | Normalized To |
|---|---|
| `pending`, `ongoing`, `negotiating`, `negotiation` | `no_commitment` |
| `plan` | `payment_plan` |
| `partial`, `settlement` | `partial_payment` |

### Score Scaling

Score fields (`payment_probability`, `debtor_satisfaction`, `compliance_score`, `rapport_built`, `escalation_risk`) are expected in the 0.0–1.0 range. If the LLM returns values on a different scale, they are normalized:

| Detection | Scale | Action |
|---|---|---|
| Any score field > 10 | 0–100 scale | Divide all scores > 1 by 100 |
| Any score field > 1 but ≤ 10 | 0–10 scale | Divide all scores > 1 by 10 |
| All scores ≤ 1 | Already normalized | No action |

---

## Fallback Behavior

If the LLM response cannot be parsed (invalid JSON, validation error, or missing JSON entirely), a **default judgment** is returned:

```python
Judgment(
    reasoning="Judge returned unparseable output; fallback heuristic used. "
              f"Raw output: {content[:500]}",
    payment_outcome=PaymentOutcome.NO_COMMITMENT,
    payment_probability=0.0,
    debtor_satisfaction=0.5,
    compliance_score=0.5,
    conversation_efficiency=turn_count,
    rapport_built=0.0,
    escalation_risk=0.5,
    end_reason="judge_parse_failed",
)
```

!!! danger "Detecting fallback judgments"
    You can identify fallback judgments by checking for `end_reason == "judge_parse_failed"`. The `reasoning` field will contain the first 500 characters of the raw LLM output for debugging.

---

## The `Judgment` Model

```python
class Judgment(BaseModel):
    reasoning: str
    payment_outcome: PaymentOutcome      # Enum: 7 possible outcomes
    payment_probability: float           # 0.0–1.0
    debtor_satisfaction: float           # 0.0–1.0
    compliance_score: float              # 0.0–1.0
    conversation_efficiency: int         # Turn count
    rapport_built: float                 # 0.0–1.0
    escalation_risk: float              # 0.0–1.0
    end_reason: str                      # Why the conversation ended
    constraint_violations: list[str]     # Merged list of violations
```

### `PaymentOutcome` Enum

| Value | Description |
|---|---|
| `full_payment` | Debtor commits to paying the full amount |
| `partial_payment` | Debtor agrees to pay a reduced amount |
| `payment_plan` | Debtor agrees to an installment plan |
| `promise_to_pay` | Debtor promises to pay but no firm commitment |
| `no_commitment` | No concrete payment outcome |
| `refusal` | Debtor explicitly refuses to pay |
| `hang_up` | Debtor ends the call abruptly |

---

## Related

- [Agent Architecture Overview](overview.md) — how the three agents interact
- [Collector Agent](collector.md) — generates the collection side of the transcript
- [Debtor Agent](debtor.md) — generates the debtor side of the transcript
- [Scripted Backend](../backends/scripted.md) — the heuristic judge used for offline evaluation
