# Collector Strategies

Collector strategies define the behavioral blueprint the **Collector Agent** follows during simulations. Each strategy specifies tone, negotiation tactics, escalation style, and follow-up approach — along with optional Will Bank-specific fields that calibrate the strategy to the Brazilian post-liquidation collection context.

All strategies are defined in `config/collector_strategies.yaml` and are fully extensible.

## Strategy Catalog

| ID | Tone | Opening Approach | Negotiation Tactic | Escalation Style | Concession Willingness | Follow-up |
|----|------|------------------|-------------------|-----------------|----------------------|-----------|
| `empathetic_payment_plan` | Empathetic | Soft intro | Payment plan | None | Flexible | Written agreement |
| `assertive_settlement` | Assertive | Direct ask | Settlement offer | Gradual | Moderate | Immediate payment |
| `neutral_reminder` | Neutral | Reminder | Payment reminder | None | Low | Digital self-service link |
| `problem_solving_callback` | Empathetic | Problem solving | Empathy then planning prompt | None | Flexible | Callback with implementation intention |
| `liquidation_explainer` | Calm informative | Identification & disclosure | Defer until validated | None | Moderate | Callback after validation |
| `whatsapp_self_service` | Friendly brief | WhatsApp template | Link to self-negotiation portal | None | Flexible | Portal self-service |
| `superendividamento_referral` | Empathetic | Soft intro | Refer to global renegotiation | None | Flexible | Hold pattern with referral |
| `consignado_confirmation` | Calm informative | Reassurance | Confirm and inform | None | Low | Written confirmation |
| `blocked_balance_hardship_plan` | Empathetic practical | Acknowledge blocked funds & basic needs | Micro-installment with fee review | None | Highly flexible | Low-entry plan after boleto confirmation |
| `micro_merchant_cashflow_alignment` | Collaborative businesslike | Cash flow mapping | Weekly/payday-aligned installments | Gradual | Flexible | Written schedule with review date |
| `overindebtedness_stabilization` | Nonjudgmental structured | Reduce cognitive load | One recommended option with interest freeze request | None | Highly flexible | Single next step + documented hardship review |
| `reimbursement_milestone_callback` | Calm respectful | Acknowledge FGC/liquidator timing | Bridge agreement until reimbursement | None | Moderate | Callback tied to official milestone |
| `low_digital_access_guidance` | Patient step-by-step | Plain-language boleto guidance | Assisted official-channel resolution | None | Flexible | Written step-by-step instructions |

## Strategy Details

### `empathetic_payment_plan`

For cooperative hardship profiles where the debtor already wants to regularize. Leads with rapport before making an offer; anchors on a payment aligned to the 5th business day.

**Rationale:** Behavioral economics evidence supports empathy-first approaches for debtors experiencing genuine hardship. Building rapport before discussing numbers increases adherence.

---

### `assertive_settlement`

For debtors who can pay a lump sum (serial renegotiators, young profiles after validation, scam-suspicious after legitimacy is confirmed). Presents a single large discount with a short deadline using loss-aversion framing ("you lose the discount if you don't close today").

**Rationale:** Avoids the anti-pattern of offering a menu of minimums, which behavioral economics research identifies as counterproductive for settlement-capable debtors.

---

### `neutral_reminder`

First-layer collection for any profile. Short, personalized message with first name, amount, date, a single CTA (link to liquidator portal / boleto), and a scam warning (FGC alert). Extremely low cost.

**Rationale:** Strong evidence base for simple personalized reminders as a cost-effective first touch before escalating to more intensive strategies.

---

### `problem_solving_callback`

For debtors who clearly want to pay but cannot right now, or need to consult a spouse / check their statement. Instead of forcing closure, exits with a concrete appointment: "I'll call you Tuesday at 7pm to close via WhatsApp — can you confirm?"

**Rationale:** Implementation intentions ("when-where-how" commitments) dramatically increase follow-through rates compared to vague promises.

---

### `liquidation_explainer`

