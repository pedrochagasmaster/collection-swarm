# Debtor Profiles

Debtor profiles define the synthetic personas that the **Debtor Agent** embodies during simulations. Each profile captures an archetype, financial situation, emotional state, backstory, and — critically — a set of **machine-readable constraints** that the Judge verifies deterministically.

All profiles are defined in `config/debtor_profiles.yaml` and are fully extensible.

## Profile Catalog

The bundled catalog is calibrated to **Will Bank's** real client base and the post-liquidation Brazilian context (BCB extrajudicial liquidation decreed 2026-01-21).

| ID | Archetype | Financial Situation | Debt (R$) | Debt Type | Primary Objection | Emotional State | Demographics |
|----|-----------|--------------------:|----------:|-----------|-------------------|-----------------|--------------|
| `cooperative_hardship` | Cooperative | Hardship | 850 | Crédito pessoal Will | Inability to pay | Anxious | Nordeste, classe C, mãe provedora |
| `written_proof_disputer` | Disputer | Can pay partial | 612 | Cartão crédito Will | Wants written proof | Guarded | Sudeste, classe C, jovem profissional |
| `hostile_avoidant` | Hostile | Can pay partial | 1,900 | Cartão crédito Will | Avoidance | Angry | Nordeste, classe D, chefe de família |
| `liquidation_confused` | Confused | Can pay partial | 540 | Cartão crédito Will | Questions validity post-liquidation | Confused | Nordeste, classe C, idoso |
| `scam_suspicious` | Skeptical | Can pay full | 1,280 | Cartão crédito Will | Suspects scam | Distrustful | Sudeste, classe B, jovem profissional |
| `feirao_serial_renegotiator` | Strategic | Can pay partial | 2,750 | Cartão crédito Will | Demands 70%+ discount | Detached | Nordeste, classe C, provedor |
| `consignado_payroll_steady` | Cooperative | Stable | 4,200 | FGTS antecipação Will | Needs reassurance post-liquidation | Calm | Nordeste, classe C, trabalhador formal |
| `superendividado_chronic` | Overwhelmed | Insolvent | 980 | Cartão crédito Will | Over-indebted, multi-creditor | Ashamed | Sudeste, classe D, provedor |
| `young_first_credit_card` | Cooperative | Can pay full | 320 | Cartão crédito Will | Forgetful / disorganized | Ashamed | Nordeste, classe C, jovem (22), primeiro cartão |
| `willbank_blocked_balance_hardship` | Anxious hardship | Temporary liquidity block | 930 | Cartão crédito Will | Money blocked by liquidation | Anxious and confused | Nordeste, classe D, saldo bloqueado |
| `willbank_micro_merchant_cashflow` | Pragmatic micro-merchant | Irregular income | 1,480 | Cartão Will (uso no negócio) | Irregular cash flow after Pix/card disruption | Stressed but practical | Microempreendedor informal, cidade pequena |
| `willbank_benefit_dependent_household` | Vulnerable hardship | Essential expenses at risk | 760 | Cartão Will + contas básicas | Basic needs take priority | Fearful | Família dependente de benefício |
| `willbank_fgc_waiting_high_balance` | Angry reimbursement-waiting | Asset-rich, cash-poor | 3,900 | Parcelas cartão Will | Will pay after FGC/liquidator release | Angry | Cliente com saldo/investimento bloqueado |
| `willbank_low_digital_access` | Low digital access | Can pay partial with assistance | 520 | Fatura cartão Will | Cannot access app or generate boleto | Uncertain | Baixa literacia digital, cidade pequena |

## Profile Details

### `cooperative_hardship`

**Backstory:** Mãe provedora de Fortaleza-CE, classes C/D. Opened a Will Bank account attracted by "diz sim aos invisíveis". Took a R$ 1,500 personal loan for a roof repair and fell behind after her husband's hours were reduced. Receives salary via Will Bank and lost access when the BC initiated liquidation. Feels ashamed but wants to regularize her CPF.

**Constraints:**

- Max payment: R$ 80/month
- Will not share card data or passwords by phone
- Only accepts boleto registrado in the name of Will Financeira / liquidante

---

### `written_proof_disputer`

