# `engine.py` — the simulation engine

<span class="cs-kicker">collection_swarm/engine.py</span>

The 145-line engine that runs one Simulation end-to-end. It owns the
turn loop, the termination guards, the token / cost accounting, and the
optional progress callback. Everything before it is configuration;
everything after it is persistence and reporting.

<dl class="cs-summary">
  <dt>Imports</dt><dd><code>collections.abc</code>, <code>difflib</code>, <code>inspect</code>, the agents, the domain models</dd>
  <dt>Dependencies</dt><dd>A pre-built <code>CollectorAgent</code>, <code>DebtorAgent</code>, and <code>Judge</code> — the engine never touches the router directly</dd>
  <dt>Concurrency</dt><dd>Async by design; the runner schedules many engines under <code>asyncio.gather</code></dd>
</dl>

## Constructor

```python
class SimulationEngine:
    def __init__(
        self,
        collector: CollectorAgent,
        debtor: DebtorAgent,
        judge: Judge,
        max_turns: int = 20,
        end_signal: str = "[END_CONVERSATION]",
        stalemate_window: int = 3,
        stalemate_similarity_threshold: float = 0.6,
    ) -> None: ...
```

The engine is given pre-built agents. This is intentional: the same
engine should work whether the agents talk to a scripted backend, a NIM
endpoint, a Cursor SDK subprocess, or a future provider. The engine
doesn't know the difference.

## `run_simulation()`

```python
async def run_simulation(
    self,
    profile: Profile,
    strategy: Strategy,
    on_progress: Callable[[SimulationResult], Awaitable[None] | None] | None = None,
) -> SimulationResult: ...
```

Lifecycle:

1. Builds an empty `SimulationResult` stamped with the model identifiers
   from the agents and a fresh `started_at`.
2. Enters the turn loop:
   - `_add_collector_turn` → progress callback → break-on-end-signal.
   - `_add_debtor_turn` → progress callback → break-on-end-signal or
     stalemate.
3. If the loop exits with no `ended_by`, stamps `EndedBy.TURN_LIMIT`.
4. Calls `judge.evaluate(transcript, profile)`. The Judge's last
   `LLMResponse` is folded into the running token / cost totals on the
   result.
5. Stamps `ended_at = utc_now()` and runs the final progress callback.

If anything raises inside the loop, the engine catches it, sets
`status="failed"`, captures `error_message`, and still returns a
`SimulationResult` so the runner can record the failure as a row in
`runs`.

## Turn helpers

```python
async def _add_collector_turn(self, result, profile, strategy) -> None:
    response = await self.collector.generate_turn(strategy, profile.account_data, result.transcript)
    result.total_input_tokens += response.input_tokens
    result.total_output_tokens += response.output_tokens
    result.estimated_cost_usd += response.estimated_cost_usd
    content, ended = strip_end_signal(response.content, self.end_signal)
    result.transcript.append(Message(role="collector", content=content))
    if ended:
        result.ended_by = EndedBy.COLLECTOR
```

`_add_debtor_turn` is symmetric. The engine never mutates the transcript
mid-turn; it only appends a `Message` after the response is parsed.

## End signals

```python
def strip_end_signal(content: str, signal: str = "[END_CONVERSATION]") -> tuple[str, bool]:
    ended = signal in content
    cleaned = content.replace(signal, "").strip()
    return cleaned, ended
```

The signal is stripped before storage so transcripts read cleanly. The
boolean is what tells the engine to flip `ended_by`. The function is
exported so the dashboard's manual session loop can apply the same
behavior to human-typed turns.

## Stalemate detection

```python
def stalemate_detected(transcript: list[Message], window: int = 3, threshold: float = 0.6) -> bool: ...
```

The detector takes the last `window` Collector / Debtor pairs, picks the
oldest pair as the baseline, and uses
`difflib.SequenceMatcher(None, baseline, candidate).ratio()` on each
later pair. If every later pair is either identical to the baseline or
above the similarity threshold on both sides, the conversation is
considered cycling. The defaults are tuned for the scripted backend
(`window=3, threshold=0.6`) and overridden in `config/simulation.yaml` to
`window=3, threshold=0.86` for live runs.

The detector returns `False` when fewer than `window` pairs exist, so
short conversations never trigger.

## On-progress callback

```python
async def _notify_progress(callback, result) -> None:
    if callback is None:
        return
    maybe_awaitable = callback(result)
    if isawaitable(maybe_awaitable):
        await maybe_awaitable
```

Sync or async, both fine. The dashboard uses an async callback to copy
the in-flight `SimulationResult` into the `WebRunJob` snapshot. The CLI
doesn't pass a callback, since it prints the final result with Rich
after the call returns.

## What the engine does *not* do

- **No retries.** A failed turn fails the simulation. Add a wrapper if
  you need retry semantics.
- **No model awareness.** The engine doesn't know if the underlying
  backend is local or live, free or paid. The runner picks models per
  cell.
- **No write to SQLite.** The engine is pure compute. The CLI and the
  runner are responsible for persistence.
- **No concurrency.** A single `run_simulation()` is sequential. Parallel
  runs are scheduled outside, by the runner.