Opens by presenting the collection company, citing the extrajudicial liquidation (BCB 2026-01-21), the liquidator (EFB Regimes Especiais de Empresas Ltda.), and offering the official channel willbank.com.br / bcb.gov.br for validation. Only advances to collection after the debtor signals they've validated or accept proceeding.

**Rationale:** Equivalent to the "scam-safety brief" recommended by FGC and Procon-SP in 2026. Builds trust with skeptical or confused debtors before any payment discussion.

---

### `whatsapp_self_service`

Short message with the client's name, amount, three pre-approved options (lump sum with discount, short installment plan, schedule for the 5th), and a link to the liquidator's portal. Maintains the "original Will" tone without violating CDC art. 42.

**Rationale:** Designed for digital-native debtors (young profiles) who prefer self-service over phone conversations.

---

### `superendividamento_referral`

Recognizes the debtor as a candidate for Law 14.181/2021. Instead of pressuring for an individual agreement that will predictably fail, offers the path via Procon / Defensoria / conciliation hearing and marks a symbolic collection amount that respects the existential minimum.

**Rationale:** Reduces litigation risk, improves rapport, and protects the liquidator's reputation by acknowledging the debtor's multi-creditor situation.

---

### `consignado_confirmation`

Confirms that FGTS anniversary withdrawal / consignado deductions continue normally, identifies the liquidator and official channels, and answers any questions. No Pix, data, or signature request.

**Rationale:** The correct behavior for this profile is *not* collecting — the simulator must learn that reassurance-only is the optimal play for payroll-steady debtors.

---

### `blocked_balance_hardship_plan`

For debtors with salary or savings blocked by the liquidation. Starts by acknowledging the asymmetry created by the liquidation, validates the official channel, and proposes a very low entry payment with fee review — without pressuring essential expenses.

**Rationale:** The liquidation created a genuine cash flow crisis for these debtors. Acknowledging it before asking for money is both ethical and more effective.

---

### `micro_merchant_cashflow_alignment`

For micro-entrepreneurs with irregular income. Replaces fixed due dates with smaller payments tied to sales cycles or client payment days, reducing promise breakage without forcing working capital.

**Rationale:** Fixed monthly due dates consistently fail for irregular-income debtors. Aligning payment timing to actual cash flow improves adherence.

---

### `overindebtedness_stabilization`

Complements the legal referral with an operational approach for avoidant profiles: few choices, one default recommendation, possible interest freeze, and a documented next step.

**Rationale:** Overwhelmed debtors suffer from decision overload. Presenting a single recommended option dramatically reduces dropout.

---

### `reimbursement_milestone_callback`

For clients with significant blocked funds. Avoids turning legitimate frustration into conflict: acknowledges the reimbursement milestone, agrees on a small bridge payment or just a callback, and does not invent liquidator deadlines.

**Rationale:** Respecting the debtor's timeline and linking follow-up to official milestones builds trust without creating false expectations.

---

### `low_digital_access_guidance`

For low digital literacy debtors. Speaks slowly, avoids jargon, does not request sensitive data, and sends verifiable instructions for generating an official boleto.

**Rationale:** The gain is in reducing operational error — guiding the debtor step-by-step through the official payment channel rather than expecting self-service.

---

## Core Fields

Every strategy requires the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique identifier used in CLI and API |
| `tone` | `str` | Overall conversational tone |
| `opening_approach` | `str` | How the collector opens the conversation |
| `negotiation_tactic` | `str` | Primary negotiation approach |
| `escalation_style` | `str` | How pressure is applied (`none`, `gradual`) |
| `concession_willingness` | `str` | Flexibility level (`low`, `moderate`, `flexible`, `highly_flexible`) |
| `compliance_adherence` | `str` | Regulatory compliance stance (always `strict`) |
| `follow_up_strategy` | `str` | How the conversation concludes or continues |

## Will Bank-Specific Fields

The following optional fields calibrate strategies to the Will Bank post-liquidation context:

