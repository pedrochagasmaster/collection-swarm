# Configuration

All Collection Swarm behavior is driven by five YAML files in the `config/` directory. The `load_app_config()` function reads them at startup and returns an `AppConfig` object with validated profiles, strategies, models, prompts, and simulation settings.

```
config/
├── debtor_profiles.yaml       # Who the debtor is
├── collector_strategies.yaml  # How the collector behaves
├── models.yaml                # Which LLMs to use
├── prompts.yaml               # System and turn prompts for each role
└── simulation.yaml            # Conversation limits, compliance, arena, taxonomy
```

!!! info "Custom config directory"
    Pass `--config-dir /path/to/configs` to the CLI to load from a different directory. The default is `config/`.

---

## Debtor Profiles

**File:** `config/debtor_profiles.yaml`

Each profile defines a synthetic debtor persona with demographic context, financial situation, emotional state, and hard constraints the debtor will never violate.

### Structure

```yaml
profiles:
  - id: cooperative_hardship               # Unique identifier
    archetype: cooperative                  # Behavioral archetype
    financial_situation: hardship           # Financial capacity
    debt_amount: 850                        # Outstanding balance (R$)
    debt_age_days: 75                       # Days since first default
    debt_type: credito_pessoal_will         # Product type
    prior_contact_count: 1                  # Previous collection contacts
    emotional_state: anxious                # Emotional baseline
    primary_objection: inability_to_pay     # Main reason for non-payment
    responsiveness: high                    # Likelihood of engaging
    demographics: nordeste_classe_c_mae_provedora  # Sociodemographic tag
    backstory: |                            # Free-text background story
      Mãe provedora de Fortaleza-CE ...
    constraints:                            # Hard behavioral limits
      - text: Nunca aceitará parcela acima de R$ 80 por mês.
        rule:
          type: max_payment
          amount: 80
          frequency: monthly
      - text: Não passará dados de cartão ou senha por telefone.
```

### Field Reference

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier used in CLI flags and cross-references |
| `archetype` | string | Behavioral category: `cooperative`, `disputer`, `hostile`, `confused`, `skeptical`, `strategic`, `overwhelmed`, `anxious_hardship`, `pragmatic_micro_merchant`, `vulnerable_hardship`, `angry_waiting_for_reimbursement`, `low_digital_access` |
| `financial_situation` | string | Capacity: `hardship`, `can_pay_partial`, `can_pay_full`, `stable`, `insolvent`, `temporary_liquidity_block`, `irregular_income`, `essential_expenses_at_risk`, `asset_rich_cash_poor` |
| `debt_amount` | number | Outstanding balance in BRL |
| `debt_age_days` | integer | Days since the account first became delinquent |
| `debt_type` | string | Product originating the debt (e.g., `cartao_credito_will`, `credito_pessoal_will`, `fgts_antecipacao_will`) |
| `prior_contact_count` | integer | Number of previous collection attempts |
| `emotional_state` | string | Emotional baseline: `anxious`, `angry`, `confused`, `guarded`, `distrustful`, `detached`, `ashamed`, `calm`, `stressed_but_practical`, `fearful`, `uncertain`, `anxious_and_confused` |
| `primary_objection` | string | Principal reason the debtor resists payment (see objection taxonomy in `simulation.yaml`) |
| `responsiveness` | string | Engagement level: `high`, `medium`, `low` |
| `demographics` | string | Free-form sociodemographic descriptor |
| `backstory` | string | Narrative injected into the debtor system prompt |
| `constraints` | list | Hard rules the debtor will never break during simulation |

### Constraint Rules

Constraints can include an optional `rule` object for machine-parseable enforcement:

```yaml
constraints:
  - text: "Nunca aceitará parcela acima de R$ 80 por mês."
    rule:
      type: max_payment       # Rule type
      amount: 80              # Monetary threshold
      frequency: monthly      # Payment frequency
  - text: "Sempre exigirá fatura detalhada antes de discutir pagamento."
    rule:
      type: required_action
      action: demand_written_proof
  - text: "Não passará dados de cartão por telefone."
    # No rule — enforced by prompt only
```

