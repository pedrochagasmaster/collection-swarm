# `agents/collector.py` — the Collector participant

<span class="cs-kicker">collection_swarm/agents/collector.py</span>

A 33-line module. The Collector renders two prompts (system + history),
pushes them through the router, and returns the raw `LLMResponse`. The
engine handles end-signal stripping and accounting.

<dl class="cs-summary">
  <dt>Imports</dt><dd>backend types, router, domain models</dd>
  <dt>Visibility</dt><dd>Sees the Strategy and Account Data; never sees Profile constraints, persona, or backstory</dd>
  <dt>Stateful?</dt><dd>No — every call is independent</dd>
</dl>

## Construction

```python
class CollectorAgent:
    def __init__(self, router: LLMRouter, model_id: str, prompts: CollectorPromptConfig) -> None:
        self.router = router
        self.model_id = model_id
        self.prompts = prompts
```

The agent holds a reference to the router and the model ID. The same
router is shared across every agent in a Simulation; only the model ID
changes between roles.

## Generating a turn

```python
async def generate_turn(self, strategy: Strategy, account: AccountData, history: list[Message]) -> LLMResponse:
    messages = [
        LLMMessage(role="system", content=_system_prompt(self.prompts, strategy, account)),
        LLMMessage(role="user", content=_history_prompt(self.prompts, history)),
    ]
    return await self.router.complete(self.model_id, messages)
```

Two messages, every time:

1. **System prompt** — `prompts.collector.system` is `.format()`-ed with
   the Strategy fields and Account Data. The shipped Brazilian-Portuguese
   prompt cites the Will Bank liquidation, the regulatory backdrop, and
   the strategy knobs (tone, opening approach, negotiation tactic, etc.).
2. **User prompt** — `prompts.collector.history_empty` for the very first
   turn (no transcript yet), otherwise `prompts.collector.history` with
   the transcript rendered as `Collector:` / `Debtor:` lines.

Because the system prompt is rebuilt every turn, the LLM sees the
strategy on every call. There is no chat-style accumulation; the engine
treats each turn as a fresh completion with the full history attached.

## Why a separate `_history_prompt`

Two reasons:

- **Backend-agnostic.** The Collector emits a single user message instead
  of relying on multi-turn chat semantics. The same payload works for
  scripted, NIM, and Cursor SDK backends without per-backend hacks.
- **Predictable formatting.** The `transcript` placeholder is rendered
  with `f"{role.title()}: {content}"` so the LLM sees a consistent format
  regardless of whether the upstream provider is chat-tuned.

## Implementation notes

- **Empty history.** `prompts.history_empty` exists so the very first
  Collector turn can be initiated cleanly with "Initiate the conversation
  as a debt collector" or its localized equivalent.
- **No system prompt caching.** The Strategy is interpolated every turn,
  which is intentional — modifying the YAML between simulations should
  reflect immediately without restarting anything.
- **No response post-processing here.** End-signal stripping, token
  counting, and cost accounting all live in the engine, not the agent.
  The agent stays a one-method object.

## Where to extend

If you want the Collector to use tool calls or structured outputs, that
extension belongs in the backend layer — the agent's contract is "given
a Strategy + Account Data + Transcript, produce a turn". Adding tool
schemas inside the system prompt is the lowest-risk path; switching the
backend to a streaming or tool-call API is the heavier path.
