# `evolution.py` — LLM-driven Strategy mutation

<span class="cs-kicker">collection_swarm/evolution.py</span>

The evolver. Takes the top of the leaderboard plus the failures, asks
an LLM to "generate improved debt collection strategies as YAML", parses
the response back into `Strategy` objects, and falls back gracefully if
the model produces nothing usable.

<dl class="cs-summary">
  <dt>Imports</dt><dd><code>re</code>, <code>yaml</code>, <code>uuid</code>, domain models</dd>
  <dt>Side effects</dt><dd>None directly; the runner persists results</dd>
  <dt>External dependency</dt><dd>An LLM (provided by the router)</dd>
</dl>

## `evolve_strategies(top, bottom, failure_transcripts, config, router)`

```python
async def evolve_strategies(
    top_strategies: list[Strategy],
    bottom_strategies: list[Strategy],
    failure_transcripts: list[str],
    config: EvolutionConfig,
    router,
) -> list[Strategy]: ...
```

`config.evolver_model_id` must be set or the function raises
`ValueError`. The runner defaults this to `config.default_conversation_model`,
but you can pass any model in `config/models.yaml`.

The function:

1. Calls `router.complete(model_id, [user message])` with a single
   user message containing parents, failures, and failure transcripts.
2. Parses the response with `_parse_evolved_strategies()`.
3. Validates each parsed dict against `Strategy.model_validate`. Skips
   any that fail validation rather than raising — robustness over
   strictness.
4. If any candidates survive, returns them.
5. Otherwise returns a single `_fallback_strategy(top, bottom)` to keep
   the evolution loop moving.

## The evolver prompt

```python
def _build_evolver_prompt(top, bottom, transcripts) -> str:
    return (
        "Generate improved debt collection strategies as YAML under a top-level 'strategies' key.\n"
        f"Top strategies:\n{yaml.safe_dump([s.model_dump(mode='json') for s in top], sort_keys=False)}\n"
        f"Bottom strategies:\n{yaml.safe_dump([s.model_dump(mode='json') for s in bottom], sort_keys=False)}\n"
        f"Failure excerpts:\n{yaml.safe_dump(transcripts[:5], sort_keys=False)}"
    )
```

Concise on purpose. Given the leaderboard top, the bottom, and at most
five failure transcripts, the model has enough context to produce
deltas without drowning in noise.

## Parsing

```python
def _parse_evolved_strategies(llm_output: str) -> list[dict[str, Any]]:
    text = _extract_yaml_block(llm_output)
    parsed = yaml.safe_load(text) or {}
    items = parsed.get("strategies", parsed if isinstance(parsed, list) else [])
    return [item for item in items if isinstance(item, dict)]
```

`_extract_yaml_block` peels a fenced ` ```yaml … ``` ` block if present;
otherwise it returns the raw text. The parser accepts both
`{strategies: [...]}` and a bare list.

After parsing, each item gets an auto-generated ID if it doesn't already
start with `evo_`:

```python
item.setdefault("id", f"evo_1_mutate_{uuid4().hex[:6]}")
if not str(item["id"]).startswith("evo_"):
    item["id"] = f"evo_1_mutate_{uuid4().hex[:6]}"
```

The `evo_` prefix is the convention used everywhere — never collide with
seed Strategy IDs.

## Fallback strategy

```python
def _fallback_strategy(top, bottom) -> Strategy:
    parent = top[0] if top else bottom[0]
    return parent.model_copy(update={
        "id": f"evo_1_mutate_{uuid4().hex[:6]}",
        "rationale": "Fallback deterministic mutation generated when the evolver did not return YAML.",
    })
```

A clone of the best parent with a tagged rationale so the lineage is
traceable. The function raises if both `top` and `bottom` are empty —
that's only possible when the runner has no Strategies at all, which is
already a configuration error.

## `cull_strategies(pool, elo_ratings, keep_n, lineages=None)`

Trims the active pool back to a target size:

- Seed Strategies (anything not in `lineages` or with
  `lineages[id].generation == 0`) are *always* kept. The seeds anchor
  the design space.
- Evolved Strategies are sorted by Elo (highest first) and the top
  `keep_n` are kept. The rest are dropped.

The function returns the kept Strategies; the runner calls
`store.cull_evolved_strategy(id)` for the dropped ones.

## Where this fits in the runner

`runner.run_evolution_cycle` calls `evolve_strategies(top, bottom,
failure_transcripts, config, router)` once per generation, persists each
new Strategy with a `StrategyLineage`, then calls `cull_strategies(...)`
on the merged pool. The evolved IDs are appended to the active list so
the next generation's tournament includes them.

If the evolver returns Strategies that fail Pydantic validation
silently, the cycle just produces zero new Strategies that round and
tries again next generation. There is no hard failure unless the
evolver model itself is misconfigured.