| Rule Type | Fields | Description |
|---|---|---|
| `max_payment` | `amount`, `frequency` | Maximum acceptable payment amount per period |
| `required_action` | `action` | Action the debtor demands before proceeding |

---

## Collector Strategies

**File:** `config/collector_strategies.yaml`

Each strategy defines the collector's behavioral parameters: tone, opening approach, negotiation tactics, compliance posture, and cultural register.

### Structure

```yaml
strategies:
  - id: empathetic_payment_plan
    tone: empathetic
    opening_approach: soft_intro
    negotiation_tactic: payment_plan
    escalation_style: none
    concession_willingness: flexible
    compliance_adherence: strict
    follow_up_strategy: written_agreement
    payment_channel: boleto_registrado
    primary_anchor: parcela_alinhada_ao_dia_5
    discovery_questions: motivational_interviewing
    framing: gain_preservation_score_cpf
    discount_authority: low
    liquidation_disclosure: proactive
    cultural_register: brasileiro_acessivel_neutro
    rationale: |
      Para perfis de hardship o default deve ser empático ...
```

### Field Reference

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique identifier |
| `tone` | string | Conversational tone: `empathetic`, `assertive`, `neutral`, `calm_informative`, `friendly_brief`, `empathetic_practical`, `collaborative_businesslike`, `nonjudgmental_structured`, `calm_respectful`, `patient_step_by_step` |
| `opening_approach` | string | How the collector starts: `soft_intro`, `direct_ask`, `reminder`, `problem_solving`, `identification_and_disclosure`, `whatsapp_template`, `reassurance`, etc. |
| `negotiation_tactic` | string | Core tactic: `payment_plan`, `settlement_offer`, `payment_reminder`, `empathy_then_planning_prompt`, `defer_until_validated`, `link_to_self_negotiation_portal`, `refer_to_global_renegotiation`, `confirm_and_inform`, etc. |
| `escalation_style` | string | Escalation behavior: `none`, `gradual` |
| `concession_willingness` | string | Flexibility level: `low`, `moderate`, `flexible`, `highly_flexible` |
| `compliance_adherence` | string | Regulatory posture (always `strict` in shipped configs) |
| `follow_up_strategy` | string | Post-conversation action: `written_agreement`, `immediate_payment`, `digital_link_to_self_service`, `callback_with_implementation_intention`, `callback_after_validation`, etc. |
| `payment_channel` | string | Accepted payment method (typically `boleto_registrado`) |
| `primary_anchor` | string | Negotiation anchor point — the central value proposition or reference |
| `discovery_questions` | string | Questioning style: `motivational_interviewing`, `minimal`, `none`, `hardship_triage`, `cashflow_mapping`, etc. |
| `framing` | string | Behavioral economics framing: `gain_preservation_score_cpf`, `loss_aversion_perda_de_desconto`, `factual_personalized`, `factual_protective`, etc. |
| `discount_authority` | string | Discount flexibility: `none`, `low`, `medium` |
| `liquidation_disclosure` | string | When/how to disclose the bank liquidation: `proactive`, `leading` |
| `cultural_register` | string | Language register matching the target demographic |
| `rationale` | string | Design rationale (not injected into prompts — documentation only) |

---

## Models

**File:** `config/models.yaml`

Models are organized into two tiers: **conversation** (used for Collector and Debtor roles) and **judge** (used for the Judge role).

### Structure

```yaml
tiers:
  conversation:
    models:
      - id: local-scripted
        backend: scripted
        provider: local
        input_cost_per_m: 0
        output_cost_per_m: 0

      - id: nim-llama-4-maverick
        backend: nim
        provider: meta
        model_name: openai/meta/llama-4-maverick-17b-128e-instruct
        input_cost_per_m: 0
        output_cost_per_m: 0

      - id: cursor-gpt-5.5-medium
        backend: cursor_sdk
        provider: openai
        model_name: gpt-5.5
        input_cost_per_m: 0
        output_cost_per_m: 0

  judge:
    models:
      - id: local-judge
        backend: heuristic
        provider: local
        input_cost_per_m: 0
        output_cost_per_m: 0

      - id: cursor-claude-4.6-opus-high-thinking
        backend: cursor_sdk
        provider: anthropic
        model_name: claude-opus-4-6
        input_cost_per_m: 0
        output_cost_per_m: 0
```

