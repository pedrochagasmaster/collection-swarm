# `agents/judge.py` — the Judge evaluator

<span class="cs-kicker">collection_swarm/agents/judge.py</span>

Two responsibilities, one module:

1. **LLM Judge** — render the system + transcript prompt, send to the
   Judge model, parse the JSON response into a `Judgment`.
2. **Deterministic verifier** — re-walk the transcript against every
   Profile Constraint that has a structured `rule` and append any
   violations the LLM may have missed.

The two outputs are merged before the `Judgment` returns.

<dl class="cs-summary">
  <dt>Imports</dt><dd>standard library, Pydantic, backend types, router, domain models</dd>
  <dt>Visibility</dt><dd>Sees the full Transcript, the Profile's Constraints, and Account Data; never sees the Strategy or Profile Tags</dd>
  <dt>Stateful?</dt><dd>Yes — caches the last <code>LLMResponse</code> on <code>self.last_response</code> so the engine can fold its tokens / cost into the result</dd>
</dl>

## `Judge.evaluate()`

```python
async def evaluate(self, transcript: list[Message], profile: Profile) -> Judgment:
    response = await self.router.complete(
        self.model_id,
        [
            LLMMessage(role="system", content=_system_prompt(self.prompts)),
            LLMMessage(role="user", content=_transcript_prompt(self.prompts, transcript, profile)),
        ],
    )
    self.last_response = response
    judgment = _parse_judgment(response.content, len(transcript))
    violations = verify_constraints(transcript, profile)
    merged = list(dict.fromkeys([*judgment.constraint_violations, *violations]))
    return judgment.model_copy(update={"constraint_violations": merged})
```

`dict.fromkeys` is the deduplication idiom: it preserves order and
removes duplicates without sorting.

## The system prompt

`prompts.judge.system` is a long Brazilian-Portuguese instruction that:

- Establishes the Will Bank liquidation framing and the regulatory
  lattice (CDC art. 42 and 71, Lei 14.181/2021, Resolução CMN 4.949/2021,
  Normativo SARB nº 27/2023).
- Reminds the model that legitimate collection identifies the liquidante,
  uses boleto registrado, and never asks for Pix or sensitive data.
- Demands a single JSON object response with no Markdown fences and a
  bounded `reasoning` field.

The transcript prompt formats the Account Data, the Constraints, and the
turn-by-turn transcript with `.format(account=..., constraints=...,
transcript=...)`.

## `_parse_judgment(content, turn_count)`

A defensive parser:

1. Calls `_extract_json(content)` to slice from the first `{` to the
   last `}` — works even if the model drifts into prose around its
   answer.
2. `json.loads` the slice.
3. Calls `_normalize_judgment_data(data)` to:
   - Lower-case and snake-case the `payment_outcome` value.
   - Map a long alias table (`"settlement"` → `partial_payment`,
     `"plan"` → `payment_plan`, `"hangup"` → `hang_up`, etc.).
   - Detect score values on a 0–10 or 0–100 scale and divide accordingly
     (the Judge sometimes returns "compliance: 95" meaning 95% — the
     normalizer divides by 100 for any score field with a value > 1).
4. Pins `conversation_efficiency = turn_count` regardless of what the
   model wrote.
5. Validates against `Judgment`.

If anything raises (`json.JSONDecodeError`, `ValidationError`, custom
`ValueError`), the parser returns a fallback `Judgment` with
`payment_probability=0.0`, `compliance_score=0.5`, `escalation_risk=0.5`,
and `end_reason="judge_parse_failed"`. That distinct end_reason is the
flag downstream tooling looks for.

## Deterministic constraint verification

```python
def verify_constraints(transcript: list[Message], profile: Profile) -> list[str]: ...
```

Walks every `Constraint.rule` and adds a string to the `violations` list
when the rule fires.

### `max_payment` rule

For every Constraint with `rule.type == "max_payment"`:

1. Concatenate every Debtor utterance.
2. Run the agreement regex below over it.
3. Parse the captured number with `_parse_brazilian_or_us_number()` —
   handles `1.234,56` (BR) and `1,234.56` (US) correctly by inspecting
   which separator appears last.
4. If any parsed amount exceeds `rule.amount`, append:

   ```
   Debtor agreed to {amount}, exceeding max payment constraint of {limit}.
   ```

The regex is deliberately liberal:

```python
_AGREEMENT_PATTERN = re.compile(
    r"\b(?:i can|i could|i will|i'll|i agree|agree to|can do|will pay|"
    r"posso pagar|consigo pagar|aceito pagar|topo|combinado em|fechado em|"
    r"vou pagar|pago)\b"
    r"[^.\n]{0,80}?"
    r"(?:r\$\s*|\$\s*)?"
    r"(\d[\d.,]*)"
    r"(?:\s*reais)?",
    re.IGNORECASE,
)
```

It matches both English and Brazilian-Portuguese agreement utterances, with
or without a currency symbol. The `[^.\n]{0,80}?` middle clause keeps it
within the same sentence-ish span to avoid stitching a verb on one line
with a number on another.

### `required_action` rules

Three known actions:

| Action                                       | Verifier checks                                                              |
| -------------------------------------------- | ----------------------------------------------------------------------------- |
| `demand_written_proof`                       | Debtor text mentions written proof / "fatura detalhada" / "contrato" / etc.  |
| `cite_liquidator_and_official_channel` and aliases | Collector text mentions the liquidante, "willbank.com.br", "bcb.gov.br", "Banco Central", "boleto registrado", or "canal oficial". |

Each verifier is a simple `any(phrase in text for phrase in [...])` over
a curated phrase list. The lists are intentionally short and tuned to
the Brazilian context — extend them if you add new locales.

If the action is missing where required, the verifier appends:

- `"Debtor never demanded written proof despite required_action constraint."`
- `"Collector never disclosed an official validation or payment channel."`

## Public symbols

| Symbol                | Purpose                                            |
| --------------------- | --------------------------------------------------- |
| `Judge`               | Class with `evaluate()` and `last_response`.       |
| `verify_constraints`  | Pure function used by `Judge.evaluate` and tests.  |

`_parse_judgment`, `_agreed_amounts`, `_mentions_written_proof`, and
`_mentions_official_channel` are private but their names are stable;
they're covered directly by the test suite.
