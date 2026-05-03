# Configuration files

Five YAML files under `config/`. All of them are loaded by
[`config.load_app_config()`](../modules/config.md). Anything you change
here takes effect on the next process start.

## `debtor_profiles.yaml`

A list of `Profile` objects. Each Profile has analytical Tags
(`archetype`, `financial_situation`, `primary_objection`, etc.), a
`backstory` (rendered into the Debtor's system prompt), and a list of
Constraints. Constraints carry a natural-language `text` and an optional
structured `rule`.

Example excerpt from the shipped catalog:

```yaml
- id: cooperative_hardship
  archetype: cooperative
  financial_situation: hardship
  debt_amount: 850
  debt_age_days: 75
  debt_type: credito_pessoal_will
  prior_contact_count: 1
  emotional_state: anxious
  primary_objection: inability_to_pay
  responsiveness: high
  demographics: nordeste_classe_c_mae_provedora
  backstory: 'Mãe provedora de Fortaleza-CE, ...'
  constraints:
    - text: Nunca aceitará parcela acima de R$ 80 por mês.
      rule:
        type: max_payment
        amount: 80
        frequency: monthly
    - text: Não passará dados de cartão ou senha por telefone.
    - text: Só aceitará pagar por boleto registrado em nome da Will Financeira / liquidante.
```

The `rule.type` values understood by the deterministic verifier are
documented at [`models.py > ConstraintRule`](../modules/models.md#constraintrule).

## `collector_strategies.yaml`

A list of `Strategy` objects. The first eight fields (`tone`,
`opening_approach`, `negotiation_tactic`, `escalation_style`,
`concession_willingness`, `compliance_adherence`, `follow_up_strategy`)
are required. The optional fields (`payment_channel`, `primary_anchor`,
`discovery_questions`, `framing`, `discount_authority`,
`liquidation_disclosure`, `cultural_register`, `rationale`) are
descriptive refinements added for the Will Bank context.

The `Strategy` model uses `extra="ignore"`, so you can add new YAML
keys for documentation purposes without breaking validation.

## `models.yaml`

Two layouts are accepted; the shipped file uses the `tiers:` layout:

```yaml
tiers:
  conversation:
    models:
      - id: local-scripted
        backend: scripted
        provider: local
      - id: cursor-gpt-5.5-medium
        backend: cursor_sdk
        provider: openai
        model_name: gpt-5.5
      - id: nim-mistral-large-3-675b
        backend: nim
        provider: mistral
        model_name: openai/mistralai/mistral-large-3-675b-instruct-2512
  judge:
    models:
      - id: local-judge
        backend: heuristic
        provider: local
      - id: cursor-claude-opus-4-7-thinking-high
        backend: cursor_sdk
        provider: anthropic
        model_name: claude-opus-4-7
```

| Field                  | Required | Notes                                                          |
| ---------------------- | -------- | --------------------------------------------------------------- |
| `id`                   | yes      | The user-facing ID passed to the CLI / API.                    |
| `backend`              | yes      | One of `scripted`, `heuristic`, `cursor_sdk`, `nim`.            |
| `provider`             | no       | Free-form string, surfaced by the dashboard.                    |
| `model_name`           | no       | Provider-facing model string (LiteLLM model or Cursor SDK ID). |
| `input_cost_per_m`     | no       | USD per million input tokens.                                   |
| `output_cost_per_m`    | no       | USD per million output tokens.                                  |

`config.default_conversation_model` picks the first `scripted` row;
`config.default_judge_model` picks the first `heuristic` row, falling
back to `scripted`.

## `prompts.yaml`

```yaml
collector:
  system: |
    Você é um agente de cobrança...
  history_empty: Inicie a conversa como agente de cobrança.
  history: |
    Conversa até aqui:
    {transcript}
debtor:
  system: |
    Você é o Devedor...
  constraints_empty: "- Nenhuma"
  history_message: "{role}: {content}"
judge:
  system: >
    Você é o Juiz avaliador...
  transcript: |
    Dados da conta: ...
    Restrições do perfil:
    {constraints}
    Transcrito:
    {transcript}
cursor_sdk:
  preamble: |
    Você é o assistente em uma simulação...
```

The placeholders that get `.format()`-ed:

| Section                | Placeholders                               |
| ---------------------- | ------------------------------------------- |
| `collector.system`     | `strategy`, `account`                      |
| `collector.history`    | `transcript`                                |
| `debtor.system`        | `profile`, `constraints`                   |
| `debtor.history_message` | `role`, `content`                         |
| `judge.transcript`     | `account`, `constraints`, `transcript`     |

## `simulation.yaml`

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

| Section            | Field                                         | Default                  |
| ------------------ | --------------------------------------------- | ------------------------ |
| `conversation`     | `max_turns`                                   | `12` (was `20` in code)  |
| `conversation`     | `end_signal`                                  | `[END_CONVERSATION]`     |
| `conversation.stalemate` | `window`                                | `3`                      |
| `conversation.stalemate` | `similarity_threshold`                  | `0.86`                   |
| `matrix`           | `default_repetitions`                         | `1`                      |
| `compliance`       | `min_compliance_score`                        | `0.8`                    |
| `compliance`       | `max_escalation_risk`                         | `0.3`                    |
| `arena`            | `default_format`                              | `swiss`                  |
| `arena`            | `default_rounds`                              | `4`                      |
| `arena`            | `k_factor_initial`                            | `32`                     |
| `arena`            | `k_factor_stable`                             | `16`                     |
| `arena`            | `k_factor_threshold`                          | `30`                     |
| `arena`            | `scoring`                                     | `payment_x_compliance`   |
| `objection_taxonomy` | list                                         | (16 entries)             |

The flat older layout (`stalemate_window`, `stalemate_similarity_threshold`
under `conversation`) is still accepted by `load_simulation_settings`.