### Field Reference

| Field | Type | Description |
|---|---|---|
| `id` | string | Unique model identifier used in CLI flags |
| `backend` | string | Routing backend: `scripted`, `heuristic`, `nim`, `cursor_sdk` |
| `provider` | string | Model provider: `local`, `meta`, `mistral`, `minimax`, `openai`, `anthropic`, `cursor` |
| `model_name` | string | Provider-facing model identifier (not needed for `scripted` / `heuristic`) |
| `input_cost_per_m` | number | Cost per million input tokens (for tracking) |
| `output_cost_per_m` | number | Cost per million output tokens (for tracking) |

### Backends

| Backend | Description | Requires |
|---|---|---|
| `scripted` | Deterministic offline responses — no LLM call | Nothing |
| `heuristic` | Rule-based judge scoring — no LLM call | Nothing |
| `nim` | NVIDIA NIM inference API | Dashboard/CLI key `nvidia_nim`, or `NVIDIA_NIM_API_KEY` fallback |
| `cursor_sdk` | Cursor SDK bridge (Node.js) | Dashboard/CLI key `cursor`, or `CURSOR_API_KEY` fallback, plus Node.js 22+ |

!!! tip "Mix and match"
    You can use different backends per role. A common setup: `nim-llama-4-maverick` for fast conversation, `cursor-claude-4.6-opus-high-thinking` for high-quality judging.

---

## Prompts

**File:** `config/prompts.yaml`

Prompt templates define the system instructions and turn formatting for each of the three roles, plus a preamble for the Cursor SDK bridge.

### Structure

```yaml
collector:
  system: |
    Você é um agente de cobrança profissional ...
    Adote a estratégia abaixo:
    - tom: {strategy.tone}
    - abordagem de abertura: {strategy.opening_approach}
    ...
    Dados da conta visíveis a você:
    - valor da dívida: R$ {account.debt_amount:,.2f}
    ...
  history_empty: Inicie a conversa como agente de cobrança.
  history: |
    Conversa até aqui:
    {transcript}
    Responda apenas como agente de cobrança.

debtor:
  system: |
    Você é o Devedor ...
    Tags do perfil:
    - archetype: {profile.archetype}
    - emotional_state: {profile.emotional_state}
    ...
    Backstory:
    {profile.backstory}
    Restrições rígidas:
    {constraints}
    ...
  constraints_empty: "- Nenhuma"
  history_message: "{role}: {content}"

judge:
  system: >
    Você é o Juiz avaliador desta simulação ...
    Retorne apenas um objeto JSON compacto ...
  transcript: |
    Dados da conta: debt_amount=R$ {account.debt_amount:,.2f} ...
    Restrições do perfil:
    {constraints}
    Transcrito:
    {transcript}

cursor_sdk:
  preamble: |
    Você é o assistente em uma simulação estruturada ...
```

### Template Variables

Variables use Python `str.format()` syntax and are injected at runtime:

| Variable | Available In | Description |
|---|---|---|
| `{strategy.tone}` | collector | Current strategy's tone |
| `{strategy.opening_approach}` | collector | Current strategy's opening style |
| `{strategy.negotiation_tactic}` | collector | Current strategy's tactic |
| `{strategy.escalation_style}` | collector | Escalation behavior |
| `{strategy.concession_willingness}` | collector | Concession level |
| `{strategy.follow_up_strategy}` | collector | Follow-up action |
| `{account.debt_amount:,.2f}` | collector, judge | Formatted debt amount |
| `{account.debt_type}` | collector, judge | Product type |
| `{account.debt_age_days}` | collector, judge | Days delinquent |
| `{account.prior_contact_count}` | collector, judge | Previous contact count |
| `{profile.archetype}` | debtor | Debtor archetype |
| `{profile.financial_situation}` | debtor | Financial capacity |
| `{profile.emotional_state}` | debtor | Emotional state |
| `{profile.primary_objection}` | debtor | Main objection |
| `{profile.responsiveness}` | debtor | Engagement level |
| `{profile.demographics}` | debtor | Demographic tag |
| `{profile.backstory}` | debtor | Narrative backstory |
| `{constraints}` | debtor, judge | Formatted constraint list |
| `{transcript}` | collector, judge | Full conversation history |
| `{role}` | debtor (`history_message`) | Speaker role label |
| `{content}` | debtor (`history_message`) | Message text |

