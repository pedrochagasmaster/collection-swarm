# Vocabulary

This page is the authoritative glossary for the project. It mirrors
[`CONTEXT.md`](https://github.com/pedrochagasmaster/collection-swarm/blob/main/CONTEXT.md)
in the repository root. If a term is ambiguous, look here first.

## The atoms

**Simulation**
: A single conversation between a Collector and a Debtor, followed by a
  Judge's evaluation and scores. *Avoid:* "Run" when referring to a single
  conversation.

**Run**
: A batch job that executes many Simulations across a configured matrix of
  variables. *Avoid:* "Batch" — use Run consistently.

**Participant**
: An agent that takes turns in a conversation — either a Collector or a
  Debtor. *Avoid:* "Agent" when distinguishing from the Judge.

**Evaluator**
: An agent that reads a completed transcript and produces a Judgment — the
  Judge. *Avoid:* "Agent" when distinguishing from Participants.

**Judgment**
: The Judge's complete output for a Simulation: free-text reasoning,
  structured scores, an End Reason, and any Constraint Violations. The
  two-pass LLM process that produces it is an implementation detail.
  *Avoid:* "Score" or "Analysis" when referring to the whole output.

**Constraint Violation**
: A finding by the Judge that the Debtor acted outside its defined
  Constraints during a Simulation. Recorded as a list within the Judgment.
  An empty list means the Simulation data is trustworthy.

**Judge Context**
: The Judge sees the Transcript, the Profile's Constraints, and the
  Account Data. It does *not* see the Strategy definition or the Profile's
  Tags / Persona. The Judge evaluates the conversation on its merits, not
  on what was intended.

## Debtor profiles

**Profile**
: A complete debtor definition combining Tags and a Persona. *Avoid:*
  "Debtor" when referring to the configuration, not the role in
  conversation.

**Tags**
: Categorical labels on a Profile used for grouping and analysis
  (`archetype`, `financial_situation`, `objection_type`, etc.). Metadata
  *about* the Profile, not instructions to the LLM.

**Persona**
: The behavioral content of a Profile that drives LLM behavior:
  `backstory`, `constraints`, `emotional_state`. This is what gets
  injected into the Debtor's system prompt.

**Constraint**
: A behavioral invariant on a Profile that the Debtor must never violate,
  regardless of Collector pressure (e.g., "will NEVER agree to more than
  R$ 80/mês"). A hard floor, not soft resistance. Each Constraint has a
  natural-language `text` (injected into the Debtor's prompt) and an
  optional structured `rule` (used for deterministic verification).

**Constraint Rule**
: The machine-readable counterpart of a Constraint's natural-language
  text. Expressed as a typed rule in the Profile YAML
  (e.g., `type: max_payment, amount: 80, frequency: monthly`). Used by the
  Judge module to programmatically verify violations after LLM scoring,
  catching violations the LLM missed. Not all Constraints have Rules —
  those that can't be expressed structurally remain LLM-only. *Avoid:*
  using "rule" alone without "Constraint" context — always **Constraint
  Rule**.

## Collector strategies

**Strategy**
: A set of behavioral parameters that govern how the Collector conducts a
  conversation: `tone`, `negotiation_tactic`, `escalation_style`,
  `concession_willingness`, `compliance_adherence`, `follow_up_strategy`,
  and several optional refinements. All parameters are *both* LLM
  instructions *and* analytical dimensions — no separate metadata layer
  needed.

**Account Data**
: The subset of Profile information visible to the Collector:
  `debt_amount`, `debt_type`, `debt_age_days`, `prior_contact_count`.
  Mirrors what a real collector would see in an account file. All other
  Profile attributes (archetype, emotional state, backstory, constraints)
  are hidden from the Collector.

## Conversation lifecycle

**Turn**
: A single message from one Participant in a conversation.

**Transcript**
: The ordered sequence of all Turns in a Simulation.

**End Signal**
: The mechanical `[END_CONVERSATION]` marker a Participant emits to stop
  the conversation. Carries no semantic meaning — just "stop".

**End Reason**
: The semantic classification of *why* a conversation ended (e.g.,
  `agreement_reached`, `debtor_hung_up`, `debtor_deferred`,
  `collector_closed`, `no_resolution`). Determined by the Judge as part of
  the Judgment, not by the engine. *Avoid:* conflating with `ended_by`,
  which is purely mechanical (who emitted the End Signal).

**Turn Limit**
: The hard ceiling on conversation length (default 12 turns; configurable
  in `config/simulation.yaml`). The only mechanical termination guard
  beyond End Signals. Stalemate detection complements the Turn Limit by
  short-circuiting cycling conversations.

## Objections

**Objection**
: A debtor's stated reason for not paying, classified against a shared
  taxonomy.

**Primary Objection**
: The dominant resistance pattern assigned to a Profile as a Tag. A
  conversation may surface additional objections beyond this one. *Avoid:*
  `objection_type` (ambiguous — sounds like the only objection).

**Objection Taxonomy**
: The canonical set of objection categories (`inability_to_pay`,
  `disputes_debt`, `wants_written_proof`, etc.). Defined in
  `config/simulation.yaml`. New categories discovered during extraction
  may be added.

## Experiment design

**Matrix**
: The combinatorial space of Simulations to execute: Profile × Strategy ×
  repetitions. Model is recorded but not a primary axis. The repetition
  count is the target number of *completed* Simulations per cell — failed
  Simulations are backfilled, not counted toward the target.

**Model Combo**
: The (`conversation_model`, `judge_model`) pair used for a Simulation.
  Recorded as metadata for secondary analysis, but results are pooled
  across models for the primary Playbook. *Avoid:* treating model as a
  primary experimental variable in the default analysis.

## Compliance

**Compliance Exclusion**
: A per-(Profile, Strategy) determination that a Strategy is too risky to
  recommend for a given Profile. Triggered when
  `compliance_score < 0.8` or `escalation_risk > 0.3` across Simulations
  for that pair. A Strategy can be excluded for one Profile and
  recommended for another.

## Payment outcomes

**Payment Outcome**
: The categorical result of a Simulation, ordered from best to worst:

| Value              | Meaning                                                                |
| ------------------ | ---------------------------------------------------------------------- |
| `full_payment`     | Debtor agrees to pay the entire balance                                |
| `partial_payment`  | Debtor agrees to pay a reduced amount (settlement)                     |
| `payment_plan`     | Structured agreement with specific terms (amount, frequency, duration) |
| `promise_to_pay`   | Unstructured verbal commitment without specific terms                  |
| `no_commitment`    | Conversation ended without a position either way                       |
| `refusal`          | Explicit "I will not pay"                                              |
| `hang_up`          | Debtor terminated the conversation abruptly                            |

## Outputs

**Playbook**
: A snapshot report generated from all Simulations in the database.
  Contains per-Profile strategy recommendations, objection responses,
  example transcripts, and compliance exclusions. Disposable and
  regenerable — not a living document. Strategy ranking is driven by
  `payment_probability` as the primary metric, with all other dimensions
  shown for transparency.

## Relationships at a glance

- A **Run** produces one or more **Simulations**.
- A **Simulation** has exactly two **Participants** (one Collector, one
  Debtor) and one **Evaluator** (the Judge).
- A **Simulation** produces one **Transcript** and one **Judgment**.
- A **Judgment** contains scores, an **End Reason**, and zero or more
  **Constraint Violations**.
- A **Profile** has **Tags** (for analysis) and a **Persona** (for LLM
  behavior), plus **Constraints** (hard behavioral invariants).
- A **Profile** exposes **Account Data** to the Collector and
  **Constraints** to the Judge.
- A **Strategy** is paired with a **Profile** to form one cell in the
  **Matrix**.
- A **Compliance Exclusion** applies to a (Profile, Strategy) pair, not
  to a Strategy globally.
- A **Playbook** is generated from all completed **Simulations** in the
  database.
- The **Objection Taxonomy** classifies both **Primary Objections** on
  Profiles and objections extracted from **Transcripts**.
