---
title: Simulation Engine
layout: default
nav_order: 4
---

# Simulation Engine
{: .no_toc }

The core conversation loop that orchestrates collector-debtor interactions.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Source:** `src/collection_swarm/engine.py`

## Overview

The `SimulationEngine` is the heart of Collection Swarm. It drives a single simulation by alternating turns between the `CollectorAgent` and `DebtorAgent`, then invoking the `Judge` to evaluate the resulting transcript.

## Class: `SimulationEngine`

### Constructor

```python
SimulationEngine(
    collector: CollectorAgent,
    debtor: DebtorAgent,
    judge: Judge,
    max_turns: int = 20,
    end_signal: str = "[END_CONVERSATION]",
    stalemate_window: int = 3,
    stalemate_similarity_threshold: float = 0.6,
)
```

| Parameter | Description |
|:----------|:------------|
| `collector` | The `CollectorAgent` that generates collector turns |
| `debtor` | The `DebtorAgent` that generates debtor turns |
| `judge` | The `Judge` that evaluates the completed transcript |
| `max_turns` | Maximum total messages before forced termination |
| `end_signal` | String token that signals voluntary conversation end |
| `stalemate_window` | Number of recent turn-pairs to compare for repetition |
| `stalemate_similarity_threshold` | Similarity ratio (0–1) above which turns are considered repetitive |

### Method: `run_simulation`

```python
async def run_simulation(
    self,
    profile: Profile,
    strategy: Strategy,
    on_progress: Callable[[SimulationResult], Awaitable[None] | None] | None = None,
) -> SimulationResult
```

Executes the full simulation lifecycle:

1. **Initialize** a `SimulationResult` with metadata (profile ID, strategy ID, model IDs, start time).
2. **Loop** alternating collector and debtor turns:
   - Generate a collector turn via `CollectorAgent.generate_turn()`.
   - Strip the end signal from the response. If found, mark `ended_by = COLLECTOR`.
   - Append the collector message to the transcript.
   - Generate a debtor turn via `DebtorAgent.generate_turn()`.
   - Strip the end signal. If found, mark `ended_by = DEBTOR`.
   - Append the debtor message.
   - Check for stalemate after each debtor turn.
3. If the loop exits without an explicit end, mark `ended_by = TURN_LIMIT`.
4. **Judge evaluation** — call `judge.evaluate()` with the full transcript and profile.
5. **Accumulate tokens and cost** from all agent responses.
6. **Error handling** — if any exception occurs, the result is marked `status = "failed"` with the error message preserved.

The optional `on_progress` callback is invoked after every turn and after judging, enabling real-time streaming in the web dashboard.

## Conversation Flow Diagram

```
┌──────────┐    ┌──────────┐    ┌──────────┐
│ Collector │◄──►│  Engine  │◄──►│  Debtor  │
└──────────┘    └────┬─────┘    └──────────┘
                     │
                     │ (after loop ends)
                     ▼
                ┌─────────┐
                │  Judge   │
                └─────────┘
                     │
                     ▼
             SimulationResult
```

## End Signal Detection

The `strip_end_signal` function scans each agent response for the `[END_CONVERSATION]` token:

```python
def strip_end_signal(content: str, signal: str = "[END_CONVERSATION]") -> tuple[str, bool]:
```

- Removes **all** occurrences of the signal from the content.
- Returns the cleaned text and a boolean indicating if the signal was present.
- The remaining content (without the signal) is what gets stored in the transcript.

## Stalemate Detection

The `stalemate_detected` function compares recent turn-pairs to detect repetitive conversations:

```python
def stalemate_detected(
    transcript: list[Message],
    window: int = 3,
    threshold: float = 0.6,
) -> bool
```

**Algorithm:**

1. Extract the last `window` collector-debtor pairs.
2. Take the **first** pair in the window as the baseline.
3. Compare each subsequent pair against the baseline using Python's `SequenceMatcher.ratio()`.
4. If **all** pairs within the window exceed the similarity threshold for **both** collector and debtor text, the conversation is declared a stalemate.

This prevents infinite loops where agents keep repeating similar messages.

### Tuning Stalemate Detection

| Parameter | Effect of Increasing | Default |
|:----------|:--------------------|:--------|
| `stalemate_window` | Requires more consecutive similar pairs → fewer false positives | 3 |
| `stalemate_similarity_threshold` | Requires higher similarity → only flags near-exact repetitions | 0.6 (config: 0.86) |

The production configuration in `config/simulation.yaml` uses a threshold of **0.86**, which is more permissive than the code default, requiring near-identical responses before triggering.

## Token and Cost Tracking

The engine accumulates `input_tokens`, `output_tokens`, and `estimated_cost_usd` from every `LLMResponse` returned by the agents. This includes:

- All collector turns
- All debtor turns
- The judge evaluation

Cost estimation is delegated to each backend, which calculates based on the model's configured `input_cost_per_m` and `output_cost_per_m` rates.

## Error Handling

If any exception occurs during the simulation (e.g., an LLM backend failure), the engine catches it and returns a `SimulationResult` with:

- `status = "failed"`
- `error_message` containing the exception string
- The transcript captured so far
- `ended_at` timestamp

This ensures that even failed simulations are recorded and can be analyzed.
