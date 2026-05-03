# Scripted Backend

**Module:** `src/collection_swarm/backends/scripted.py`

The `ScriptedBackend` is a **deterministic, offline backend** that requires no API keys or network access. It uses keyword-matching heuristics to generate contextually appropriate responses for all three agent roles, making the application fully functional without any LLM provider.

---

## Class: `ScriptedBackend`

```python
class ScriptedBackend:
    backend_name = "scripted"

    async def complete(
        self,
        model: ModelConfig,
        messages: list[LLMMessage],
    ) -> LLMResponse
```

### When to Use

- **Development:** rapid iteration without API costs or latency
- **Testing:** deterministic outputs for reproducible test suites
- **CI/CD:** automated pipelines where external API access is unavailable
- **Demos:** showcasing the system architecture without credentials

---

## Role Detection

The backend determines which role to emulate by inspecting the **system prompt** (first message):

```
┌─────────────────────────────┐
│ System prompt inspection    │
│                             │
│ Contains "judge" /          │
│ "evaluator" / "juiz"?       │──── Yes ──→ _judge_response()
│                             │
│ Contains "you are the       │
│ debtor" / "você é o         │
│ devedor"?                   │──── Yes ──→ _debtor_response()
│                             │
│ Default                     │──────────→ _collector_response()
└─────────────────────────────┘
```

| Priority | Markers (case-insensitive) | Detected Role |
|---|---|---|
| 1st | `judge`, `evaluator`, `juiz avaliador` | Judge |
| 2nd | `you are the debtor`, `você é o devedor` | Debtor |
| 3rd | _(default)_ | Collector |

!!! info "Anchored debtor detection"
    The debtor match is anchored on the opening phrase (`"you are the debtor"` / `"você é o devedor"`) so it doesn't get falsely triggered by passing references to "devedor" inside the collector's system prompt.

---

## Token Counting

The scripted backend estimates tokens using whitespace splitting:

```python
LLMResponse(
    input_tokens=sum(len(message.content.split()) for message in messages),
    output_tokens=len(content.split()),
    estimated_cost_usd=0.0,  # Always free
    model_id=model.id,
    backend="scripted",
)
```

---

## Collector Response Logic

```python
def _collector_response(self, system: str, history: str) -> str
```

The collector response is **tactic-aware** — it inspects the strategy keywords in the system prompt to tailor its opening, then adapts based on the conversation state.

### Opening Tactic Selection

| Strategy Keywords in System Prompt | Opening Tactic |
|---|---|
| `payment_plan`, `parcelamento`, `parcela`, `micro_installment`, `cashflow`, `cash_flow`, `low_entry`, `assisted_official_channel` | `"combinar uma parcela que caiba no seu bolso"` (find an affordable installment) |
| `settlement`, `settlement_offer`, `acordo`, `à vista`, `a vista` | `"ver um acordo com desconto à vista"` (explore a lump-sum discount) |
| _(default)_ | `"encontrar o próximo passo de pagamento que faça sentido"` (find a sensible next step) |

### Conversation State Handling

| State Detection | Response |
|---|---|
| No debtor messages yet | Opening greeting with tactic-specific phrasing |
| Agreement keywords detected (`topo`, `fechado`, `posso pagar`, `will pay`, etc.) | Confirms the agreement via official boleto, includes `[END_CONVERSATION]` signal |
| Hardship/proof keywords + micro-installment strategy | Offers low-entry boleto via official liquidator channels |
| Hardship/proof keywords (general) | Offers to send detailed invoice and contract via official channels |
| _(default)_ | Asks for a realistic amount or date |

!!! example "Brazilian Portuguese throughout"
    All scripted collector responses are in Brazilian Portuguese, reflecting the Will Bank liquidation context. Example opening:

    > *"Olá, aqui é Alex falando em nome do liquidante do Will Bank. Quero entender sua situação e ver se conseguimos combinar uma parcela que caiba no seu bolso, sem pressão."*

---

## Debtor Response Logic

```python
def _debtor_response(self, system: str, history: str) -> str
```

The debtor response is **profile-aware** — it inspects the system prompt for archetype keywords and generates behavior consistent with that profile.

### Profile-Based Responses