### Prompt Sections

| Section | Role | Purpose |
|---|---|---|
| `collector.system` | Collector | System prompt with strategy params and compliance guardrails |
| `collector.history_empty` | Collector | User prompt when no conversation history exists (first turn) |
| `collector.history` | Collector | User prompt with transcript for subsequent turns |
| `debtor.system` | Debtor | System prompt with profile, backstory, and constraints |
| `debtor.constraints_empty` | Debtor | Fallback when the profile has no constraints |
| `debtor.history_message` | Debtor | Format string for each turn in the transcript |
| `judge.system` | Judge | System prompt with evaluation criteria and output schema |
| `judge.transcript` | Judge | User prompt with account data, constraints, and full transcript |
| `cursor_sdk.preamble` | All (Cursor SDK) | Prepended to prompts routed through the Cursor SDK bridge |

---

## Simulation Settings

**File:** `config/simulation.yaml`

Controls conversation mechanics, compliance thresholds, arena parameters, and the objection taxonomy.

### Structure

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
  - already_paid
  - needs_time
  - wants_written_proof
  - avoidance
  - requests_callback
  - liquidation_confusion
  - scam_concern
  - overindebtedness
  - bank_mistrust
  - privacy_concern
  - official_channel_request
  - blocked_balance_hardship
  - irregular_cashflow
  - low_digital_access
```

### Conversation Settings

| Field | Type | Default | Description |
|---|---|---|---|
| `max_turns` | integer | `12` | Maximum turns before the engine forces conversation end |
| `end_signal` | string | `[END_CONVERSATION]` | Token that either agent can emit to end the conversation naturally |
| `stalemate.window` | integer | `3` | Number of recent turns to check for repetitive dialogue |
| `stalemate.similarity_threshold` | float | `0.86` | Cosine similarity threshold — if exceeded within the window, the engine declares a stalemate |

### Matrix Settings

| Field | Type | Default | Description |
|---|---|---|---|
| `default_repetitions` | integer | `1` | How many times each profile × strategy cell runs in a matrix `run` |

### Compliance Thresholds

| Field | Type | Default | Description |
|---|---|---|---|
| `min_compliance_score` | float | `0.8` | Strategies scoring below this are flagged/excluded in playbook analysis |
| `max_escalation_risk` | float | `0.3` | Strategies with escalation risk above this are flagged/excluded |

### Arena (Elo Tournament) Settings

| Field | Type | Default | Description |
|---|---|---|---|
| `default_format` | string | `swiss` | Tournament format: `swiss` or `round_robin` |
| `default_rounds` | integer | `4` | Number of tournament rounds |
| `k_factor_initial` | integer | `32` | Elo K-factor for new entrants (higher = faster rating movement) |
| `k_factor_stable` | integer | `16` | Elo K-factor after reaching the threshold |
| `k_factor_threshold` | integer | `30` | Games played before switching from initial to stable K-factor |
| `scoring` | string | `payment_x_compliance` | Scoring function: multiplies payment probability by compliance score |

### Objection Taxonomy

The `objection_taxonomy` list defines the canonical set of debtor objections recognized by the system. Each profile's `primary_objection` should be one of these values. The taxonomy is used in analysis and playbook generation to group results by objection type.

---

## Loading Configuration in Code

```python
from collection_swarm.config import load_app_config

config = load_app_config("config")  # or pass a custom directory

# Access components
profile = config.profile("cooperative_hardship")
strategy = config.strategy("empathetic_payment_plan")
model = config.model("nim-llama-4-maverick")

# Defaults
default_conv = config.default_conversation_model   # first scripted model
default_judge = config.default_judge_model          # first heuristic model

# Simulation settings
max_turns = config.simulation.conversation.max_turns
arena = config.simulation.arena
```

The `AppConfig` object validates all YAML at load time using Pydantic. If a file is missing or malformed, you get a clear error immediately rather than a cryptic failure mid-simulation.
