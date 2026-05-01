# Willbank Collection Strategy — Research Dossier

A consolidated, sourced briefing that grounds the redesigned debtor profiles
(`config/debtor_profiles.yaml`) and collector strategies
(`config/collector_strategies.yaml`) in the real-world context of Will Bank's
forced liquidation, the Brazilian regulatory and macroeconomic environment, the
profile of Will Bank's actual client base, and the peer-reviewed literature on
debt-collection effectiveness. Every claim below is annotated with the public
source it came from. This document is the primary input for any future revision
of the simulation's profiles and strategies.

---

## 1. Will Bank — company, client base, and brand voice

### 1.1 Origin and trajectory

- Founded in 2017 in Espírito Santo as the credit-card issuer **Meu Pag!** by
  Felipe Felix and the brothers Giovanni and Walter Piana. Rebranded as
  **Will Bank** in 2020 when it expanded into a full digital bank with
  remunerated digital accounts, debit and credit cards, Pix and TED, personal
  loans, FGTS *saque-aniversário* anticipation, and a cashback marketplace
  (G1, ISTOÉ Dinheiro, Meio & Mensagem).
- 2021: R$ 250 million PE round led by XP and Atmos Capital (24.9% minority
  stake). 2022: absorbed the team and partnerships of cashback startup Getmore.
  2024: control transferred to **Banco Master** (CADE/BCB-approved restructuring
  separated Will Instituição de Pagamentos under Grupo Reag from Will Financeira
  S.A. CFI under Master) (G1, ISTOÉ Dinheiro).
- The legal entity that survives the rebrand and is in liquidation is
  **Will Financeira S.A. Crédito, Financiamento e Investimento** — a Sociedade
  de Crédito, Financiamento e Investimento (SCFI), not a *banco múltiplo*
  (BCB official notice).

### 1.2 Forced liquidation — timeline

- **2025-11-18** — BCB decreed extrajudicial liquidation of **Banco Master**.
  Will Financeira was kept under **RAET** (Regime Especial de Administração
  Temporária) so a sale to a new investor could be attempted (G1, BCB).
- A potential acquirer of Arab origin showed interest but the deal collapsed
  (G1 / Blog do Valdo Cruz).
- **2026-01-19** — Will Financeira defaulted on its Mastercard payment-arrangement
  schedule. Mastercard suspended Will-issued cards the next day (Reuters,
  Yahoo Finance, Valor International).
- **2026-01-21** — BCB decreed the **extrajudicial liquidation** of Will
  Financeira. EFB Regimes Especiais de Empresas Ltda. was appointed liquidator;
  controllers' and former administrators' assets were frozen (BCB official
  notice; Agência Brasil; G1).
- Reported scale at liquidation: ~R$ 7 bi in passivos, ~R$ 8 bi in current
  Mastercard transactions, ~R$ 6.3 bi in CDBs (FGC-eligible, per November 2025
  census). The Conglomerado Master was an S3 (small-tier) institution holding
  0.57% of SFN total assets and 0.55% of total funding (BCB note; UOL).

### 1.3 Customer base — who actually owes Willbank

- **Scale**: 9–12 million clients depending on the cut and reporting date;
  10 mi at end-2024 dropping after the Master collapse, 9 mi cited on the bank's
  own site at liquidation (UOL, ISTOÉ Dinheiro, G1).
- **Geography**: highly skewed to the **Nordeste**, where roughly **60% of users**
  resided, many in small towns (G1, ISTOÉ Dinheiro). FGV-EBAPE research
  characterizes Northeast household indebtedness as severe and concentrated in
  digital channels (FGV repository).
- **Income**: explicit positioning on **classes C and D**, *desbancarizados* and
  the "invisíveis do crédito" — Felipe Felix described Will as "o banco que diz
  sim aos invisíveis do crédito" (Brazil Journal interview cited by ISTOÉ
  Dinheiro). 40% of Will users got their first credit card via Will (ISTOÉ
  Dinheiro).
- **Demographics & behavior**: marketing targeted the young digital-native
  audience (TikTok, Instagram), with a deliberately playful, accessible tone and
  high-celebrity reach: Whindersson Nunes (Dia do Nordestino campaign), Pabllo
  Vittar, Maísa, Simone, Thelminha, Vinícius Jr., Danny Bond (Meio & Mensagem,
  G1, Reclame Aqui).