**Backstory:** Young professional in São Paulo, second credit card ever. Believes the invoice includes an annual fee Will had promised to waive and an unrecognized withdrawal fee. Filed a complaint on Reclame Aqui without resolution. Knows CDC art. 42 and will demand itemized invoice and signed contract before any payment discussion.

**Constraints:**

- Always demands itemized invoice and written contract before discussing payment (rule: `required_action` → `demand_written_proof`)
- Will not pay the disputed R$ 79 fee without documentary proof

---

### `hostile_avoidant`

**Backstory:** Head of household in Recife, has received collection calls for weeks and just read on social media about scams impersonating Will Bank post-liquidation. Irritated, suspicious, and brief. Will hang up if the approach is not objective and respectful.

**Constraints:**

- Will not provide card, account, or password data during the call
- Will end the call if there's hostility, threats, or excessive pressure
- Will not accept Pix payments — knows Will Bank Pix was deactivated

---

### `liquidation_confused`

**Backstory:** Retiree from Salvador who saw on Jornal Nacional that Will Bank "broke" and thinks his debt was cancelled. The Will app doesn't work properly and he can't generate a boleto. Good faith, wants to do the right thing, but needs patient explanation with official sources (BCB, willbank.com.br).

**Constraints:**

- Will only pay after the collector cites the liquidator (EFB Regimes Especiais de Empresas) and indicates the official channel (willbank.com.br or BCB) (rule: `required_action` → `cite_liquidator_and_official_channel`)
- Will not provide personal data without confirmation via official channel

---

### `scam_suspicious`

**Backstory:** Will customer since 2021, read the FGC and Procon-SP alert about post-liquidation scams. Has the means to pay but won't move a cent until confirming the collection is legitimate. Will ask for protocol, BCB liquidation process number, collector company ID, and will likely hang up to validate independently.

**Constraints:**

- Will not provide any personal data until validating legitimacy via official channel
- Refuses any payment via Pix or card during the call
- Will end the call if the collector refuses to provide protocol, CNPJ, or liquidator reference

---

### `feirao_serial_renegotiator`

**Backstory:** Has already renegotiated three debts via Feirão Serasa Limpa Nome and is waiting for the next Feirão to resolve this one too. Will demand aggressive discount (≥80%), lump-sum payment, and immediate removal from the defaulter registry. No emotional urgency — treats it as cold negotiation.

**Constraints:**

- Will only accept an effective discount of at least 70% on the current balance
- Demands immediate proof of name clearance after payment

---

### `consignado_payroll_steady`

**Backstory:** Advanced seven FGTS anniversary withdrawals at Will Bank. Deductions continue normally through the linked FGTS account, but saw on social media that Will Bank was liquidated and is worried. Doesn't want trouble — just wants to know if everything is in order and who the creditor is now.

**Constraints:**

- Will not authorize new debit or Pix during the call — trusts only the automatic FGTS flow

---

### `superendividado_chronic`

**Backstory:** Has nine active debts (cards, finance companies, electricity), income commitment above 80%, and cannot prioritize a single creditor. Law 14.181/2021 (superendividamento) applies. Too ashamed to ask for help but is a natural candidate for the over-indebtedness conciliation hearing.

**Constraints:**

- Will not take on new commitments before organizing all debts in a superendividamento hearing
- Max payment: R$ 35/month to this creditor while other debts remain open

---

### `young_first_credit_card`

**Backstory:** 22 years old, first credit card (Will), initially approved through the "AprovadoDoRolê" campaign. Forgot the due date, lacked Pix balance, couldn't collect from a friend who split a purchase. Has the money, is embarrassed to talk on the phone, but would resolve in seconds via WhatsApp / payment link.

**Constraints:**

- Prefers digital resolution; will hang up if the call lasts more than 5 minutes without practical resolution

---

### `willbank_blocked_balance_hardship`

**Backstory:** Used Will Bank as primary digital account and had salary or emergency reserve unavailable after the BC liquidation. Understands the card invoice may remain valid but considers it unfair to pay interest while essential money is frozen. Wants official boleto, fee review, and a plan that protects food, rent, electricity, and medication first.

**Constraints:**

