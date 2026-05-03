# SimulationEngine

> **Module:** `collection_swarm.engine`
> **Source:** `src/collection_swarm/engine.py`

The `SimulationEngine` drives a single debt-collection conversation between a
**Collector** agent and a **Debtor** agent, then hands the transcript to a
**Judge** for evaluation. It handles turn alternation, end-signal detection,
stalemate detection, token/cost tracking, and progress callbacks.

---

## Overview

```
┌──────────────┐     turn      ┌─────────────┐
│  Collector   │──────────────▶│   Debtor     │
│  Agent       │◀──────────────│   Agent      │
└──────┬───────┘               └──────┬───────┘
       │                              │
       │  transcript + profile        │
       ▼                              │
┌──────────────┐                      │
│    Judge      │◀────────────────────┘
└──────────────┘
       │
       ▼
  SimulationResult
```

A simulation proceeds as follows:

1. The **collector** generates a turn.
2. The engine checks for the `[END_CONVERSATION]` signal.
3. The **debtor** generates a response.
4. The engine checks for end signals and stalemate conditions.
5. Steps 1–4 repeat until a termination condition is met.
6. The **judge** evaluates the full transcript and produces a `Judgment`.

---

## Class: `SimulationEngine`

### Constructor

```python
from collection_swarm.engine import SimulationEngine

engine = SimulationEngine(
    collector=collector_agent,
    debtor=debtor_agent,
    judge=judge,
    max_turns=20,
    end_signal="[END_CONVERSATION]",
    stalemate_window=3,
    stalemate_similarity_threshold=0.6,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `collector` | `CollectorAgent` | *required* | The agent that plays the debt collector role. |
| `debtor` | `DebtorAgent` | *required* | The agent that plays the debtor role. |
| `judge` | `Judge` | *required* | Evaluates the completed transcript. |
| `max_turns` | `int` | `20` | Maximum number of messages before the simulation ends. |
| `end_signal` | `str` | `"[END_CONVERSATION]"` | Marker that either agent can embed in its response to end the conversation naturally. |
| `stalemate_window` | `int` | `3` | Number of recent turn-pairs to compare when checking for repetitive dialogue. |
| `stalemate_similarity_threshold` | `float` | `0.6` | Minimum `SequenceMatcher` ratio to consider two turns "similar enough" to constitute a stalemate. |

---

### Method: `run_simulation`

```python
async def run_simulation(
    self,
    profile: Profile,
    strategy: Strategy,
    on_progress: Callable[[SimulationResult], Awaitable[None] | None] | None = None,
) -> SimulationResult
```

Runs the full conversation loop and returns a `SimulationResult`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `profile` | `Profile` | The debtor profile that defines persona, financial situation, constraints, and backstory. |
| `strategy` | `Strategy` | The collector strategy that defines tone, negotiation tactics, and behavioral knobs. |
| `on_progress` | `Callable` or `None` | Optional callback invoked after every turn and after judgment. Accepts both sync and async callables. |

**Returns:** `SimulationResult` — contains the transcript, judgment, token counts, cost estimate, and metadata.

#### Turn Flow

```
while transcript length < max_turns:
    ┌─ Collector Turn ──────────────────────────────┐
    │  1. collector.generate_turn(strategy, account, │
    │     transcript)                                │
    │  2. Accumulate input/output tokens + cost      │
    │  3. Strip [END_CONVERSATION] signal            │
    │  4. Append Message(role="collector", ...)       │
    │  5. If ended → set ended_by = COLLECTOR        │
    └────────────────────────────────────────────────┘
              │
              ▼ notify on_progress
              │
    ┌─ Check: ended_by set? ────────────────────────┐
    │  YES → break                                   │
    │  NO  → continue                                │
    └────────────────────────────────────────────────┘
              │
    ┌─ Check: max_turns reached? ───────────────────┐
    │  YES → break                                   │
    │  NO  → continue                                │
    └────────────────────────────────────────────────┘
              │
    ┌─ Debtor Turn ─────────────────────────────────┐
    │  1. debtor.generate_turn(profile, transcript)  │
    │  2. Accumulate input/output tokens + cost      │
    │  3. Strip [END_CONVERSATION] signal            │
    │  4. Append Message(role="debtor", ...)          │
    │  5. If ended → set ended_by = DEBTOR           │
    └────────────────────────────────────────────────┘
              │
              ▼ notify on_progress
              │
    ┌─ Check: ended_by set OR stalemate? ───────────┐
    │  Stalemate detected → ended_by = STALEMATE     │
    │  Either true → break                           │
    └────────────────────────────────────────────────┘

After loop:
    • If ended_by is still None → ended_by = TURN_LIMIT
    • Set turn_count
    • Judge evaluates transcript
    • Accumulate judge tokens + cost
    • Set ended_at timestamp
    • Final on_progress notification
```

#### Termination Conditions

| Condition | `ended_by` Value | Description |
|-----------|-----------------|-------------|
| Collector includes `[END_CONVERSATION]` | `EndedBy.COLLECTOR` | The collector ended the conversation. |
| Debtor includes `[END_CONVERSATION]` | `EndedBy.DEBTOR` | The debtor ended the conversation. |
| Recent turns are repetitive | `EndedBy.STALEMATE` | Stalemate detected via `SequenceMatcher`. |
| Transcript reaches `max_turns` | `EndedBy.TURN_LIMIT` | Hard limit on conversation length. |

#### Error Handling

If any exception is raised during the simulation loop, the engine catches it and:

1. Sets `result.status` to `"failed"`.
2. Stores the exception message in `result.error_message`.
3. Records the current turn count and timestamp.
4. Fires a final progress notification.
5. Returns the partial result (no exception propagates to the caller).

```python
except Exception as exc:
    result.status = "failed"
    result.error_message = str(exc)
    result.turn_count = len(result.transcript)
    result.ended_at = utc_now()
    await _notify_progress(on_progress, result)
    return result
