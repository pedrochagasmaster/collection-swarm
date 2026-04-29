# Collection Swarm — Project Specification

## 1. Overview

**Collection Swarm** is a simulation platform that runs multi-turn conversations between an AI **Collector Agent** and a variety of AI **Debtor Agents** (each embodying a distinct debtor profile). By running hundreds of simulated conversations with varying strategies, the system identifies which negotiation tactics, tone, and messaging work best for each debtor archetype — ultimately producing a **playbook** that real-world collectors can follow to maximize payment probability.

---

## 2. Problem Statement

Debt collection is a high-volume, low-conversion activity. Collectors often use a one-size-fits-all script, which fails because debtors have vastly different:

- Financial situations (temporary hardship vs. chronic insolvency)
- Psychological profiles (cooperative, avoidant, hostile, confused)
- Objection types ("I can't pay", "I don't owe this", "I forgot", "I'm disputing")
- Communication preferences (direct, empathetic, formal)

There is no scalable way to A/B test conversation strategies against every debtor type. This project solves that by simulating the entire space.

---

## 3. Core Concepts

### 3.1 Debtor Profiles

Each debtor profile is a structured persona with:

| Attribute              | Description                                              | Example Values                                      |
|------------------------|----------------------------------------------------------|-----------------------------------------------------|
| `archetype`            | High-level behavioral category                           | cooperative, avoidant, hostile, disputer, confused   |
| `financial_situation`  | Ability to pay                                           | can_pay_full, can_pay_partial, hardship, insolvent   |
| `debt_amount`          | Outstanding balance                                      | $500, $2,500, $15,000                               |
| `debt_age_days`        | How long the debt has been outstanding                   | 30, 90, 180, 365+                                   |
| `debt_type`            | Category of debt                                         | medical, credit_card, utility, auto_loan, student    |
| `prior_contact_count`  | Number of previous collection attempts                   | 0, 1-3, 4+                                          |
| `emotional_state`      | Starting emotional disposition                           | calm, anxious, angry, indifferent, ashamed           |
| `objection_type`       | Primary reason for non-payment                           | inability, dispute, forgetfulness, avoidance, refusal|
| `responsiveness`       | Likelihood of engaging in conversation                   | high, medium, low                                   |
| `demographics`         | Age bracket and context (affects communication style)    | young_professional, senior, family_provider          |

### 3.2 Collector Strategies

Each collector strategy is a configuration that governs the agent's behavior:

| Parameter              | Description                                              | Example Values                                      |
|------------------------|----------------------------------------------------------|-----------------------------------------------------|
| `tone`                 | Overall communication style                              | empathetic, assertive, neutral, urgent               |
| `opening_approach`     | How the conversation begins                              | soft_intro, direct_ask, problem_solving, reminder    |
| `negotiation_tactic`   | Primary negotiation lever                                | payment_plan, settlement_offer, deadline, empathy    |
| `escalation_style`     | How pressure is applied over the conversation            | gradual, immediate, none                             |
| `concession_willingness` | How flexible the collector is                          | rigid, moderate, flexible                            |
| `compliance_adherence` | Level of regulatory script adherence (FDCPA, etc.)       | strict, standard                                    |
| `follow_up_strategy`   | What the collector proposes for next steps               | callback, written_agreement, immediate_payment       |

### 3.3 Conversation Simulation

A single simulation run consists of:

1. **Setup** — A debtor profile and collector strategy are selected (or generated).
2. **Conversation** — The Collector Agent and Debtor Agent exchange messages in alternating turns (max N turns, configurable, default 20).
3. **Outcome Extraction** — After the conversation ends (naturally or at turn limit), a Judge Agent evaluates the result.
4. **Scoring** — The outcome is scored on multiple dimensions.

### 3.4 Outcome Scoring

The **Judge Agent** (a separate LLM call) reads the full transcript and produces:

