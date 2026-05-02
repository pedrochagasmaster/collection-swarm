"""LLM-driven collector strategy evolution."""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import uuid4

import yaml

from collection_swarm.models import EvolutionConfig, LLMMessage, Strategy, StrategyLineage

logger = logging.getLogger(__name__)


def _parse_evolved_strategies(llm_output: str) -> list[dict[str, Any]]:
    text = _extract_yaml_block(llm_output)
    try:
        parsed = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return []
    if not isinstance(parsed, (dict, list)):
        return []
    items = parsed.get("strategies", parsed if isinstance(parsed, list) else [])
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


async def evolve_strategies(
    top_strategies: list[Strategy],
    bottom_strategies: list[Strategy],
    failure_transcripts: list[str],
    config: EvolutionConfig,
    router,
) -> list[Strategy]:
    if not config.evolver_model_id:
        raise ValueError("EvolutionConfig.evolver_model_id is required")
    response = await router.complete(
        config.evolver_model_id,
        [
            LLMMessage(
                role="user", content=_build_evolver_prompt(top_strategies, bottom_strategies, failure_transcripts)
            )
        ],
    )
    evolved: list[Strategy] = []
    for index, item in enumerate(_parse_evolved_strategies(response.content), start=1):
        item.setdefault("id", f"evo_1_mutate_{uuid4().hex[:6]}")
        if not str(item["id"]).startswith("evo_"):
            item["id"] = f"evo_1_mutate_{uuid4().hex[:6]}"
        try:
            evolved.append(Strategy.model_validate(item))
        except Exception:
            logger.warning("Skipping invalid evolved strategy entry %d: %s", index, item.get("id", "<no id>"))
            continue
    if evolved:
        return evolved
    return [_fallback_strategy(top_strategies, bottom_strategies)]


def cull_strategies(
    strategy_pool: list[Strategy],
    elo_ratings: dict[str, float],
    keep_n: int,
    lineages: dict[str, StrategyLineage] | None = None,
) -> list[Strategy]:
    lineages = lineages or {}
    seeds = [
        strategy for strategy in strategy_pool if strategy.id not in lineages or lineages[strategy.id].generation == 0
    ]
    evolved = [strategy for strategy in strategy_pool if strategy not in seeds]
    evolved.sort(key=lambda strategy: elo_ratings.get(strategy.id, 1500.0), reverse=True)
    kept: list[Strategy] = []
    for strategy in [*seeds, *evolved]:
        if strategy in seeds or len(kept) < keep_n:
            kept.append(strategy)
    return kept


def _build_evolver_prompt(top: list[Strategy], bottom: list[Strategy], transcripts: list[str]) -> str:
    return (
        "Generate improved debt collection strategies as YAML under a top-level 'strategies' key.\n"
        f"Top strategies:\n{yaml.safe_dump([s.model_dump(mode='json') for s in top], sort_keys=False)}\n"
        f"Bottom strategies:\n{yaml.safe_dump([s.model_dump(mode='json') for s in bottom], sort_keys=False)}\n"
        f"Failure excerpts:\n{yaml.safe_dump(transcripts[:5], sort_keys=False)}"
    )


def _fallback_strategy(top: list[Strategy], bottom: list[Strategy]) -> Strategy:
    if not top and not bottom:
        raise ValueError("Cannot create fallback strategy without at least one parent")
    parent = top[0] if top else bottom[0]
    return parent.model_copy(
        update={
            "id": f"evo_1_mutate_{uuid4().hex[:6]}",
            "rationale": "Fallback deterministic mutation generated when the evolver did not return YAML.",
        }
    )


def _extract_yaml_block(text: str) -> str:
    match = re.search(r"```(?:yaml|yml)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    return match.group(1) if match else text
