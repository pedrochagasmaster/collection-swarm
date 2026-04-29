# Collection Swarm

A simulation platform that runs AI-vs-AI debt collection conversations to discover which negotiation strategies work best for each debtor archetype.

## Language

**Simulation**:
A single conversation between a Collector and a Debtor, followed by a Judge's evaluation and scores.
_Avoid_: Run (when referring to a single conversation)

**Run**:
A batch job that executes many Simulations across a configured matrix of variables.
_Avoid_: Batch (use Run consistently)

**Participant**:
An agent that takes turns in a conversation — either a Collector or a Debtor.
_Avoid_: Agent (when distinguishing from the Judge)

**Evaluator**:
An agent that reads a completed transcript and produces a Judgment — the Judge.
_Avoid_: Agent (when distinguishing from Participants)

**Judgment**:
The Judge's complete output for a Simulation: a free-text reasoning, structured scores, an End Reason, and any Constraint Violations. The two-pass LLM process that produces it is an implementation detail.
_Avoid_: Score, Analysis (when referring to the whole output)

**Constraint Violation**:
A finding by the Judge that the Debtor acted outside its defined Constraints during a Simulation. Recorded as a list within the Judgment. An empty list means the Simulation data is trustworthy.

**Judge Context**:
The Judge sees the Transcript, the Profile's Constraints, and the Account Data. It does not see the Strategy definition or the Profile's Tags/Persona. The Judge evaluates the conversation on its merits, not on what was intended.

### Debtor Profiles

**Profile**:
A complete debtor definition combining Tags and a Persona.
_Avoid_: Debtor (when referring to the configuration, not the role in conversation)

**Tags**:
Categorical labels on a Profile used for grouping and analysis (archetype, financial_situation, objection_type, etc.). Metadata *about* the Profile, not instructions to the LLM.

**Persona**:
The behavioral content of a Profile that drives LLM behavior: backstory, constraints, emotional_state. This is what gets injected into the Debtor's system prompt.