- **Brand voice**: simple, casual, humor-forward, pro-inclusion. The default
  experience was app-first ("plim! O Programa de Limite do Will" gamified limit
  increases). Customers are accustomed to being addressed informally (`tu`/`você`,
  emojis, slangs like "rolê", "manda ver"), which sets expectations for any
  collection script that wants to feel familiar instead of intimidating.

### 1.4 Product mix that drives the active receivables

- **Credit cards (Mastercard)** — the largest portfolio. Limits are dynamic and
  start small for the C/D segment (Will Bank blog "Como aumentar o limite do
  cartão"). After liquidation new compras and approximation/recurring payments
  are blocked, but installments and outstanding balances remain due.
- **Antecipação do saque-aniversário do FGTS** — up to 7 years anticipated, from
  R$ 100, juros ~1.89%/mês (MaisRetorno; Will Bank blog). Repaid via the FGTS
  account by Caixa, so default risk is structurally lower; however, post-RAET
  the FGTS counterparty must redirect repayments to the liquidator.
- **Crédito pessoal** — taxes from 4.99%/mês, limits R$ 500–50.000 depending on
  client profile (Will Bank blog "Como fazer empréstimo").
- **Conta de pagamento pré-paga** (not conta corrente) — by law Will deposited
  client balances daily at BCB; reimbursement of these balances is handled
  directly by the liquidator without FGC intervention (UOL errata; Serasa blog;
  Andrea Sano Alencar quoted in UOL).
- **CDBs** — R$ 6.3 bi outstanding at Nov-2025 census; covered by the FGC up to
  R$ 250.000 per CPF, with the conglomerated cap of R$ 1 mi over four years
  shared with Banco Master / Letsbank since 30-Aug-2024 (FGC; UOL).
- **Marketplace cashback** and **Pix** — operational only, no receivables.

### 1.5 What changes for debtors after liquidation

- **Debts are NOT extinguished.** Credit-card invoices, personal loans, and
  installments remain due and accrue ordinary interest, fines, and *negativação*
  if missed (Serasa blog "Liquidação do will bank"; Agência Brasil; BCB FAQ).
- **The counterparty changes.** All collections are now administered by the
  liquidator (EFB Regimes Especiais de Empresas Ltda.), via official channels
  posted at willbank.com.br/Banco Central. The liquidator may transfer (cede)
  the credit portfolio to another institution (UOL; BCB note on Banco Master
  FAQ; Forbes).
- **Operational frictions for debtors.**
  - The app is in liquidation mode; new boletos may not be generated.
  - Faturas em aberto already issued before liquidation are still payable.
  - **Pix to Will Bank stopped working** at liquidation — invoices must be paid
    by **boleto only** (willbank.com.br homepage; Serasa blog).
  - Pix keys at Will Bank are invalid; debtors must rebind keys at another
    institution.
  - Clientes consignados continue to have payroll deductions applied normally —
    these do NOT stop with liquidation.
- **Scam exposure is high.** FGC and BCB have publicly warned that fraudsters
  are sending fake boletos, fake "managers", fake "FGC payouts" to extract
  data and money from confused Will customers (Gazeta do Povo; Procon-SP;
  YouTube/Instagram alerts). This is a first-class concern any post-liquidation
  collection script must address.
- **Legal hooks for the debtor**: Serasa and consumer-law firms note that
  *negativação* and late fees can be contested if the debtor can prove a
  material payment impossibility caused by the BC intervention (no boleto,
  app down, account that received salary blocked). This does not extinguish
  the debt but it does affect punitive add-ons (Serasa blog).
- **No FGC for debtors.** The FGC protects depositors / investors, never
  debtors of the failed institution. Debt remains an asset of the *massa
  liquidanda* (FGC; BCB FAQ; jurisprudence on Cruzeiro do Sul).

---

## 2. Brazilian regulatory and macroeconomic context for collection

### 2.1 Regulatory floor (non-negotiable)

- **CDC art. 42** — vedação de cobrança vexatória, ridículo, ameaça, coação;
  pagamento indevido devolvido em dobro (*repetição do indébito*) (TJDFT;
  Jusbrasil).
- **CDC art. 71** — penaliza criminalmente ameaças, coação, constrangimento
  físico ou moral, declarações falsas, e qualquer procedimento que exponha o
  consumidor ao ridículo ou interfira em trabalho, descanso ou lazer (TJDFT).
- **Lei 14.181/2021 — Lei do Superendividamento** — alterou o CDC para
  prevenir/atender o superendividamento de pessoas naturais; preserva o
  *mínimo existencial*; veda assédio em oferta de crédito; possibilita
  renegociação global em audiência conciliatória; foco extra em idosos
  (anbc.org.br; CPG; JICL; Conjur).
- **Resolução CMN 4.949/2021** — exige que toda IF tenha *política institucional
  de relacionamento com clientes* contendo "sistemática de cobrança em caso de
  inadimplemento" e princípios de ética, responsabilidade, transparência e
  diligência (BCB normativo).
- **Resolução CMN 4.860/2020** — disciplina ouvidoria como canal de última
  instância; exigida para IFs que atendem PFs e MEs (BCB; Estratégia
  Concursos).
- **Normativo SARB nº 27/2023 (FEBRABAN)** — autorregulação:
  - Telefone: **seg–sex 07h–21h**, **sáb 09h–16h**, exceto agendamento explícito
    do consumidor (FEBRABAN, Anuário 2024).
  - E-mail: sem restrição de horário.
  - **Vedado** cobrar telefonicamente dívidas vencidas há mais de **5 anos**.
  - Atendimento "sempre cordial e respeitoso", com identificação clara da dívida
    e das condições.
- **LGPD** — comunicação por canal digital (WhatsApp, e-mail, SMS) exige base
  legal (execução de contrato ou legítimo interesse), finalidade declarada, e
  oferta de opt-out. PG Mais e Voll Solutions reportam que a maioria das IFs
  brasileiras já operam cobrança via WhatsApp Business API por LGPD-compliance.
- Em **liquidação extrajudicial**, a sistemática de cobrança passa para o
  liquidante — toda comunicação deve identificar a *massa liquidanda* e o
  liquidante nomeado pelo BC, sob pena de invalidade e risco de equiparação
  a golpe (BCB Bank Resolution; Forbes; jurisprudência Cruzeiro do Sul).

### 2.2 Macro context for debtors at the moment of liquidation

- **82.8 milhões** de inadimplentes registrados pela Serasa em mar/2026, ~49%
  da população adulta; 80.6 mi em nov/2025 (Serasa Mapa da Inadimplência;
  Rio Times).
- **Dívida média**: ~R$ 6.274,82 por inadimplente em fim de 2025 (com viés
  para tickets bancários); ~R$ 1.588 quando se contam dívidas extra-bureau
  (Prime Yield; Pagou Fácil/Valor).
- **Composição das dívidas** (Serasa):
  - Bancos e cartões: 27–28,5% (líder).
  - Utilities (água, luz, gás): 20–21%.
  - Financeiras: 19–20%.
- **Faixa etária mais negativada**: 41–60 anos, **35,5%** do total.
- **Nordeste**: a região líder em recuperação de dívidas, com 67,7% de
  regularização em fim de 2022 (Serasa). Classes C/D priorizam dívidas
  "essenciais" (banco/cartão e contas de luz/água/gás) acima das demais.
- **Comprometimento de renda** (PEIC/CNC, ago/2025): 78% das famílias
  brasileiras estão endividadas; ~30% inadimplentes; cerca de 12% não terão
  capacidade de quitar.
- **Default contagion** (BCB working paper #476): inadimplência em uma
  modalidade espalha para outras, aumentando risco de espiral.

---

## 3. Psychology of Brazilian indebted consumers

- **Querem pagar, mas estão travados.** 77% dos inadimplentes brasileiros
  declaram que querem regularizar, mas são bloqueados por **ansiedade**
  (98% dos devedores em estudo da Carta Capital/Veja) e burocracia inflexível
  (Carta Capital; Veja).
- **Vergonha e culpa** são dominantes — Portal do Investidor / CVM lista
  vergonha, culpa, sensação de fracasso e ansiedade como efeitos
  psicológicos centrais; bloqueiam a busca por ajuda e a renegociação.
- **Mentalidade de escassez** (Mullainathan & Shafir): a falta crônica de
  recursos consome *mental bandwidth*, leva a decisões de curtíssimo prazo e
  ao "túnel" — debtors em escassez ignoram cartas e chamadas porque não
  conseguem absorver mais informação. Consequência prática: scripts longos,
  multi-cláusula, com várias opções, performam pior que ofertas únicas e claras.
- **Materialism + emotional gratification** drivers — preprint *Digital Credit
  and Debt Traps* (2025) atribui parte da inadimplência fintech em economias
  emergentes a vieses comportamentais (gratificação imediata, ancoragem em
  limites baixos crescentes, framing otimista do crédito) e à fragilidade da
  educação financeira no público C/D.
- **Default contagion psicológico**: depois do primeiro nome sujo, o devedor
  tende a "desistir" e parar de pagar outras contas.
- **Mistrust de canais financeiros** acentuado pós-Master/Will: Mastercard
  fallout (Yahoo Finance) e o "Master paradox" (FairObserver) mostram que a
  confiança é abalada não só na instituição falida mas no setor todo. Para
  cobrança, isso significa: **a primeira tarefa é validar a legitimidade da
  cobrança** antes de discutir valores.
- **Emoções em alta** (ansiedade, raiva, vergonha) desligam o sistema executivo
  (PMC #11867886): a pressão de cobrança, ainda mais em debtors low-income, é
  associada a sofrimento psicológico significativo. Cobrança hostil reduz
  cooperação a curto prazo e aumenta judicialização a longo prazo.

---

## 4. Scientific literature on collection strategy effectiveness

Findings below are drawn from peer-reviewed papers and large-scale industry
studies. Each is tagged with the *direction* of effect that should inform the
strategies in our YAML.

### 4.1 Empathy, motivational interviewing, and rapport

- Empathy-driven scripts increase recovery by **~20%+** vs high-pressure
  scripts (Empath Solutions / Advanced Collection Bureau; Redwood Collections;
  UNI KCM industry brief; McKinsey "Behavioral insights and innovative
  treatments in collections").
- **Pressão alta produz a "withholding response"** — debtors that *could* pay
  withhold payments after hostile contact (ACB).
- **Active listening + open questions** (motivational interviewing) shifts
  debtors from defensive to collaborative posture; effective especially when
  the debtor *intends* to pay but *cannot momentarily* — exactly Brazil's 77%.
- *Payoff*: empathic, autonomy-supportive opens are the dominant evidence-based
  default for the C/D, anxious, hardship segments.

### 4.2 Framing — loss, gain, and discount anchors

- **Loss framing dominates gain framing** in collections. McKinsey: framing a
  late-fee waiver as something the debtor *will lose if they do not pay this
  week* was **~2× more effective** than offering the same waiver as a reward.
- **Discount anchors** (the "save R$ X if you settle today") are powerful
  precisely because the unpaid balance is the anchor. The *Feirão Limpa Nome*
  (Serasa) leans into this with discounts of up to **99%** and immediate Pix
  *limpa nome*; in 2026 the *Feirão* had 2.200+ partner companies and is
  Brazil's largest renegotiation event.
- **Caveats** (Behavioral Economics Hub; ScienceDirect Medina 2021): poorly
  framed payoff scenarios *reduce* repayment when debtors anchor on the
  *minimum* payment instead of the full balance. Implication: discount offers
  must be paired with a clear primary number, not a menu.

### 4.3 Reminders and channel choice

- **SMS / digital reminders cut delinquency**. Karlan et al. (2016)
  demonstrated that adding the borrower's *name* in an SMS reminder
  significantly improves microloan repayment vs. a generic message (RG citation).
- Medina (2021), Brazil-specific RCT: digital repayment reminders reduced late
  fees paid by borrowers (ScienceDirect).
- Roll (2019) pilot: automated reminders cut **60-day delinquency by ~21%** and
  improved credit scores.
- **Personalization > prosocial appeals** (Sunstein-style PMC #11443582):
  personalized messages outperform moral/pro-social appeals, which often fail.
- **WhatsApp is the dominant Brazilian channel** — present on 99% of smartphones;
  industry standard for cobrança digital. Voll Solutions, Vindi, Blip, Recash,
  PG Mais all document chatbot-driven WhatsApp negotiations as the de-facto
  modern playbook for the C/D Brazilian segment, including in fintechs.

### 4.4 Implementation intentions, planning prompts, and self-service

- **Planning prompts** (BehavioralEconomics.com) — asking the debtor to pick
  a *specific* date / amount / channel raises follow-through. Implementation
  intentions of the form "I will pay X on day D via channel C" can lift
  promise-fulfillment rates substantially.
- **Self-service partial payments** (McKinsey) — letting the debtor pay any
  partial amount via app/portal, instead of forcing a "full deal", increases
  recovery in low-income segments where cash flow is volatile.
- **Cadence aligned with paycheck** (weekly / quincenal / dia 5) outperforms
  rigid monthly billing for hourly and informal workers — exactly the Will Bank
  base.

### 4.5 Reciprocity and prosocial connections

- Offering help beyond debt recovery (financial education, referrals to
  Procon/Defensoria/CRAS, Lei do Superendividamento renegotiation channels)
  builds reciprocity and improves cooperation on the immediate ask
  (Advanced Collection Bureau).

### 4.6 Behavioral segmentation > one-size-fits-all

- McKinsey: tailoring the script to the *psychological reason* for non-payment
  (vs. simply the bucket / aging) lifts effectiveness materially. Segments
  worth distinguishing in a Will Bank context:
  1. Want-to-pay-but-cannot (hardship; majority of NE C/D)
  2. Want-to-pay-but-confused-by-liquidation (post-Will-specific)
  3. Suspect-the-call-is-a-scam (post-Will-specific; FGC/Procon alerts)
  4. Disputers (write-proof requesters; CDC art.42)
  5. Avoidants (overwhelmed, multiple-contact debtors)
  6. Strategic / chronic over-indebted (superendividado, Lei 14.181 candidate)
  7. Serial renegotiators (Feirão Limpa Nome power-users; expect deep discounts)

---

## 5. Liquidation-era considerations specific to Will Bank

Special factors that change the right collection script for Willbank's debtors:

1. **Validity of the call must be proved first.** Debtors have been actively
   warned (FGC, Procon-SP, BCB) that scams impersonating Will Bank are circulating.
   The collector must volunteer the liquidator's name (EFB Regimes Especiais
   de Empresas Ltda.), the BCB liquidation reference, and direct the debtor to
   willbank.com.br / bcb.gov.br before asking for any payment data.
2. **Boleto-only.** Pix at Will is invalid. Any "pay by Pix" instruction is
   itself a red flag, not a legitimate ask.
3. **No card-on-file or new Pix.** The collector cannot accept card details
   (still risky) nor bank account details — only direct boleto.
4. **Discount authority is limited.** Collections that flow through the
   liquidator must respect the order of preference for creditors of the
   *massa liquidanda*. Aggressive haircuts that look great for the debtor may
   destroy value for the FGC's eventual ressarcimento. Settlement strategy must
   be calibrated to liquidator-approved policies, not to debtor-only economics.
5. **Comprovação**. Debtors should be encouraged to keep prints / records of
   payments and to bring documentation if they were materially blocked from
   paying — this buys legitimate negotiation room.
6. **Channel shift to liquidator's official channels.** All scripts should
   point debtors to credores@willbank.com.br / liquidante@willbank.com.br /
   willbank.com.br /  the BCB FAQ as the *only* legitimate channels.
7. **FGC confusion is endemic.** Debtors regularly conflate "FGC will return
   my money" with "FGC will pay my debt". The collector must clarify in plain
   language: FGC protege investidor, não devedor.
8. **Empathy must include the collapse itself.** Many debtors lost their
   primary salary account; some had their salário blocked on the day of
   liquidation (Serasa blog). Pretending nothing happened is tone-deaf and
   fuels mistrust.
9. **Consignado / FGTS antecipado continue automatically** — these debtors
   need no action, only a reassuring confirmation that nothing broke; pushing
   a hard ask here looks predatory.

Historical precedent (Cruzeiro do Sul, Banco Santos, BVA): credit portfolios
of failed banks are usually maintained or sold; debtors who keep paying on
schedule receive better credit-bureau treatment and avoid judicial collection
years later. The collector script can use this as a forward-looking reason
to pay (*"a sua dívida continuará registrada e administrada — manter os
pagamentos em dia preserva seu CPF e seu score"*).

---

## 6. Direct implications for the simulation

The redesign in `config/debtor_profiles.yaml` and `config/collector_strategies.yaml`
follows from the synthesis above. Concretely:

### 6.1 Profiles — what we keep, change, and add

- **Currency switches to BRL (R$).** All amounts in profiles, prompts, and the
  judge's constraint regex now match the Brazilian context.
- **Existing IDs preserved** for test compatibility:
  - `cooperative_hardship` → reframed as a **NE family-provider with reduced
    work hours**, anxious, *crédito pessoal* of R$ 850, willing up to R$ 80/mês,
    Pix removed, boleto-only.
  - `written_proof_disputer` → reframed as a **young professional disputing
    fees on a Will credit card**, primary objection grounded in CDC art. 42
    *cobrança indevida* and a request for *fatura detalhada* + contrato.
  - `hostile_avoidant` → reframed as an **overwhelmed family provider** with a
    R$ 1.900 utility-rooted debt, multiple contacts, post-liquidation distrust,
    refuses to share card/Pix during the call (echoes BCB scam alert).
- **New profiles added** to cover the segments where Will Bank actually has
  exposure but the original three did not represent:
  - `liquidation_confused` — does not know the bank still exists; afraid the
    cobrança is a *golpe*.
  - `scam_suspicious` — actively pattern-matches the call as fraud; will
    only engage after credibility is proven.
  - `feirao_serial_renegotiator` — Limpa Nome regular, anchored on 90%+
    discounts; will not move without a settlement.
  - `consignado_payroll_steady` — FGTS-anticipation / consignado debtor;
    cooperative because cash flow is stable; mostly needs reassurance.
  - `superendividado_chronic` — *superendividamento* (Lei 14.181) candidate;
    multiple credors; needs systemic answer, not a single deal.
  - `young_first_credit_card` — "AprovadoDoRolê" who lapsed on his first
    card; financially capable but disorganized; emotional shame.

### 6.2 Strategies — what we keep, change, and add

- **Existing IDs preserved** but reshaped to match the literature and the
  Will-specific constraints:
  - `empathetic_payment_plan` → motivational-interviewing-style open, NE-friendly
    register, parcela alinhada ao salário (5/15/30), boleto-only.
  - `assertive_settlement` → loss-framed *Feirão* discount with a credible
    deadline and a clear primary number; explicit compliance guardrails.
  - `neutral_reminder` → personalized SMS/WhatsApp-style reminder; named
    debtor, named amount, single CTA.
  - `problem_solving_callback` → empathetic discovery + agendamento explícito
    com data/hora/canal preferido (implementation intention).
- **New strategies added**:
  - `liquidation_explainer` — opens by validating the bank's situation,
    naming the liquidator, and providing scam-safety pointers before discussing
    money. Designed for `liquidation_confused` and `scam_suspicious`.
  - `whatsapp_self_service` — short, mobile-first, link-to-portal, planning
    prompt for date/channel/amount.
  - `superendividamento_referral` — recognizes Lei 14.181 candidates, refers
    to *audiência conciliatória* / Procon / Defensoria pathway, files a
    holding pattern instead of forcing a deal.
  - `consignado_confirmation` — for stable consignado debtors; reassurance,
    no ask, light verification of routing post-liquidation.

### 6.3 Prompt and judge updates

- `config/prompts.yaml` switches the displayed currency to **R$** and
  references "Will Bank em liquidação extrajudicial pelo Banco Central"
  in the system prompts so participants stay in the correct context.
- `src/collection_swarm/agents/judge.py` accepts amounts written either as
  `$200` or `R$ 200` (or `R$200`) when verifying the `max_payment` constraint.
  This is additive — existing `$` test cases continue to pass.
- `Collector` system prompt now includes a compliance line referencing
  CDC art. 42, Normativo SARB nº 27/2023 (calling hours), Lei 14.181, and
  the Will-specific scam-safety language.

---

## 7. References

- BCB. *Banco Central decreta liquidação extrajudicial da Will Financeira*.
  <https://www.bcb.gov.br/detalhenoticia/21001/nota>
- BCB. *Liquidação Extrajudicial da Will Financeira* (FAQ + liquidator contact).
  <https://www.bcb.gov.br/estabilidadefinanceira/will-financeira-liquidacao>
- BCB. *Bank Resolution* (Intervention, RAET, extrajudicial liquidation).
  <https://www.bcb.gov.br/en/financialstability/bankingresolution>
- Resolução CMN 4.949/2021 (relacionamento com clientes).
  <https://www.bcb.gov.br/estabilidadefinanceira/exibenormativo?tipo=Resolu%C3%A7%C3%A3o%20CMN&numero=4949>
- Resolução CMN 4.860/2020 (ouvidoria).
  <https://tpicap.com/tpbrasil/sites/g/files/escbpb221/files/Resolu%C3%A7%C3%A3o%20CMN%204.860-2020.pdf>
- FEBRABAN — Normativo SARB nº 27/2023 e Anuário 2024 de Autorregulação.
  <https://cmsarquivos.autorregulacaobancaria.com.br/Arquivos/documentos/PDF/Consolida%C3%A7%C3%A3o%20Normativa%20Relacionamento%20com%20o%20Consumidor%20-%20Normativo%2027-2023.pdf>
- Lei 14.181/2021 — Lei do Superendividamento. ANBC overview.
  <https://anbc.org.br/en/over-indebtedness-law-turns-2/>
- TJDFT. *Cobrança vexatória / art. 42 e 71 do CDC*.
  <https://www.tjdft.jus.br/consultas/jurisprudencia/jurisprudencia-em-temas/cdc-na-visao-do-tjdft-1/praticas-abusivas/proibicao-de-constrangimentos-ou-exposicao-do-consumidor-ao-ridiculo>
- Senacon. *Manual de Direitos do Consumidor*.
  <https://www.gov.br/mj/pt-br/assuntos/seus-direitos/consumidor/Anexos/manual-4a-edicao-2.pdf>
- G1 / Globo. *Liquidado pelo BC, Will Bank cresceu com foco em baixa renda*.
  <https://g1.globo.com/economia/negocios/noticia/2026/01/21/liquidado-pelo-bc-banco-digital-will-bank.ghtml>
- ISTOÉ Dinheiro. *De "banco dos invisíveis" à liquidação*.
  <https://istoedinheiro.com.br/trajetoria-historia-do-will-bank-21126>
- UOL Economia. *O que acontece com clientes do Will Bank, liquidado pelo BC*.
  <https://economia.uol.com.br/noticias/redacao/2026/01/21/o-que-acontece-com-clientes-do-will-bank-liquidado-pelo-bc.htm>
- Serasa. *Liquidação do will bank: o que aconteceu e o que muda para
  clientes*.
  <https://www.serasa.com.br/blog/liquidacao-do-will-bank/>
- Serasa Mapa da Inadimplência (mar/2026).
  <https://www.serasa.com.br/limpa-nome-online/blog/mapa-da-inadimplencia-e-renogociacao-de-dividas-no-brasil/>
- Serasa Limpa Nome — Feirão.
  <https://www.serasa.com.br/limpa-nome-online/feirao/>
- PEIC / CNC, ago/2025.
  <https://portaldocomercio.org.br/publicacoes_posts/pesquisa-de-endividamento-e-inadimplencia-do-consumidor-peic-agosto-de-2025/>
- Reuters. *Brazil central bank shuts Banco Pleno after Banco Master*.
  <https://www.reuters.com/world/americas/brazil-central-bank-shuts-banco-pleno-extrajudicial-liquidation-after-banco-2026-02-18/>
- Yahoo Finance. *Brazil central bank liquidates Banco Master's Will as
  Mastercard suspends cards*.
  <https://finance.yahoo.com/news/brazil-central-bank-liquidates-banco-123820637.html>
- FGC. *Pagamento de garantia* (Will Financeira / Banco Master).
  <https://www.fgc.org.br/pagamento-de-garantia>
- Gazeta do Povo. *FGC alerta para golpes a clientes afetados pelas liquidações
  do Master e Will Bank*.
  <https://www.gazetadopovo.com.br/economia/fgc-alerta-golpes-clientes-afetados-liquidacoes-master-will-bank/>
- Procon-SP — alertas pós-liquidação. Instagram.
  <https://www.instagram.com/p/DTyUtOEiall/>
- Will Bank — site institucional pós-liquidação.
  <https://www.willbank.com.br/>
- Will Bank Blog — *Como aumentar o limite do cartão de crédito*.
  <https://blog.willbank.com.br/como-aumentar-limite-do-cartao/>
- Will Bank Blog — *Como fazer empréstimo*.
  <https://blog.willbank.com.br/como-emprestimo/>
- MaisRetorno — *Will Bank entra em crédito pessoal com antecipação de
  saque-aniversário do FGTS*.
  <https://maisretorno.com/portal/will-bank-entra-em-credito-pessoal-com-antecipacao-de-saque-aniversario-do-fgts>
- FGV-EBAPE. *O grave quadro do endividamento das famílias no Nordeste*.
  <https://repositorio.fgv.br/items/efb8ab69-a3a5-42f2-997a-32a5207e1293>
- McKinsey. *Behavioral insights and innovative treatments in collections*.
  <https://www.mckinsey.com/capabilities/risk-and-resilience/our-insights/behavioral-insights-and-innovative-treatments-in-collections>
- BehavioralEconomics.com. *The Psychology of Debt Collection*.
  <https://www.behavioraleconomics.com/the-psychology-of-debt-collection/>
- Advanced Collection Bureau. *Empath Solutions* and *The Role of Behavioral
  Science in Effective Debt Collection*.
  <https://www.advancedcb.com/post/empath-solutions-debt-collection-a-new-approach>,
  <https://www.advancedcb.com/post/the-role-of-behavioral-science-in-effective-debt-collection>
- Medina, Pamela. *Reducing credit card delinquency using repayment reminders*
  (Brazil RCT).
  <https://www.sciencedirect.com/science/article/abs/pii/S0378426622001431>
- *Behavioral Messages and Debt Repayment* (Colombia RCT, Oxford Review of
  Finance).
  <https://academic.oup.com/rof/advance-article-pdf/doi/10.1093/rof/rfag015/68143797/rfag015.pdf>
- *Personalized messaging enhances hospital debt collection while prosocial
  appeals fail* (PMC #11443582).
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC11443582/>
- *Debt Collection Pressure and Mental Health* (PMC #11867886).
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC11867886/>
- Karlan et al. — *A personal touch in text messaging can improve microloan
  repayment*.
  <https://www.researchgate.net/publication/304441268>
- Roll, S. *The Impact of Automated Reminders on Credit Outcomes* (J. Consumer
  Affairs 2019).
  <https://onlinelibrary.wiley.com/doi/10.1111/joca.12252>
- Mullainathan & Shafir. *Scarcity: Why Having Too Little Means So Much*
  excerpt.
  <https://behavioralscientist.org/scarcity-excerpt-mullainathan-shafir/>
- Carta Capital. *77% dos inadimplentes querem pagar*.
  <https://www.cartacapital.com.br/do-micro-ao-macro/estudo-revela-que-77-dos-inadimplentes-querem-pagar-mas-ansiedade-e-burocracia-travam-acordos/>
- Veja. *Ansiedade e vergonha: estado emocional dos inadimplentes*.
  <https://veja.abril.com.br/coluna/radar-economico/ansiedade-e-vergonha-estudo-revela-estado-emocional-dos-inadimplentes/>
- Portal do Investidor / CVM. *Dívidas: fatores comportamentais e seus
  efeitos psicológicos*.
  <https://www.gov.br/investidor/pt-br/penso-logo-invisto/dividas-fatores-comportamentais-e-seus-efeitos-psicologicos>
- BCB working paper #476 — *Default Contagion among Credit Types: evidence
  from Brazilian data*.
  <https://ideas.repec.org/p/bcb/wpaper/476.html>
- Voll Solutions. *WhatsApp Business como protagonista da cobrança digital
  no Brasil*.
  <https://vollsolutions.com.br/blog/whatsapp/plataforma-whatsapp-business-como-protagonista-da-cobranca-digital-no-brasil/>
- Forbes Brasil. *Quando, por que e como ocorre uma liquidação extrajudicial
  bancária*.
  <https://forbes.com.br/forbes-money/2026/01/quando-por-que-e-como-ocorre-uma-liquidacao-extrajudicial-bancaria/>
- Estadão. *Dez anos após liquidação, Banco Cruzeiro do Sul começa a pagar
  credores*.
  <https://www.estadao.com.br/economia/coluna-do-broad/dez-anos-apos-liquidacao-banco-cruzeiro-do-sul-comeca-a-pagar-credores/>
