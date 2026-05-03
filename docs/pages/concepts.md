---
title: Core Concepts
layout: default
nav_order: 3
---

# Core Concepts
{: .no_toc }

The domain vocabulary and mental model behind Collection Swarm.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

## Simulation

A **Simulation** is a single synthetic conversation between a Collector and a Debtor, followed by a Judge evaluation. Each simulation produces a `SimulationResult` containing the full transcript, termination metadata, judgment scores, and token/cost information.

Simulations are the atomic unit of the system. Everything else — matrix runs, tournaments, evolution — is built by orchestrating many simulations.

## Participants

Every simulation has three AI **Participants**, each driven by an LLM (or the scripted fallback):

### Collector
The collection agent trying to reach a payment arrangement. Behavior is controlled by a **Strategy** (tone, tactic, escalation style, concession willingness, etc.) and informed by account data (debt amount, type, age, prior contacts).

### Debtor
The consumer being contacted. Behavior is controlled by a **Profile** (archetype, financial situation, emotional state, backstory, constraints). The debtor must stay in character and respect hard constraints like maximum payment amounts.

### Judge
An evaluator that reads the full transcript after the conversation ends. Produces a structured **Judgment** with 8 scored metrics. The Judge also runs deterministic constraint verification in addition to LLM-based scoring.

## Profile

A **Profile** defines a synthetic debtor persona. It includes:

- **Archetype** — cooperative, hostile, disputer, confused, skeptical, strategic, overwhelmed, etc.
- **Financial situation** — hardship, can_pay_partial, can_pay_full, insolvent, etc.
- **Emotional state** — anxious, angry, confused, calm, ashamed, etc.
- **Primary objection** — inability_to_pay, wants_written_proof, suspects_scam, etc.
- **Backstory** — A narrative paragraph in Portuguese describing the debtor's real-world context.
- **Constraints** — Machine-readable rules the debtor must never violate (e.g., max payment of R$80/month).
- **Account data** — Debt amount, type, age in days, and prior contact count.

Profiles are defined in `config/debtor_profiles.yaml`.

## Strategy

A **Strategy** defines how the Collector behaves. Core fields:

- **Tone** — empathetic, assertive, calm_informative, neutral, friendly_brief, etc.
- **Opening approach** — soft_intro, direct_ask, reminder, problem_solving, etc.
- **Negotiation tactic** — payment_plan, settlement_offer, defer_until_validated, etc.
- **Escalation style** — none, gradual, etc.
- **Concession willingness** — flexible, moderate, low, etc.
- **Compliance adherence** — strict (always).
- **Follow-up strategy** — written_agreement, immediate_payment, callback, portal, etc.

Optional fields extend strategies for the Will Bank/Brazilian context (payment channel, primary anchor, discovery questions, framing, discount authority, liquidation disclosure, cultural register, rationale).

Strategies are defined in `config/collector_strategies.yaml`.

## Constraint

A **Constraint** is a rule attached to a debtor profile that must not be violated during the conversation. Constraints have a human-readable `text` field and an optional machine-readable `rule` used for deterministic verification.

Two rule types:

| Type | Fields | Verified By |
|:-----|:-------|:------------|
| `max_payment` | `amount`, `frequency` | Judge checks if the debtor agreed to an amount exceeding the cap |
| `required_action` | `action` | Judge checks if the required action was performed (e.g., demanding written proof) |

The Judge verifies constraints deterministically (via regex and keyword matching) **in addition to** LLM-based scoring. This hybrid approach catches constraint violations even when the LLM judge fails to notice them.

## Judgment

A **Judgment** is the structured evaluation produced by the Judge after reading a simulation transcript. Fields:

| Metric | Type | Description |
|:-------|:-----|:------------|
| `reasoning` | string | Free-text explanation of the evaluation |
| `payment_outcome` | enum | Whether a payment arrangement was reached |
| `payment_probability` | 0–1 | Likelihood the debtor will follow through |
| `debtor_satisfaction` | 0–1 | How the debtor perceived the interaction |
| `compliance_score` | 0–1 | Adherence to regulatory standards |
| `conversation_efficiency` | int | Number of turns in the conversation |
| `rapport_built` | 0–1 | Quality of the working relationship |
| `escalation_risk` | 0–1 | Likelihood of complaint or litigation |
| `end_reason` | string | Why the conversation ended |
| `constraint_violations` | list | Profile constraints that were violated |

### Payment Outcomes

| Value | Description |
|:------|:------------|
| `full_payment` | Debtor agreed to pay the full amount |
| `partial_payment` | Debtor agreed to a partial settlement |
| `payment_plan` | Debtor agreed to an installment plan |
| `promise_to_pay` | Debtor promised to pay later |
| `no_commitment` | No payment arrangement was reached |
| `refusal` | Debtor explicitly refused to pay |
| `hang_up` | Debtor ended the call abruptly |

## Conversation Termination

A simulation ends when one of these conditions is met:

| Ended By | Trigger |
|:---------|:--------|
| `collector` | The collector's message contains `[END_CONVERSATION]` |
| `debtor` | The debtor's message contains `[END_CONVERSATION]` |
| `stalemate` | The last N turn-pairs are too similar (configurable threshold) |
| `turn_limit` | The maximum turn count was reached |

## Matrix Cell

A **MatrixCell** represents one unique combination of `(profile_id, strategy_id, conversation_model, judge_model)`. Matrix runs execute simulations for every cell, with optional repetitions per cell.

## Tournament

A **Tournament** is an Elo-rated competition that pairs strategies against profiles over multiple rounds. After each simulation, Elo ratings are updated for both the strategy and the profile. Supports Swiss pairing (minimizes repeats, matches by rating proximity) and round-robin formats.

## Elo Rating

Every strategy and profile has an **Elo rating** (starting at 1500) that moves up or down based on simulation outcomes. The effective score combines payment probability and compliance score by default. A strategy that achieves high payments with good compliance gains rating; a profile that resists collection effectively also gains rating.

## Strategy Evolution

The system can use LLMs to **evolve** collection strategies. Top-performing strategies serve as parents; the LLM generates new strategy variants by mutating and recombining the best traits while learning from failure transcripts. Underperforming strategies are culled.

## Profile Hardening

**Adversarial hardening** generates tougher debtor profiles by prompting an LLM to create variants that are harder to collect from while remaining realistic. This stress-tests strategies against edge cases.

## Playbook

A **Playbook** is a generated Markdown document that summarizes simulation results: strategy rankings per profile, compliance exclusions, objection frequencies, and example transcripts. It serves as an actionable reference for collection teams.