**Constraint**:
A behavioral invariant on a Profile that the Debtor must never violate, regardless of Collector pressure (e.g., "will NEVER agree to more than $150/month"). A hard floor, not soft resistance. Violations indicate unreliable Simulation data and should be flagged by the Judge. Each Constraint has a natural-language `text` (injected into the Debtor's prompt) and an optional structured `rule` (used for deterministic verification).

**Constraint Rule**:
The machine-readable counterpart of a Constraint's natural-language text. Expressed as a typed rule in the Profile YAML (e.g., `type: max_payment, amount: 150, frequency: monthly`). Used by the Judge module to programmatically verify violations after LLM scoring, catching violations the LLM missed. Not all Constraints have Rules — those that can't be expressed structurally remain LLM-only. The structured layer is additive, not a replacement.
_Avoid_: Using "rule" alone without "Constraint" context — always "Constraint Rule."

### Collector Strategies

**Strategy**:
A set of behavioral parameters that govern how the Collector conducts a conversation (tone, tactic, escalation style, etc.). All parameters are both LLM instructions and analytical dimensions — no separate metadata layer needed.

**Account Data**:
The subset of Profile information visible to the Collector: debt_amount, debt_type, debt_age_days, prior_contact_count. Mirrors what a real collector would see in an account file. All other Profile attributes (archetype, emotional state, backstory, constraints) are hidden from the Collector.

### Conversation Lifecycle

**Turn**:
A single message from one Participant in a conversation.

**Transcript**:
The ordered sequence of all Turns in a Simulation.

**End Signal**:
The mechanical `[END_CONVERSATION]` marker a Participant emits to stop the conversation. Carries no semantic meaning — just "stop."

**End Reason**:
The semantic classification of *why* a conversation ended (e.g., agreement_reached, debtor_hung_up, debtor_deferred, collector_closed, no_resolution). Determined by the Judge as part of the Judgment, not by the engine.
_Avoid_: Conflating with ended_by, which is purely mechanical (who emitted the End Signal)

**Turn Limit**:
The hard ceiling on conversation length (default 20 turns). The only mechanical termination guard beyond End Signals. Stalemate detection is deferred — not needed until evidence shows conversations routinely hit the limit without resolution.

### Objections

**Objection**:
A debtor's stated reason for not paying, classified against a shared taxonomy.

**Primary Objection**:
The dominant resistance pattern assigned to a Profile as a Tag. A conversation may surface additional objections beyond this one.
_Avoid_: objection_type (ambiguous — sounds like the only objection)

**Objection Taxonomy**:
The canonical set of objection categories (inability_to_pay, disputes_debt, wants_written_proof, etc.). Seeded with ~12 categories; novel categories discovered during extraction are added dynamically.

### Experiment Design

**Matrix**:
The combinatorial space of Simulations to execute: Profile × Strategy × repetitions. Model is recorded but not a primary axis. The repetition count is the target number of *completed* Simulations per cell — failed Simulations are backfilled, not counted toward the target.

**Model Combo**:
The (conversation_model, judge_model) pair used for a Simulation. Recorded as metadata for secondary analysis, but results are pooled across models for the primary Playbook.
_Avoid_: Treating model as a primary experimental variable in the default analysis

### Compliance

**Compliance Exclusion**:
A per-(Profile, Strategy) determination that a Strategy is too risky to recommend for a given Profile. Triggered when compliance_score < 0.8 or escalation_risk > 0.3 across Simulations for that pair. A Strategy can be excluded for one Profile and recommended for another.

### Payment Outcomes

**Payment Outcome**:
The categorical result of a Simulation, ordered from best to worst:
- **full_payment** — debtor agrees to pay the entire balance
- **partial_payment** — debtor agrees to pay a reduced amount (settlement)
- **payment_plan** — structured agreement with specific terms (amount, frequency, duration)
- **promise_to_pay** — unstructured verbal commitment without specific terms
- **no_commitment** — conversation ended without the debtor taking a position either way
- **refusal** — explicit "I will not pay"
- **hang_up** — debtor terminated the conversation abruptly

### Outputs

**Playbook**:
A snapshot report generated from all Simulations in the database. Contains per-Profile strategy recommendations, objection responses, example transcripts, and compliance exclusions. Disposable and regenerable — not a living document. Strategy ranking is driven by payment_probability as the primary metric, with all other dimensions shown for transparency. When two strategies cannot be statistically separated after maximum repetitions, they are reported as **statistically tied** — no false winner is forced.

## Relationships

- A **Run** produces one or more **Simulations**
- A **Simulation** has exactly two **Participants** (one Collector, one Debtor) and one **Evaluator** (the Judge)
- A **Simulation** produces one **Transcript** and one **Judgment**
- A **Judgment** contains scores, an **End Reason**, and zero or more **Constraint Violations**
- A **Profile** has **Tags** (for analysis) and a **Persona** (for LLM behavior), plus **Constraints** (hard behavioral invariants)
- A **Profile** exposes **Account Data** to the Collector and **Constraints** to the Judge
- A **Strategy** is paired with a **Profile** to form one cell in the **Matrix**
- A **Compliance Exclusion** applies to a (Profile, Strategy) pair, not to a Strategy globally
- A **Playbook** is generated from all completed **Simulations** in the database
- The **Objection Taxonomy** classifies both **Primary Objections** on Profiles and objections extracted from **Transcripts**

## Example dialogue

> **Dev:** "A Simulation failed halfway through — do we retry it?"
> **Domain expert:** "No. A new **Simulation** is scheduled to backfill that **Matrix** cell. The failed one stays in the database with its partial **Transcript**, but it doesn't count toward the repetition target."

> **Dev:** "The Judge gave this conversation a low compliance score. Should we exclude the Strategy?"
> **Domain expert:** "Only for this **Profile**. Check the **Compliance Exclusion** threshold across all **Simulations** for that (Profile, Strategy) pair. The same **Strategy** might be fine for a different **Profile**."

> **Dev:** "The Debtor agreed to $200/month but their **Constraint** says never more than $150/month."
> **Domain expert:** "That's a **Constraint Violation**. The **Judgment** should flag it. The **Simulation** data is unreliable — don't exclude it, but don't trust the outcome scores."

## Flagged ambiguities

- "run" was used to mean both a single conversation and a batch of conversations — resolved: the atom is a **Simulation**, the batch job is a **Run**.
- "agent" was used for both conversation participants and the post-hoc evaluator — resolved: **Participant** for Collector/Debtor, **Evaluator** for the Judge. "Agent" is fine informally but the distinction matters architecturally.