| Field | Type | Description |
|-------|------|-------------|
| `payment_channel` | `str` | Payment method (e.g. `boleto_registrado`, `link_boleto_registrado`) |
| `primary_anchor` | `str` | The main anchoring point for negotiation (e.g. `parcela_alinhada_ao_dia_5`) |
| `discovery_questions` | `str` | Type of discovery approach (`motivational_interviewing`, `minimal`, `none`, `hardship_triage`, `cashflow_mapping`) |
| `framing` | `str` | Behavioral framing technique (e.g. `gain_preservation_score_cpf`, `loss_aversion_perda_de_desconto`) |
| `discount_authority` | `str` | Level of discount the collector can offer (`none`, `low`, `medium`) |
| `liquidation_disclosure` | `str` | When to disclose liquidation context (`proactive`, `leading`) |
| `cultural_register` | `str` | Language and cultural register (e.g. `brasileiro_acessivel_neutro`, `brasileiro_jovem_will_voice`) |
| `rationale` | `str` | Internal documentation explaining why this strategy exists and when to use it |

### Payment channels

| Value | Description |
|-------|-------------|
| `boleto_registrado` | Official registered boleto (most strategies) |
| `link_boleto_registrado` | Digital link to boleto generation |
| `nao_aplicavel_descontos_automaticos` | Not applicable — automatic deductions (consignado) |

### Framing techniques

| Value | Behavioral Basis |
|-------|-----------------|
| `gain_preservation_score_cpf` | Gain framing — preserve credit score |
| `loss_aversion_perda_de_desconto` | Loss aversion — "you lose the discount" |
| `factual_personalized` | Neutral facts with personalization |
| `gain_progress_recovery` | Gain framing — recovery progress |
| `factual_protective` | Protective factual framing |
| `gain_resolve_now` | Urgency + gain framing |
| `gain_organize_all_debts` | Gain framing — organize all debts |
| `protective_minimo_existencial` | Protective — existential minimum |
| `business_continuity` | Business continuity framing |
| `reduce_decision_overload` | Reduce decision overload |
| `fairness_and_timing` | Fairness and timing framing |
| `confidence_and_control` | Build confidence and sense of control |

### Cultural registers

| Value | Description |
|-------|-------------|
| `brasileiro_acessivel_neutro` | Accessible Brazilian Portuguese, neutral tone |
| `brasileiro_acessivel_assertivo` | Accessible, assertive |
| `brasileiro_acessivel_breve` | Accessible, brief |
| `brasileiro_acessivel_acolhedor` | Accessible, welcoming |
| `brasileiro_acessivel_didatico` | Accessible, didactic |
| `brasileiro_jovem_will_voice` | Young, Will Bank voice |
| `brasileiro_pratico_microempreendedor` | Practical, micro-entrepreneur register |
| `brasileiro_acessivel_sem_julgamento` | Accessible, nonjudgmental |
| `brasileiro_respeitoso_formal` | Respectful, formal |
| `brasileiro_simples_paciente` | Simple, patient |

## Adding New Strategies

1. Open `config/collector_strategies.yaml`.
2. Add a new entry under the `strategies` list:

```yaml
- id: my_custom_strategy
  tone: empathetic
  opening_approach: soft_intro
  negotiation_tactic: payment_plan
  escalation_style: none
  concession_willingness: flexible
  compliance_adherence: strict
  follow_up_strategy: written_agreement
  # Optional Will Bank fields
  payment_channel: boleto_registrado
  primary_anchor: parcela_alinhada_ao_dia_5
  discovery_questions: motivational_interviewing
  framing: gain_preservation_score_cpf
  discount_authority: low
  liquidation_disclosure: proactive
  cultural_register: brasileiro_acessivel_neutro
  rationale: |
    Explain why this strategy exists and when it should be used.
```

3. The strategy is immediately available in the CLI and dashboard.

!!! tip "Testing new strategies"
    Run a matrix sweep with your new strategy against several profiles to see how it performs:

    ```bash
    collection-swarm run \
      --strategies my_custom_strategy \
      --profiles cooperative_hardship,hostile_avoidant,written_proof_disputer \
      --reps 3
    ```

    Then generate a playbook to see the ranking:

    ```bash
    collection-swarm analyze --output output/playbook.md
    ```
