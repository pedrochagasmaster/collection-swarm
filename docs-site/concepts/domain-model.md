# Domain model

Every object that flows through Collection Swarm is a Pydantic model
defined in [`models.py`](../modules/models.md). This page is the visual
overview; the module page is the field-by-field reference.

## Class diagram

```mermaid
classDiagram
    direction LR

    class Profile {
      +str id
      +str archetype
      +str financial_situation
      +float debt_amount
      +int debt_age_days
      +str debt_type
      +int prior_contact_count
      +str emotional_state
      +str primary_objection
      +str responsiveness
      +str demographics
      +str backstory
      +list~Constraint~ constraints
      +AccountData account_data
    }
    class AccountData {
      +float debt_amount
      +int debt_age_days
      +str debt_type
      +int prior_contact_count
    }
    class Constraint {
      +str text
      +ConstraintRule? rule
    }
    class ConstraintRule {
      +Literal type
      +float? amount
      +str? frequency
      +str? action
    }

    class Strategy {
      +str id
      +str tone
      +str opening_approach
      +str negotiation_tactic
      +str escalation_style
      +str concession_willingness
      +str compliance_adherence
      +str follow_up_strategy
      +str? payment_channel
      +str? primary_anchor
      +str? rationale
    }

    class Message {
      +Literal role
      +str content
    }

    class Judgment {
      +str reasoning
      +PaymentOutcome payment_outcome
      +float payment_probability
      +float debtor_satisfaction
      +float compliance_score
      +int conversation_efficiency
      +float rapport_built
      +float escalation_risk
      +str end_reason
      +list~str~ constraint_violations
    }

    class SimulationResult {
      +str id
      +str status
      +str profile_id
      +str strategy_id
      +str conversation_model
      +str judge_model
      +datetime started_at
      +datetime? ended_at
      +int turn_count
      +EndedBy? ended_by
      +list~Message~ transcript
      +Judgment? judgment
      +int total_input_tokens
      +int total_output_tokens
      +float estimated_cost_usd
    }

    Profile *-- "0..*" Constraint
    Constraint *-- "0..1" ConstraintRule
    Profile --> AccountData : derives
    SimulationResult *-- "0..*" Message : transcript
    SimulationResult *-- "0..1" Judgment
    SimulationResult --> Profile : profile_id
    SimulationResult --> Strategy : strategy_id
```

## How the data is sourced

| Object               | Source                                              |
| -------------------- | --------------------------------------------------- |
| `Profile`            | `config/debtor_profiles.yaml`                       |
| `Strategy`           | `config/collector_strategies.yaml`                  |
| `ModelConfig`        | `config/models.yaml`                                |
| `PromptConfig`       | `config/prompts.yaml`                               |
| `SimulationSettings` | `config/simulation.yaml`                            |
| `Message`            | Generated turn by turn by Collector / Debtor agents  |
| `Judgment`           | Returned by the Judge agent (LLM JSON + parser)      |
| `SimulationResult`   | Built by `SimulationEngine.run_simulation()`         |

## Visibility rules

This is the most important slide:

| Object        | Collector sees | Debtor sees | Judge sees                |
| ------------- | -------------- | ----------- | ------------------------- |
| `Strategy`    | Yes            | No          | No                        |
| `Profile.persona` (backstory, constraints, emotional_state) | No | Yes | Constraints only |
| `AccountData` (debt amount, type, age, prior contacts) | Yes | Implicit (via persona) | Yes |
| `Transcript`  | Yes (history)  | Yes (history) | Yes (full)              |

The Judge does not see the Strategy definition or the Profile's
analytical Tags. It evaluates the conversation on its merits, not on what
was *intended*. This separation is what makes the Judge a credible
evaluator instead of a rubber-stamp on the Collector's plan.

## Tournament & evolution data

The arena and evolution loops add a few more shapes on top:

| Object              | Where it lives                          |
| ------------------- | --------------------------------------- |
| `EloRating`         | `elo_ratings` SQLite table              |
| `EloUpdate`         | `elo_history` SQLite table              |
| `TournamentConfig`  | `config/simulation.yaml` (`arena:`)     |
| `TournamentResult`  | `tournaments` SQLite table              |
| `EvolutionConfig`   | CLI flags / programmatic `EvolutionConfig` |
| `StrategyLineage`   | `evolved_strategies` SQLite table       |
| `ProfileLineage`    | `evolved_profiles` SQLite table         |

See [Arena & evolution](arena-and-evolution.md) for how they tie back into
`SimulationResult`.
