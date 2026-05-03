# `backends/scripted.py` — the deterministic offline backend

<span class="cs-kicker">collection_swarm/backends/scripted.py</span>

A 215-line backend that produces realistic, role-aware Brazilian-Portuguese
turns and a heuristic JSON Judgment without any network calls. It is the
default `scripted` and `heuristic` backend, the engine the test suite
runs against, and what makes the project usable end-to-end with zero API
keys.

<dl class="cs-summary">
  <dt>Imports</dt><dd>standard library only</dd>
  <dt>Network</dt><dd>None</dd>
  <dt>Determinism</dt><dd>Pure function of the input messages — same input always produces the same output</dd>
</dl>

## Public surface

```python
class ScriptedBackend:
    backend_name = "scripted"

    async def complete(self, model: ModelConfig, messages: list[LLMMessage]) -> LLMResponse: ...
```

That's it. The same class instance answers for both the `scripted` and
`heuristic` backend slots.

## Role detection

The backend infers the role from the system message:

- "judge" / "evaluator" / "juiz avaliador" → Judge response.
- "you are the debtor" / "você é o devedor" → Debtor response.
- Anything else → Collector response.

The Debtor anchor matches on the opening English/Portuguese phrase so
casual mentions of "devedor" inside the Collector prompt don't cause a
false positive.

## Collector responses

The Collector heuristic looks at the system prompt for a tactic hint and
at the history for what the Debtor most recently said:

- If the system prompt mentions a payment plan / parcelamento /
  micro-installment / cashflow tactic, the Collector framing leans on
  installments.
- If the system prompt mentions settlement / acordo / discount, the
  framing leans on a one-shot discount.
- If the history contains agreement markers ("topo", "fechado", "vou
  pagar", etc.), the Collector closes with a written-confirmation line
  and the `[END_CONVERSATION]` signal.
- If the history contains hardship / written-proof / scam markers, the
  Collector defers to the official channel and offers a smaller entry
  amount.
- Otherwise it asks an open-ended next-step question.

This is enough realism to drive every test case in the suite, the
seed data generator, and the CLI demos.

## Debtor responses

Branches on the system prompt tags:

| Branch                                          | Behavior                                                                            |
| ----------------------------------------------- | ----------------------------------------------------------------------------------- |
| `dispute` / `wants_written_proof` / `disputer`   | Demands fatura detalhada + contrato; defers commitment until validation arrives.   |
| `scam` / `suspects_scam` / `distrustful`         | Asks for the liquidante name and an official channel before any payment talk.       |
| `hardship` / `can_pay_partial` / `temporary_liquidity_block` | Offers a small installment under the constraint ceiling.                |
| `angry` / `hostile` / `avoidance`                | Asks to receive everything in writing; ends with the signal.                        |
| `confused` / `questions_validity`                | Asks the Collector to explain how the post-liquidation collection works.            |
| Default                                          | Cooperative "I forgot, send the confirmation in writing" response.                  |

When the Debtor commits to an installment value, the value is always
under the strictest Constraint ceiling shipped with the canonical
profiles (R$ 80/mês for the cooperative hardship persona) so the
deterministic verifier never flags the scripted runs as constraint
violations.

## Judge response

Returns a JSON payload like:

```json
{
  "reasoning": "Heuristic local judge based on the transcript outcome and tone.",
  "payment_outcome": "payment_plan",
  "payment_probability": 0.72,
  "debtor_satisfaction": 0.68,
  "compliance_score": 0.95,
  "conversation_efficiency": 5,
  "rapport_built": 0.62,
  "escalation_risk": 0.08,
  "end_reason": "agreement_reached",
  "constraint_violations": []
}
```

The outcome is picked from the transcript:

- Payment-plan markers ("payment plan", "por mês", "parcela", "boleto
  registrado") → `payment_plan`, probability 0.72.
- Will-pay markers ("vou pagar", "pago essa semana") → `promise_to_pay`,
  probability 0.65.
- Refusal markers ("send everything in writing", "não vou me
  comprometer") → `no_commitment`, probability 0.25.
- Otherwise → `no_commitment`, probability 0.35.

## Token accounting

```python
input_tokens=sum(len(message.content.split()) for message in messages),
output_tokens=len(content.split()),
estimated_cost_usd=0.0,
```

A word-count proxy. It's not accurate against any provider's tokenizer,
but it's stable across runs and lets the engine display non-zero token
counts during demos.

## When you should not use it

The scripted backend is great for tests and demos. It is **not** a
substitute for live evaluation. The Playbook generated from scripted
runs reflects the heuristic, not the real model — treat scripted runs
as plumbing, not insight.
