# Compliance & guardrails

Collection Swarm has three layers of compliance enforcement, in increasing
order of trust:

1. **Prompt-level guardrails.** The Collector and Debtor system prompts in
   `config/prompts.yaml` cite the relevant Brazilian regulation (CDC art.
   42 and 71, Lei 14.181/2021, Resolução CMN 4.949/2021, Normativo SARB nº
   27/2023, the BCB extrajudicial liquidation context). They tell the LLM
   what it can and cannot say.
2. **The LLM Judge.** After every Simulation, the Judge scores
   `compliance_score` and `escalation_risk` from 0 to 1 with the same
   regulatory context in its own system prompt. The Judge can also list
   Constraint Violations it observes.
3. **Deterministic constraint verification.** A pure Python check at
   [`agents/judge.py:verify_constraints`](../modules/agents/judge.md#deterministic-constraint-verification)
   re-reads the transcript and adds violations the LLM may have missed.
   This is what makes the system dependable for analysis: even a sloppy
   Judge cannot let a max-payment violation slip through.

## Layer 1 — Prompt guardrails

The Collector prompt explicitly forbids:

- Threats, coercion, exposure to ridicule, interference in work / rest /
  leisure (CDC art. 42 and 71).
- Forcing an agreement when over-indebtedness markers are present
  (Lei 14.181/2021 — direct the debtor to a conciliation hearing instead).
- Calls outside Mon–Fri 7am–9pm or Sat 9am–4pm; collecting debts older
  than 5 years (Normativo SARB nº 27/2023).
- Asking for passwords, app codes, or Pix payment.
- Promises that depend on the (non-operating) Will Bank app.

The Debtor prompt makes the Debtor scam-aware: they will refuse to share
card data over the phone, will only accept payment via boleto registrado
in the liquidante's name, and know about the BCB liquidation.

## Layer 2 — The LLM Judge

The Judge's system prompt asks it to consider the regulatory backdrop when
calculating `compliance_score` and `escalation_risk`. It returns a single
JSON object:

```json
{
  "reasoning": "...",
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

The parser at [`agents/judge.py`](../modules/agents/judge.md) is forgiving:
it tolerates trailing prose, score values on a 0–10 or 0–100 scale, alias
values for `payment_outcome` ("settlement" → `partial_payment`,
"plan" → `payment_plan`, etc.). When the response cannot be parsed, the
Judgment falls back to a flat heuristic with `end_reason="judge_parse_failed"`
so failure is visible downstream.

## Layer 3 — Deterministic Constraint verification

`verify_constraints(transcript, profile)` walks every Constraint with a
structured `rule`:

- `type=max_payment, amount=N, frequency=...` — scans the Debtor's
  utterances for agreement phrases ("posso pagar", "topo", "I can do",
  "I will pay") followed by a number. Numbers are parsed in either
  Brazilian (`1.234,56`) or US (`1,234.56`) format. If any parsed amount
  exceeds `N`, it adds a violation.
- `type=required_action, action=demand_written_proof` — if the Debtor
  text never mentions written proof, "fatura detalhada", "contrato",
  "prova documental", "por escrito", or one of a dozen other phrases,
  it adds a violation.
- `type=required_action, action=cite_liquidator_and_official_channel`
  (or `provide_official_boleto_path`, `verify_official_channel`) — if the
  Collector text never mentions the liquidante, "willbank.com.br",
  "bcb.gov.br", "Banco Central", or "boleto registrado", it adds a
  violation.

Violations from layer 2 and layer 3 are merged with `dict.fromkeys` so
order is preserved and duplicates removed.

## Compliance Exclusions

The analysis pipeline at
[`analysis/compliance.py`](../modules/analysis/compliance.md) enforces
two thresholds, configured in `config/simulation.yaml`:

```yaml
compliance:
  min_compliance_score: 0.8
  max_escalation_risk: 0.3
```

For every (Profile, Strategy) pair:

- If the **mean** `compliance_score` across all completed Simulations is
  below `min_compliance_score`, the pair is excluded.
- If the **mean** `escalation_risk` is above `max_escalation_risk`, the
  pair is excluded.

Excluded pairs surface as `ComplianceExclusion` objects with a `reason`
string, are listed at the top of the generated Playbook, and are omitted
from per-Profile recommendations downstream.

A Strategy can be excluded for one Profile and recommended for another —
exclusions are scoped to the pair, not the Strategy.

## The escape hatch

If you ever need to override the deterministic verifier (e.g., a real
debtor in a future variant *should* be allowed to agree above the
constraint), don't disable the verifier — change the Profile. The
verifier is the floor that makes Collection Swarm trustworthy as an
analytical tool. Failing-loud is a feature.
