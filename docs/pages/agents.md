---
title: Agents
layout: default
nav_order: 5
---

# Agents
{: .no_toc }

The three AI participants: Collector, Debtor, and Judge.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Source:** `src/collection_swarm/agents/`

## Overview

The `agents` package contains three classes — `CollectorAgent`, `DebtorAgent`, and `Judge` — that transform domain objects (strategies, profiles, transcripts) into LLM prompts and parse the responses back into structured data.

All three agents delegate actual model calls to the `LLMRouter`, making them backend-agnostic.

---

## CollectorAgent

**Source:** `src/collection_swarm/agents/collector.py`

The `CollectorAgent` generates the collector's side of the conversation. It builds prompts from a `CollectorPromptConfig` and the current strategy/account context.

### Constructor

```python
CollectorAgent(router: LLMRouter, model_id: str, prompts: CollectorPromptConfig)
```

### Method: `generate_turn`

```python
async def generate_turn(
    self,
    strategy: Strategy,
    account: AccountData,
    history: list[Message],
) -> LLMResponse
```

**Prompt construction:**

1. **System prompt** — Built by formatting `prompts.system` with the strategy object and account data. This injects the strategy's tone, tactic, escalation style, and all other behavioral knobs, plus the account's debt amount, type, age, and prior contacts.

2. **User prompt** — If the conversation history is empty, uses `prompts.history_empty` (e.g., "Inicie a conversa como agente de cobrança"). Otherwise, formats the full transcript as `Role: Content` lines using `prompts.history`.

The agent sends these two messages to the router and returns the raw `LLMResponse`.

### Prompt Template Variables

| Variable | Source | Example |
|:---------|:-------|:--------|
| `{strategy.tone}` | Strategy | `empathetic` |
| `{strategy.opening_approach}` | Strategy | `soft_intro` |
| `{strategy.negotiation_tactic}` | Strategy | `payment_plan` |
| `{strategy.escalation_style}` | Strategy | `none` |
| `{strategy.concession_willingness}` | Strategy | `flexible` |
| `{strategy.follow_up_strategy}` | Strategy | `written_agreement` |
| `{account.debt_amount:,.2f}` | AccountData | `850.00` |
| `{account.debt_type}` | AccountData | `credito_pessoal_will` |
| `{account.debt_age_days}` | AccountData | `75` |
| `{account.prior_contact_count}` | AccountData | `1` |

---

## DebtorAgent

**Source:** `src/collection_swarm/agents/debtor.py`

The `DebtorAgent` generates the debtor's side of the conversation. It builds prompts from a `DebtorPromptConfig` and the debtor's profile.

### Constructor

```python
DebtorAgent(router: LLMRouter, model_id: str, prompts: DebtorPromptConfig)
```

### Method: `generate_turn`

```python
async def generate_turn(
    self,
    profile: Profile,
    history: list[Message],
) -> LLMResponse
```

**Prompt construction:**

1. **System message** — Built by formatting `prompts.system` with the full profile (archetype, financial situation, emotional state, backstory, demographics, etc.) and the profile's constraints formatted as a bullet list.

2. **History messages** — The conversation history is converted to alternating `user`/`assistant` messages: debtor turns become `assistant` (so the model continues as the debtor), and collector turns become `user`. This leverages the LLM's native turn structure.

### History Message Mapping

| Simulation Role | LLM Role | Rationale |
|:----------------|:---------|:----------|
| `debtor` | `assistant` | The model is the debtor, so its prior outputs are `assistant` turns |
| `collector` | `user` | The collector's messages are treated as the "user" input to respond to |

This mapping is critical for correct in-context learning — the model sees its own prior debtor responses as things it said, maintaining persona consistency.

### Constraint Injection

Profile constraints are injected into the system prompt as a bullet list:

```
Restrições rígidas que você NÃO pode violar, sob nenhuma pressão:
- Nunca aceitará parcela acima de R$ 80 por mês.
- Não passará dados de cartão ou senha por telefone.
- Só aceitará pagar por boleto registrado em nome da Will Financeira / liquidante.
```

If the profile has no constraints, the fallback text `"- Nenhuma"` is used.

---

## Judge

**Source:** `src/collection_swarm/agents/judge.py`

The `Judge` evaluates a completed transcript and produces a structured `Judgment`. It combines LLM-based scoring with deterministic constraint verification.

### Constructor

```python
Judge(router: LLMRouter, model_id: str, prompts: JudgePromptConfig)
```

### Method: `evaluate`

```python
async def evaluate(
    self,
    transcript: list[Message],
    profile: Profile,
) -> Judgment
```

**Process:**

1. Build the system prompt from `prompts.system`.
2. Build the user prompt from `prompts.transcript`, injecting account data, constraint descriptions, and the formatted transcript.
3. Call the LLM via the router.
4. **Parse the response** into a `Judgment` using `_parse_judgment()`.
5. **Verify constraints deterministically** using `verify_constraints()`.
6. **Merge** LLM-detected and deterministic constraint violations (deduplicating).

### JSON Parsing and Normalization

The judge response is expected to be a JSON object. The parser:

1. Extracts JSON from the response by finding the first `{` and last `}`.
2. Normalizes `payment_outcome` values using an alias map (e.g., `"payment_plan_agreed"` → `payment_plan`, `"refused"` → `refusal`).
3. Rescales score fields if they appear to be on a 0–100 or 0–10 scale instead of 0–1.
4. If parsing fails entirely, returns a **fallback judgment** with neutral scores and `end_reason = "judge_parse_failed"`.

### Payment Outcome Aliases

The normalizer handles many common LLM variations:

| Raw Output | Normalized To |
|:-----------|:-------------|
| `payment_plan_agreed`, `payment_plan_accepted`, `payment_arrangement` | `payment_plan` |
| `promise`, `promise_made`, `promised` | `promise_to_pay` |
| `paid_in_full`, `settled_in_full` | `full_payment` |
| `pending`, `in_progress`, `ongoing`, `no_resolution` | `no_commitment` |
| `refused` | `refusal` |
| `hangup` | `hang_up` |

### Deterministic Constraint Verification

`verify_constraints()` checks profile constraints against the actual transcript content:

#### `max_payment` Constraints
- Scans debtor text for agreement utterances (in both English and Portuguese) using regex.
- Extracts payment amounts from matched text.
- Flags violations when agreed amounts exceed the constraint's `amount` field.
- Handles both US (`$1,234.56`) and Brazilian (`R$ 1.234,56`) number formats.

#### `required_action` Constraints
- **`demand_written_proof`**: Checks if the debtor mentioned written proof, validation, fatura detalhada, contrato, etc.
- **`cite_liquidator_and_official_channel`**: Checks if the collector mentioned the liquidator (EFB), official channels (willbank.com.br, bcb.gov.br), or Banco Central.
- **`provide_official_boleto_path`** / **`verify_official_channel`**: Same as above, checking collector text.

### Agreement Pattern Detection

The regex pattern for detecting debtor payment agreements handles:

- English: "I can do $200", "I will pay 50", "I agree to..."
- Portuguese: "posso pagar R$ 80", "topo R$ 100", "fechado em 150 reais"
- With or without currency symbols
- US and Brazilian number formatting

```python
_AGREEMENT_PATTERN = re.compile(
    r"\b(?:i can|i could|i will|posso pagar|aceito pagar|topo|...)\b"
    r"[^.\n]{0,80}?"
    r"(?:r\$\s*|\$\s*)?"
    r"(\d[\d.,]*)"
    r"(?:\s*reais)?",
    re.IGNORECASE,
)
```
