# Agents

<span class="cs-kicker">collection_swarm/agents/</span>

Three files, one job each. The agents are the LLM-facing layer:
they render prompts from configuration, push the resulting `LLMMessage`
list through the router, and return either an `LLMResponse` (Collector,
Debtor) or a parsed `Judgment` (Judge).

| Agent     | Role                                            | What it sees                                                 | What it returns                |
| --------- | ----------------------------------------------- | ------------------------------------------------------------- | ------------------------------ |
| Collector | Conducts negotiation per the chosen Strategy    | `Strategy`, `AccountData`, conversation `Transcript`         | `LLMResponse` (turn text)      |
| Debtor    | Plays the customer per the chosen Profile       | `Profile` (incl. constraints), conversation `Transcript`     | `LLMResponse` (turn text)      |
| Judge     | Evaluates the completed Simulation              | `Profile.constraints`, `AccountData`, full `Transcript`      | `Judgment` (parsed JSON + deterministic verifier output) |

The visibility table in [Domain model](../../concepts/domain-model.md#visibility-rules)
spells out which fields each agent can and cannot see. That separation
is enforced here, not in the engine.

## Per-agent pages

- [`collector.py`](collector.md)
- [`debtor.py`](debtor.md)
- [`judge.py`](judge.md)
