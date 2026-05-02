from __future__ import annotations

import pytest

from collection_swarm.config import load_app_config
from collection_swarm.evolution import _parse_evolved_strategies, cull_strategies, evolve_strategies
from collection_swarm.models import EvolutionConfig, LLMMessage, Strategy, StrategyLineage
from collection_swarm.store import SimulationStore


class _Router:
    async def complete(self, model_id: str, messages: list[LLMMessage]):
        class Response:
            content = """
strategies:
  - id: evo_candidate
    tone: empathetic
    opening_approach: soft_intro
    negotiation_tactic: payment_plan
    escalation_style: none
    concession_willingness: flexible
    compliance_adherence: strict
    follow_up_strategy: written_agreement
"""
            input_tokens = 10
            output_tokens = 30
            estimated_cost_usd = 0.0

        return Response()


def test_parse_evolved_strategies_valid_yaml() -> None:
    parsed = _parse_evolved_strategies(
        """
```yaml
strategies:
  - id: evo_test
    tone: neutral
    opening_approach: reminder
    negotiation_tactic: payment_reminder
    escalation_style: none
    concession_willingness: low
    compliance_adherence: strict
    follow_up_strategy: written_agreement
```
"""
    )

    assert parsed[0]["id"] == "evo_test"


def test_parse_evolved_strategies_rejects_garbage() -> None:
    assert _parse_evolved_strategies("not: [valid") == []


@pytest.mark.asyncio
async def test_evolve_strategies_produces_valid_output() -> None:
    config = load_app_config("config")
    top = [next(iter(config.strategies.values()))]
    bottom = [list(config.strategies.values())[1]]

    evolved = await evolve_strategies(top, bottom, [], EvolutionConfig(evolver_model_id="local-scripted"), _Router())

    assert len(evolved) == 1
    assert evolved[0].id == "evo_candidate"


def test_cull_strategies_preserves_seed_and_removes_lowest_evolved() -> None:
    seed = Strategy(
        id="seed",
        tone="neutral",
        opening_approach="reminder",
        negotiation_tactic="payment_reminder",
        escalation_style="none",
        concession_willingness="low",
        compliance_adherence="strict",
        follow_up_strategy="written_agreement",
    )
    evolved = seed.model_copy(update={"id": "evo_low"})

    kept = cull_strategies(
        [seed, evolved],
        {"seed": 1200, "evo_low": 1100},
        keep_n=1,
        lineages={"evo_low": StrategyLineage(strategy_id="evo_low", generation=1)},
    )

    assert [strategy.id for strategy in kept] == ["seed"]


def test_store_evolved_strategy_round_trip(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")
    strategy = Strategy(
        id="evo_saved",
        tone="neutral",
        opening_approach="reminder",
        negotiation_tactic="payment_reminder",
        escalation_style="none",
        concession_willingness="low",
        compliance_adherence="strict",
        follow_up_strategy="written_agreement",
    )
    lineage = StrategyLineage(
        strategy_id="evo_saved",
        parent_ids=["empathetic_payment_plan"],
        generation=1,
        mutation_type="mutate",
        mutation_description="small tone variation",
    )

    store.save_evolved_strategy(strategy, lineage)

    loaded = store.get_evolved_strategy("evo_saved")
    assert loaded is not None
    assert loaded.id == "evo_saved"
    assert store.list_evolved_strategies()[0][1].generation == 1
