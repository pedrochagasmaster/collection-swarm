# Concepts

Before you read the modules, read this. The codebase is small but
opinionated about its vocabulary, and a couple of the choices are easy to
miss until they bite you.

| Page                                            | What it covers                                                                                              |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| [Vocabulary](vocabulary.md)                     | Simulation vs Run, Participant vs Evaluator, Profile vs Persona vs Tags, Constraint vs Constraint Rule.      |
| [Domain model](domain-model.md)                 | The Pydantic objects that flow through the system, and how they relate.                                     |
| [Conversation lifecycle](conversation-lifecycle.md) | What actually happens turn by turn from `engine.run_simulation()` to a persisted `SimulationResult`.       |
| [Compliance & guardrails](compliance.md)        | The deterministic constraint verifier, the LLM Judge, and the `min_compliance_score` / `max_escalation_risk` exclusions. |
| [Arena & evolution](arena-and-evolution.md)     | Elo ratings, Swiss vs round-robin pairing, and how strategies mutate across generations.                    |
| [Judge calibration](judge-calibration.md)       | How human-labeled scores become a per-metric Pearson correlation, and how Judge prompt variants are tracked.|

If you only have time for one page, read [Vocabulary](vocabulary.md). It's
copied verbatim from `CONTEXT.md` and is the same vocabulary the rest of
this site uses.
