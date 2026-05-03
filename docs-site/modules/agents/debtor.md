# `agents/debtor.py` — the Debtor participant

<span class="cs-kicker">collection_swarm/agents/debtor.py</span>

A 33-line module symmetrical to the Collector, with one difference: the
Debtor uses chat-style alternating roles (`assistant` for its own past
turns, `user` for the Collector's turns) so the LLM stays in character
across longer conversations.

<dl class="cs-summary">
  <dt>Imports</dt><dd>backend types, router, domain models</dd>
  <dt>Visibility</dt><dd>Sees the full Profile (incl. constraints, persona, backstory); never sees the Strategy or analytical Tags</dd>
  <dt>Stateful?</dt><dd>No — the Profile is rendered into the system prompt every call</dd>
</dl>

## Construction

```python
class DebtorAgent:
    def __init__(self, router: LLMRouter, model_id: str, prompts: DebtorPromptConfig) -> None:
        self.router = router
        self.model_id = model_id
        self.prompts = prompts
```

Same shape as the Collector. Same model ID convention.

## Generating a turn

```python
async def generate_turn(self, profile: Profile, history: list[Message]) -> LLMResponse:
    messages = [_system_message(self.prompts, profile), *_history_messages(self.prompts, history)]
    return await self.router.complete(self.model_id, messages)
```

The system message is `prompts.debtor.system` formatted with the Profile
fields *and* the constraints rendered as `- ...` bullets. If the Profile
has no constraints, `prompts.debtor.constraints_empty` is substituted
(default `"- None"`).

The history is mapped turn by turn into `LLMMessage`s:

```python
for turn in history:
    role = "assistant" if turn.role == "debtor" else "user"
    content = prompts.debtor.history_message.format(role=turn.role.title(), content=turn.content)
    messages.append(LLMMessage(role=role, content=content))
```

This is the chat-style layout the Collector explicitly avoids. Two
reasons it's the right call here:

1. The Debtor must hold a stable persona across many turns. Most live
   chat-tuned models stay in character better when their own past turns
   come back as `assistant` messages.
2. The Debtor's content is short (1–3 sentences per turn by prompt
   instruction), so the larger token overhead of multi-message rendering
   is negligible.

## Persona contract

The shipped Debtor system prompt:

- Anchors on the Will Bank liquidation context.
- Tells the model it is a Brazilian consumer, not an AI assistant.
- Renders `archetype`, `financial_situation`, `emotional_state`,
  `primary_objection`, `responsiveness`, and `demographics` as Tags so
  the LLM can lean on them for tone.
- Renders the `backstory` as free text — this is the persona content.
- Lists the Constraints under "Restrições rígidas que você NÃO pode
  violar" so the LLM cannot wander off into a payment plan above the
  ceiling.
- Tells the LLM to never share card data, passwords, or accept Pix.
- Instructs the model to keep responses short and to emit
  `[END_CONVERSATION]` at a natural close.

The deterministic constraint verifier in
[`agents/judge.py`](judge.md#deterministic-constraint-verification)
catches any violation that does slip through.

## Implementation notes

- The system message is recomputed every turn — no caching. Same
  rationale as the Collector.
- The constraints list is the only Profile content the Debtor agent
  formats specially. Everything else is rendered through `.format(...)`
  on the prompt string.
- The Debtor agent is the most demanding role for the underlying model:
  it has to play a coherent persona, read context, and respect explicit
  hard floors. The model evaluation report
  ([`model_evaluation.py`](../model-evaluation.md)) carries
  per-Debtor-probe scores so you can pick the right model for the role.