| Metric                    | Type     | Description                                                |
|---------------------------|----------|------------------------------------------------------------|
| `payment_outcome`         | enum     | full_payment, partial_payment, payment_plan, promise_to_pay, no_commitment, refusal, hang_up |
| `payment_probability`     | float    | 0.0–1.0 estimated likelihood the debtor would actually pay |
| `debtor_satisfaction`     | float    | 0.0–1.0 how the debtor felt about the interaction          |
| `compliance_score`        | float    | 0.0–1.0 adherence to fair debt collection regulations      |
| `conversation_efficiency` | int      | Number of turns to reach outcome                           |
| `rapport_built`           | float    | 0.0–1.0 quality of relationship established                |
| `escalation_risk`         | float    | 0.0–1.0 risk of complaint, lawsuit, or brand damage        |

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    CLI / Runner                          │
│  (Orchestrates batch runs, reads config, writes output) │
└──────────────┬──────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│         Simulation Engine            │
│  - Pairs profiles with strategies    │
│  - Manages conversation loop         │
│  - Enforces turn limits & guardrails │
└──────┬───────────────┬───────────────┘
       │               │
       ▼               ▼
┌─────────────┐ ┌─────────────┐
│  Collector   │ │   Debtor    │
│    Agent     │ │    Agent    │
│ (LLM-based) │ │ (LLM-based) │
└─────────────┘ └─────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │   Judge Agent   │
              │ (scores result) │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │  Results Store   │
              │ (JSON / SQLite)  │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    Analyzer      │
              │ (aggregate stats,│
              │  produce playbook)│
              └─────────────────┘
```

### 4.1 Component Details

| Component            | Responsibility                                                                 |
|----------------------|--------------------------------------------------------------------------------|
| **CLI / Runner**     | Entry point. Accepts config (which profiles, strategies, how many runs). Parallel execution. |
| **Simulation Engine**| Manages a single conversation: alternates turns, injects system prompts, enforces limits. |
| **Collector Agent**  | LLM prompted with a collector strategy config. Speaks as the debt collector.   |
| **Debtor Agent**     | LLM prompted with a debtor profile. Simulates realistic debtor behavior.       |
| **Judge Agent**      | Post-conversation LLM call. Reads transcript, produces structured scores.      |
| **Results Store**    | Persists every conversation transcript + scores. SQLite for querying, JSON for portability. |
| **Analyzer**         | Aggregates results across runs. Finds best strategy per profile. Generates playbook. |

---

## 5. Tech Stack

| Layer          | Choice         | Rationale                                            |
|----------------|----------------|------------------------------------------------------|
| Language       | Python 3.12+   | LLM ecosystem, rapid prototyping                     |
| LLM Interface  | LiteLLM        | Provider-agnostic (OpenAI, Anthropic, local models)  |
| Data Storage   | SQLite          | Zero-config, good enough for thousands of runs       |
| Config         | YAML            | Human-readable profile and strategy definitions      |
| CLI            | Click           | Clean CLI with subcommands                           |
| Analysis       | Pandas          | Aggregation, pivot tables, stats                     |
| Output         | Rich + Markdown | Terminal-friendly reports + exportable playbooks      |

---

## 6. Project Structure

```
collection-swarm/
├── README.md
├── SPEC.md
├── pyproject.toml
├── requirements.txt
│
├── config/
│   ├── debtor_profiles.yaml      # All debtor persona definitions
│   ├── collector_strategies.yaml  # All collector strategy definitions
│   └── simulation.yaml            # Global settings (model, turn limit, etc.)
│
├── src/
│   └── collection_swarm/
│       ├── __init__.py
│       ├── cli.py                 # Click CLI entry point
│       ├── models.py              # Pydantic data models (Profile, Strategy, Score, etc.)
│       ├── agents/
│       │   ├── __init__.py
│       │   ├── collector.py       # Collector agent (prompt builder + LLM call)
│       │   ├── debtor.py          # Debtor agent (prompt builder + LLM call)
│       │   └── judge.py           # Judge agent (transcript → scores)
│       ├── engine.py              # Simulation engine (conversation loop)
│       ├── prompts/
│       │   ├── collector.py       # Collector system prompt templates
│       │   ├── debtor.py          # Debtor system prompt templates
│       │   └── judge.py           # Judge system prompt + output schema
│       ├── store.py               # SQLite persistence layer
│       └── analyzer.py            # Aggregation, ranking, playbook generation
│
├── output/                        # Generated reports and playbooks (gitignored)
│
└── tests/
    ├── test_models.py
    ├── test_engine.py
    ├── test_agents.py
    └── test_analyzer.py