- Max payment: R$ 80/month until blocked funds are released
- Will only proceed after receiving an official boleto path or written instruction from the liquidator (rule: `required_action` → `cite_liquidator_and_official_channel`)
- Will screenshot app/boleto failures before accepting interest and penalties

---

### `willbank_micro_merchant_cashflow`

**Backstory:** Used card, Pix, and marketplace purchases linked to Will for informal sales. The liquidation disrupted client receipts and supplier payments. Can pay when weekly sales come in but rejects rigid due dates that compete with inventory purchases.

**Constraints:**

- Max payment: R$ 120/month or R$ 35/week
- Will only proceed if allowed to choose payment dates aligned with weekly cash flow

---

### `willbank_benefit_dependent_household`

**Backstory:** Depends on social benefits, gig work, or family help. The frozen Will Bank balance was reserved for groceries, rent, medication, and electricity. Wants to avoid negative credit listing but cannot trade essential expenses for a high card payment.

**Constraints:**

- Max payment: R$ 45/month before covering essential expenses
- Will disengage if the collector suggests sacrificing food, medication, or rent

---

### `willbank_fgc_waiting_high_balance`

**Backstory:** Has over R$ 1,000 blocked or invested and was not covered by the initial FGC advance through the app. Believes the institution created the problem and demands that any collection acknowledge the liquidation timeline. Can make a meaningful payment after reimbursement but before that only considers a bridge agreement or scheduled callback.

**Constraints:**

- Max payment: R$ 150/month before FGC or liquidator reimbursement
- Demands a callback tied to an official reimbursement milestone before a larger agreement

---

### `willbank_low_digital_access`

**Backstory:** Has limited data plan, an old phone, or difficulty using the Will app after liquidation. Wants to pay enough to avoid negative consequences but cannot generate a boleto alone. Responds to plain Portuguese, step-by-step guidance, and official written instructions.

**Constraints:**

- Max payment: R$ 55/month
- Demands official step-by-step instructions before accepting responsibility for delays

---

## Constraint System

Each profile can define one or more **constraints** — rules the debtor will not break during the conversation. Constraints serve two purposes:

1. **Behavioral guardrails** — The Debtor Agent uses constraint text to stay in character.
2. **Deterministic verification** — The Judge checks machine-readable `rule` fields against the transcript.

### Constraint structure

```yaml
constraints:
  - text: "Nunca aceitará parcela acima de R$ 80 por mês."
    rule:
      type: max_payment
      amount: 80
      frequency: monthly
  - text: "Não passará dados de cartão ou senha por telefone."
  - text: "Só aceitará pagar por boleto registrado."
```

### Rule types

| `type` | Fields | Description |
|--------|--------|-------------|
| `max_payment` | `amount`, `frequency` | Debtor will not agree above this payment ceiling |
| `required_action` | `action` | A specific action must occur before the debtor engages |

### Available actions

| `action` | Description |
|----------|-------------|
| `demand_written_proof` | Debtor demands itemized invoice and contract |
| `cite_liquidator_and_official_channel` | Collector must reference the liquidator or official channel |

!!! info "Soft vs. hard constraints"
    Constraints with a `rule` block are verified deterministically by the Judge. Constraints with only `text` (no `rule`) guide the Debtor Agent's behavior but are evaluated heuristically by the LLM Judge.

## Adding New Profiles

1. Open `config/debtor_profiles.yaml`.
2. Add a new entry under the `profiles` list:

```yaml
- id: my_custom_profile
  archetype: cooperative
  financial_situation: can_pay_partial
  debt_amount: 1000
  debt_age_days: 90
  debt_type: cartao_credito_will
  prior_contact_count: 2
  emotional_state: anxious
  primary_objection: inability_to_pay
  responsiveness: medium
  demographics: sudeste_classe_c
  backstory: |
    A detailed backstory that gives the Debtor Agent
    context for role-playing this persona.
  constraints:
    - text: "Will not agree to more than R$ 50/month."
      rule:
        type: max_payment
        amount: 50
        frequency: monthly
```

3. The profile is immediately available in the CLI and dashboard — no code changes required.

!!! tip "Calibration"
    Run a few simulations with the new profile and review the transcripts to verify the Debtor Agent stays in character. Adjust the backstory and constraints as needed.
