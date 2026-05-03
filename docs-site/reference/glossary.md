# Glossary

Quick A–Z cross-reference. The full prose is in
[Vocabulary](../concepts/vocabulary.md).

| Term                       | Short definition                                                                                       | Read more                                                                |
| -------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| **Account Data**           | Subset of the Profile visible to the Collector: debt amount, type, age, prior contacts.                 | [Vocabulary](../concepts/vocabulary.md#collector-strategies)              |
| **Compliance Exclusion**   | A per-(Profile, Strategy) determination that a Strategy is too risky to recommend.                      | [Compliance](../concepts/compliance.md#compliance-exclusions)             |
| **Constraint**             | A behavioral invariant the Debtor must never violate.                                                   | [Vocabulary](../concepts/vocabulary.md#debtor-profiles)                  |
| **Constraint Rule**        | The structured, machine-readable counterpart of a Constraint's text.                                    | [models.py](../modules/models.md#constraintrule)                         |
| **Constraint Violation**   | A finding that the Debtor acted outside its Constraints during a Simulation.                            | [Compliance](../concepts/compliance.md#layer-3-deterministic-constraint-verification) |
| **End Reason**             | Semantic classification of *why* a conversation ended (set by the Judge).                               | [Conversation lifecycle](../concepts/conversation-lifecycle.md#end-reason-vs-ended_by) |
| **End Signal**             | Mechanical `[END_CONVERSATION]` marker emitted by a Participant.                                        | [engine.py](../modules/engine.md#end-signals)                             |
| **Evaluator**              | The Judge agent.                                                                                        | [Vocabulary](../concepts/vocabulary.md#the-atoms)                        |
| **Judgment**               | Judge's complete output: reasoning, structured scores, end reason, constraint violations.               | [models.py](../modules/models.md#judgment)                                |
| **Judge Context**          | What the Judge sees: transcript, profile constraints, account data. Not the Strategy or Tags.            | [Vocabulary](../concepts/vocabulary.md#the-atoms)                        |
| **Matrix**                 | Combinatorial space of Simulations to execute (Profile × Strategy × repetitions).                       | [runner.py](../modules/runner.md)                                         |
| **Model Combo**            | The (conversation_model, judge_model) pair recorded as Simulation metadata.                             | [Vocabulary](../concepts/vocabulary.md#experiment-design)                |
| **Objection**              | A debtor's stated reason for not paying, classified against the taxonomy.                               | [analysis/objections.py](../modules/analysis/objections.md)               |
| **Objection Taxonomy**     | The canonical set of objection categories defined in `simulation.yaml`.                                 | [Configuration](configuration.md#simulationyaml)                           |
| **Participant**            | An agent that takes turns: Collector or Debtor.                                                         | [Vocabulary](../concepts/vocabulary.md#the-atoms)                        |
| **Payment Outcome**        | Categorical result ordered best-to-worst.                                                              | [Vocabulary](../concepts/vocabulary.md#payment-outcomes)                  |
| **Persona**                | The Profile's behavioral content (backstory, constraints, emotional state).                             | [Vocabulary](../concepts/vocabulary.md#debtor-profiles)                  |
| **Playbook**               | Markdown report aggregating recommendations, exclusions, and example transcripts.                       | [analysis/playbook.py](../modules/analysis/playbook.md)                  |
| **Primary Objection**      | The dominant resistance pattern assigned to a Profile as a Tag.                                         | [Vocabulary](../concepts/vocabulary.md#objections)                       |
| **Profile**                | Complete debtor definition: Tags + Persona + Constraints.                                                | [models.py](../modules/models.md#accountdata-and-profile)                |
| **Run**                    | A batch job that executes many Simulations.                                                            | [runner.py](../modules/runner.md)                                         |
| **Simulation**             | One conversation between Collector and Debtor plus the Judge's evaluation.                              | [engine.py](../modules/engine.md)                                         |
| **Strategy**               | Behavioral parameters that govern Collector conduct.                                                    | [models.py](../modules/models.md#strategy)                                |
| **Tags**                   | Categorical labels on a Profile used for grouping and analysis.                                          | [Vocabulary](../concepts/vocabulary.md#debtor-profiles)                  |
| **Transcript**             | Ordered sequence of Turns in a Simulation.                                                              | [engine.py](../modules/engine.md)                                         |
| **Turn**                   | A single message from one Participant.                                                                  | [Vocabulary](../concepts/vocabulary.md#conversation-lifecycle)           |
| **Turn Limit**             | Hard ceiling on conversation length.                                                                    | [Configuration](configuration.md#simulationyaml)                          |