```

---

## 7. Data Flow

### 7.1 Single Simulation Run

```
1. Load debtor profile P and collector strategy S from config
2. Build system prompts for Collector Agent and Debtor Agent
3. Collector sends opening message
4. Loop (up to max_turns):
   a. Debtor Agent responds to last collector message
   b. Check for conversation end signals (agreement, hang-up, stalemate)
   c. Collector Agent responds to last debtor message
   d. Check for conversation end signals
5. Pass full transcript to Judge Agent
6. Judge returns structured OutcomeScore
7. Store (P, S, transcript, OutcomeScore) in database
```

### 7.2 Batch Run

```
1. Load all profiles and strategies from config
2. Generate run matrix: each profile × each strategy × N repetitions
3. Execute simulations (parallel with configurable concurrency)
4. After all runs complete, run Analyzer
5. Analyzer outputs:
   a. Per-profile best strategy ranking
   b. Per-strategy effectiveness across profiles
   c. Overall playbook (Markdown document)
```

---

## 8. CLI Interface

```bash
# Run a full batch simulation
collection-swarm run --profiles config/debtor_profiles.yaml \
                     --strategies config/collector_strategies.yaml \
                     --repetitions 5 \
                     --concurrency 4

# Run a single simulation (interactive, prints transcript)
collection-swarm simulate --profile cooperative_hardship \
                          --strategy empathetic_payment_plan

# Analyze stored results and generate playbook
collection-swarm analyze --output output/playbook.md

# List available profiles and strategies
collection-swarm list-profiles
collection-swarm list-strategies
```

---

## 9. Prompt Design (Summary)

### 9.1 Collector Agent System Prompt

The collector receives:
- Role: "You are a professional debt collector..."
- Strategy parameters (tone, tactic, etc.) as behavioral instructions
- Debt details (amount, type, age) as context
- Constraints: must comply with FDCPA, must not threaten, must not misrepresent
- Goal: secure payment or payment commitment while maintaining professionalism

### 9.2 Debtor Agent System Prompt

The debtor receives:
- Role: "You are roleplaying as a debtor with the following profile..."
- Full profile attributes as personality/situation instructions
- Behavioral guidelines: respond realistically, don't be artificially cooperative or hostile beyond profile
- Internal state: hidden motivation, breaking points, what would actually convince them to pay

### 9.3 Judge Agent System Prompt

The judge receives:
- Role: "You are an expert evaluator of debt collection conversations..."
- The full transcript
- The scoring rubric (all metrics with clear definitions)
- Instructions to output a JSON object matching the OutcomeScore schema
- Must evaluate independently of the strategy label — only judge what happened in the conversation

---

## 10. Configuration Examples

### 10.1 Debtor Profile (YAML)

```yaml
profiles:
  - id: cooperative_hardship
    archetype: cooperative
    financial_situation: hardship
    debt_amount: 2500
    debt_age_days: 90
    debt_type: medical
    prior_contact_count: 1
    emotional_state: anxious
    objection_type: inability
    responsiveness: high
    demographics: family_provider
    backstory: >
      Recently lost a secondary income due to spouse's layoff.
      Wants to pay but genuinely cannot afford full amount right now.
      Open to payment plans if affordable. Feels guilty about the debt.

  - id: hostile_disputer
    archetype: hostile
    financial_situation: can_pay_full
    debt_amount: 800
    debt_age_days: 60
    debt_type: credit_card
    prior_contact_count: 3
    emotional_state: angry
    objection_type: dispute
    responsiveness: medium
    demographics: young_professional
    backstory: >
      Believes the charge is fraudulent or already paid.
      Has been contacted multiple times and is increasingly irritated.
      Will escalate to threats of legal action or complaints if pushed.
