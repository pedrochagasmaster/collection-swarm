---
title: Strategy Evolution
layout: default
nav_order: 12
---

# Strategy Evolution
{: .no_toc }

LLM-driven genetic evolution of collection strategies.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Source:** `src/collection_swarm/evolution.py`

## Overview

The evolution module uses LLMs to generate new collection strategies inspired by tournament results. Top-performing strategies serve as "parents"; underperforming strategies and their failure transcripts provide negative examples. The LLM generates improved variants that are added to the strategy pool.

## Evolution Cycle

The full evolution lifecycle (orchestrated by `runner.run_evolution_cycle()`):

```
┌──────────────────────────────────────┐
│     For each generation:             │
│                                      │
│  1. Run tournament with current pool │
│  2. Sort strategies by Elo rating    │
│  3. Select top-k and bottom-k        │
│  4. Collect failure transcripts      │
│  5. Call LLM to evolve strategies    │
│  6. Add evolved strategies to pool   │
│  7. Cull underperformers             │
│  8. (Optional) Harden profiles       │
│                                      │
└──────────────────────────────────────┘
```

## Core Functions

### evolve_strategies

```python
async def evolve_strategies(
    top_strategies: list[Strategy],
    bottom_strategies: list[Strategy],
    failure_transcripts: list[str],
    config: EvolutionConfig,
    router,
) -> list[Strategy]
```

1. Builds an evolver prompt containing:
   - YAML dump of top-performing strategies
   - YAML dump of bottom-performing strategies
   - Up to 5 failure transcript excerpts
2. Calls the LLM via the router.
3. Parses the response for YAML-formatted strategies under a `strategies` key.
4. Validates each parsed strategy against the `Strategy` model.
5. Auto-generates IDs with the `evo_` prefix if missing.
6. If parsing produces no valid strategies, returns a **fallback mutation** (copy of the best parent with a new ID).

### Evolver Prompt

The prompt instructs the LLM to:

```
Generate improved debt collection strategies as YAML under a top-level 'strategies' key.
Top strategies: [YAML dump]
Bottom strategies: [YAML dump]
Failure excerpts: [YAML dump of transcript strings]
```

### YAML Extraction

The `_extract_yaml_block()` function handles LLM responses that wrap YAML in markdown code fences:

```python
def _extract_yaml_block(text: str) -> str:
    match = re.search(r"```(?:yaml|yml)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else text
```

### cull_strategies

```python
def cull_strategies(
    strategy_pool: list[Strategy],
    elo_ratings: dict[str, float],
    keep_n: int,
    lineages: dict[str, StrategyLineage] | None = None,
) -> list[Strategy]
```

Culling rules:
1. **Seed strategies** (generation 0 or not in lineage) are always kept.
2. **Evolved strategies** are sorted by Elo rating (highest first).
3. The top `keep_n` evolved strategies are kept.
4. Strategies not in the kept set are marked as culled in the store.

### Fallback Strategy

If the LLM fails to produce valid YAML:

```python
def _fallback_strategy(top: list[Strategy], bottom: list[Strategy]) -> Strategy:
    parent = top[0] if top else bottom[0]
    return parent.model_copy(
        update={
            "id": f"evo_1_mutate_{uuid4().hex[:6]}",
            "rationale": "Fallback deterministic mutation generated when the evolver did not return YAML.",
        }
    )
```

This ensures evolution always produces at least one new strategy per cycle.

## EvolutionConfig Parameters

| Parameter | Default | Description |
|:----------|:--------|:------------|
| `population_size` | 20 | Maximum active strategies |
| `top_k` | 3 | Best strategies used as parents |
| `bottom_k` | 3 | Worst strategies used as negative examples |
| `cull_bottom_n` | 3 | Number of underperformers to remove per generation |
| `mutation_rate` | 0.5 | Not directly used by LLM (reserved for future use) |
| `crossover_rate` | 0.3 | Not directly used by LLM (reserved for future use) |
| `evolver_model_id` | None | Model to use for strategy generation |

## Strategy Lineage

Every evolved strategy is tracked with a `StrategyLineage` record:

```python
lineage = StrategyLineage(
    strategy_id=strategy.id,
    parent_ids=[s.id for s in top[:2]],
    generation=generation,
    mutation_type="llm",
    mutation_description="Generated from tournament leaderboard feedback.",
)
```

This enables tracing any strategy's evolutionary history back to its seed ancestors.