| Profile Keywords | Behavior | Example Response |
|---|---|---|
| `dispute`, `written proof`, `wants_written_proof`, `disputer` | Demands written documentation before discussing payment | *"Antes de falar de pagamento, preciso da fatura detalhada e do contrato por escrito..."* |
| `scam`, `suspects_scam`, `distrustful`, `skeptical` | Demands official channel verification | *"Como sei que isso não é golpe? Me passe o nome do liquidante..."* |
| `hardship`, `can_pay_partial`, `temporary_liquidity_block` | Offers small payments within constraints | *"Não consigo pagar tudo, mas R$ 100 por mês eu topo se for em boleto."* |
| `angry`, `hostile`, `avoidance`, `avoidant` | Ends the call immediately | *"Cansei dessas ligações. Manda tudo por escrito. [END_CONVERSATION]"* |
| `confused`, `questions_validity` | Asks for clarification about the debt | *"Achei que com o Will tendo quebrado eu nem precisava pagar..."* |
| _(default)_ | Cooperative — promises to pay this week | *"Esqueci esse boleto. Se me mandarem a confirmação por escrito, eu pago essa semana."* |

### State-Dependent Branching

Several profiles have **two-phase behavior** that checks whether a prior condition has been met:

=== "Disputer"

    **Phase 1** (proof not yet provided):
    > *"Preciso da fatura detalhada e do contrato por escrito pra confirmar essa cobrança."*

    **Phase 2** (proof keywords in history):
    > *"Quando eu receber e revisar a documentação a gente fala. Hoje eu não vou me comprometer. [END_CONVERSATION]"*

=== "Scam Suspect"

    **Phase 1** (official channel not yet cited):
    > *"Como sei que isso não é golpe? Me passe o nome do liquidante e o canal oficial."*

    **Phase 2** (official channel in history):
    > *"Vou confirmar essas informações nos canais oficiais e te retorno. [END_CONVERSATION]"*

=== "Hardship (blocked funds)"

    **Phase 1** (no low-entry offer yet):
    > *"Meu dinheiro ficou bloqueado, então só consigo algo pequeno e por boleto oficial."*

    **Phase 2** (low-entry boleto offered):
    > *"R$ 80 por mês no boleto registrado cabe pra mim. Pode mandar por escrito. [END_CONVERSATION]"*

---

## Judge Response Logic

```python
def _judge_response(self, history: str) -> str
```

The judge generates a **JSON `Judgment` object** based on keyword analysis of the full conversation history.

### Outcome Classification

| History Keywords | `payment_outcome` | `payment_probability` |
|---|---|---|
| `payment plan`, `per month`, `por mês`, `parcela`, `boleto registrado` | `payment_plan` | `0.72` |
| `payment this week`, `will pay`, `vou pagar`, `pago essa semana` | `promise_to_pay` | `0.65` |
| `not committing`, `send me everything in writing`, `manda tudo por escrito`, `não vou me comprometer` | `no_commitment` | `0.25` |
| _(default)_ | `no_commitment` | `0.35` |

### Static Score Values

All heuristic judgments use the same baseline scores:

| Field | Value |
|---|---|
| `debtor_satisfaction` | `0.68` |
| `compliance_score` | `0.95` |
| `rapport_built` | `0.62` |
| `escalation_risk` | `0.08` |
| `conversation_efficiency` | Turn count from transcript |
| `end_reason` | `"agreement_reached"` (if payment plan or promise) or `"debtor_deferred"` |
| `constraint_violations` | `[]` (empty — deterministic check runs separately) |

### Output Format

The judge returns valid JSON that can be parsed by the Judge agent's `_parse_judgment` function:

```json
{
  "reasoning": "Heuristic local judge based on the transcript outcome and tone.",
  "payment_outcome": "payment_plan",
  "payment_probability": 0.72,
  "debtor_satisfaction": 0.68,
  "compliance_score": 0.95,
  "conversation_efficiency": 6,
  "rapport_built": 0.62,
  "escalation_risk": 0.08,
  "end_reason": "agreement_reached",
  "constraint_violations": []
}
```

---

## Related

- [Backend Overview](overview.md) — the `LLMBackend` protocol
- [LLM Router](router.md) — how `"scripted"` and `"heuristic"` map to this backend
- [Judge](../agents/judge.md) — how the JSON output is parsed and verified