```

### 10.2 Collector Strategy (YAML)

```yaml
strategies:
  - id: empathetic_payment_plan
    tone: empathetic
    opening_approach: problem_solving
    negotiation_tactic: payment_plan
    escalation_style: none
    concession_willingness: flexible
    compliance_adherence: strict
    follow_up_strategy: written_agreement

  - id: assertive_settlement
    tone: assertive
    opening_approach: direct_ask
    negotiation_tactic: settlement_offer
    escalation_style: gradual
    concession_willingness: moderate
    compliance_adherence: strict
    follow_up_strategy: immediate_payment
```

---

## 11. Playbook Output

The final deliverable is a **Playbook** — a Markdown document structured as:

```
# Collection Playbook

## Profile: Cooperative Hardship
**Best Strategy:** Empathetic Payment Plan
**Payment Probability:** 78% (avg across 5 runs)
**Key Tactics:**
- Open with acknowledgment of their situation
- Propose a 3-month payment plan early in conversation
- Avoid any urgency or deadline language
**Sample Opening Lines:**
- "I understand you're going through a difficult time..."
**What to Avoid:**
- Assertive tone (drops probability to 31%)
- Settlement offers (perceived as insulting)

## Profile: Hostile Disputer
**Best Strategy:** Neutral + Validation
...
```

---

## 12. Development Plan

### Phase 1 — Foundation (MVP)
1. Set up project structure, dependencies, and config files
2. Implement Pydantic data models (`Profile`, `Strategy`, `Message`, `Transcript`, `OutcomeScore`)
3. Build prompt templates for all three agents
4. Implement the conversation engine (single run, sequential turns)
5. Implement the Judge agent with structured JSON output
6. Wire up CLI with `simulate` command (single run, print transcript + scores)
7. Create 5 debtor profiles and 4 collector strategies

### Phase 2 — Scale & Store
8. Implement SQLite storage layer
9. Implement batch runner with concurrency (asyncio)
10. Add `run` CLI command for batch execution
11. Add progress reporting (Rich progress bars)

### Phase 3 — Analysis & Playbook
12. Implement Analyzer: aggregate scores, rank strategies per profile
13. Implement playbook generator (Markdown output)
14. Add `analyze` CLI command

### Phase 4 — Refinement
15. Add more profiles (target: 15+ profiles covering the full matrix)
16. Add conversation guardrails (detect loops, force termination)
17. Add cost tracking (token usage per run)
18. Add support for different LLM models per agent role
19. Write tests

---

## 13. Key Design Decisions

| Decision                         | Choice                          | Rationale                                                        |
|----------------------------------|---------------------------------|------------------------------------------------------------------|
| Separate Judge Agent             | Yes (not self-scoring)          | Avoids bias — the collector/debtor agents shouldn't grade themselves |
| YAML config for profiles         | Yes                             | Non-developers (collection managers) can add/edit profiles       |
| SQLite over Postgres             | SQLite                          | Zero setup, single-file, sufficient for this workload            |
| LiteLLM over direct SDK          | LiteLLM                         | Swap providers without code changes                              |
| Async concurrency                | asyncio                         | LLM calls are I/O-bound; threads are wasteful                   |
| Structured output from Judge     | JSON mode / function calling    | Reliable parsing of scores                                      |
| Conversation as alternating turns| Fixed turn order                | Simpler than free-form; mirrors real phone/chat interactions     |

---

## 14. Compliance & Ethics Notes

- All collector agent prompts must include FDCPA compliance guardrails
- The system must never generate scripts that threaten, harass, or deceive
- The playbook should flag any strategy that scores high on `escalation_risk`
- This tool is for **training and strategy optimization**, not for direct consumer interaction
- No real consumer data is used — all profiles are synthetic

---

## 15. Success Criteria

1. The system can run 100+ simulated conversations in a single batch
2. Results show statistically meaningful differences between strategies per profile
3. The generated playbook provides actionable, profile-specific guidance
4. Compliance scores remain above 0.8 for all recommended strategies
5. The system is provider-agnostic (works with OpenAI, Anthropic, or local models)