```

---

## Utility Functions

### `strip_end_signal`

```python
def strip_end_signal(
    content: str,
    signal: str = "[END_CONVERSATION]",
) -> tuple[str, bool]
```

Extracts the end-conversation marker from agent output.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `content` | `str` | *required* | Raw text from the agent. |
| `signal` | `str` | `"[END_CONVERSATION]"` | The marker string to look for. |

**Returns:** A tuple of `(cleaned_content, was_signal_found)`.

```python
>>> from collection_swarm.engine import strip_end_signal
>>> strip_end_signal("Thank you for your time. [END_CONVERSATION]")
('Thank you for your time.', True)
>>> strip_end_signal("Let me check on that for you.")
('Let me check on that for you.', False)
```

---

### `stalemate_detected`

```python
def stalemate_detected(
    transcript: list[Message],
    window: int = 3,
    threshold: float = 0.6,
) -> bool
```

Determines whether the conversation has entered a repetitive loop by comparing
recent collector/debtor turn-pairs against a baseline pair.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `transcript` | `list[Message]` | *required* | The conversation history so far. |
| `window` | `int` | `3` | Number of recent turn-pairs to examine. |
| `threshold` | `float` | `0.6` | Minimum similarity ratio (0.0–1.0) for a pair to be considered repetitive. |

**Returns:** `True` if all recent pairs within the window are similar enough to the baseline.

#### Algorithm

1. Count the number of complete collector/debtor pairs in the transcript.
2. If fewer than `window` pairs exist, return `False` (not enough data).
3. Select the baseline pair at index `pair_count - window`.
4. For each subsequent pair up to the most recent:
   - If the collector text differs from the baseline, compute `SequenceMatcher.ratio()`.
   - If the debtor text differs from the baseline, compute `SequenceMatcher.ratio()`.
   - If either ratio falls below `threshold`, return `False` (conversation is still evolving).
5. If all pairs pass the similarity check, return `True`.

!!! note "Case-insensitive comparison"
    All text is lowercased before comparison, so minor casing differences
    do not prevent stalemate detection.

---

## Progress Callback

The `on_progress` callback is invoked at the following points:

1. After each **collector turn**.
2. After each **debtor turn**.
3. After a **stalemate** is detected (if applicable).
4. After **judgment** is produced.
5. On **error** (with the partial result).

The callback may be either a synchronous or asynchronous function. The engine
uses `inspect.isawaitable` to detect and `await` async return values:

```python
async def _notify_progress(callback, result):
    if callback is None:
        return
    maybe_awaitable = callback(result)
    if isawaitable(maybe_awaitable):
        await maybe_awaitable
```

#### Sync callback example

```python
def log_progress(result: SimulationResult) -> None:
    print(f"Turn {result.turn_count}: {len(result.transcript)} messages")

await engine.run_simulation(profile, strategy, on_progress=log_progress)
```

#### Async callback example

```python
async def ws_progress(result: SimulationResult) -> None:
    await websocket.send_json(result.model_dump(mode="json"))

await engine.run_simulation(profile, strategy, on_progress=ws_progress)
```

---

## Complete Usage Example

```python
import asyncio
from collection_swarm.config import load_app_config
from collection_swarm.backends.router import LLMRouter
from collection_swarm.agents.collector import CollectorAgent
from collection_swarm.agents.debtor import DebtorAgent
from collection_swarm.agents.judge import Judge
from collection_swarm.engine import SimulationEngine

async def main():
    config = load_app_config("config")
    router = LLMRouter(config.models)

    model_id = config.default_conversation_model
    judge_id = config.default_judge_model

    engine = SimulationEngine(
        collector=CollectorAgent(router, model_id, config.prompts.collector),
        debtor=DebtorAgent(router, model_id, config.prompts.debtor),
        judge=Judge(router, judge_id, config.prompts.judge),
        max_turns=20,
        end_signal="[END_CONVERSATION]",
        stalemate_window=3,
        stalemate_similarity_threshold=0.6,
    )

    profile = config.profile("struggling_single_parent")
    strategy = config.strategy("empathetic_negotiator")

    result = await engine.run_simulation(profile, strategy)

    print(f"Status:   {result.status}")
    print(f"Turns:    {result.turn_count}")
    print(f"Ended by: {result.ended_by}")
    print(f"Cost:     ${result.estimated_cost_usd:.4f}")

    if result.judgment:
        print(f"Payment outcome: {result.judgment.payment_outcome}")
        print(f"Compliance:      {result.judgment.compliance_score:.2f}")

asyncio.run(main())
```

---

## Token and Cost Tracking

Every agent response carries token counts and a cost estimate. The engine
accumulates these across all turns and the judge evaluation:

| Field | Description |
|-------|-------------|
| `total_input_tokens` | Sum of input tokens across all collector, debtor, and judge calls. |
| `total_output_tokens` | Sum of output tokens across all calls. |
| `estimated_cost_usd` | Running dollar-cost estimate based on per-model pricing. |

These values are available on the `SimulationResult` after the simulation
completes (or fails).
