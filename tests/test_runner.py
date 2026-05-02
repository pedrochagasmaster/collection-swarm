from __future__ import annotations

import pytest

from collection_swarm.config import load_app_config
from collection_swarm.models import EvolutionConfig, HardeningConfig, TournamentConfig
from collection_swarm.runner import build_matrix, run_evolution_cycle, run_tournament
from collection_swarm.store import SimulationStore


def test_build_matrix_applies_filters_and_reps() -> None:
    config = load_app_config("config")

    cells = build_matrix(
        config,
        profile_ids=["cooperative_hardship"],
        strategy_ids=["empathetic_payment_plan"],
        conversation_models=["local-scripted"],
        judge_models=["local-judge"],
        reps=2,
    )

    assert len(cells) == 2
    assert cells[0].profile_id == "cooperative_hardship"
    assert cells[0].strategy_id == "empathetic_payment_plan"


@pytest.mark.asyncio
async def test_run_tournament_swiss_completes(tmp_path) -> None:
    config = load_app_config("config")
    store = SimulationStore(tmp_path / "runs.sqlite")

    result = await run_tournament(
        config,
        store,
        TournamentConfig(format="swiss", rounds=2),
        profile_ids=["cooperative_hardship", "hostile_avoidant"],
        strategy_ids=["empathetic_payment_plan", "neutral_reminder"],
        conversation_model="local-scripted",
        judge_model="local-judge",
        concurrency=2,
    )

    assert result.rounds_completed == 2
    assert result.total_games == 4
    assert len(store.list_runs()) == 4


@pytest.mark.asyncio
async def test_run_tournament_round_robin_updates_elo_ratings(tmp_path) -> None:
    config = load_app_config("config")
    store = SimulationStore(tmp_path / "runs.sqlite")

    result = await run_tournament(
        config,
        store,
        TournamentConfig(format="round_robin", rounds=1),
        profile_ids=["cooperative_hardship", "hostile_avoidant"],
        strategy_ids=["empathetic_payment_plan", "neutral_reminder"],
        conversation_model="local-scripted",
        judge_model="local-judge",
        concurrency=2,
    )

    ratings = store.get_elo_ratings()
    assert result.total_games == 4
    assert len(ratings) == 4
    assert any(rating.rating != 1500.0 for rating in ratings)
    assert store.get_tournament(result.id).total_games == 4


@pytest.mark.asyncio
async def test_run_evolution_cycle_saves_evolved_strategy(tmp_path) -> None:
    config = load_app_config("config")
    store = SimulationStore(tmp_path / "runs.sqlite")

    results = await run_evolution_cycle(
        config,
        store,
        EvolutionConfig(evolver_model_id="local-scripted", population_size=20, cull_bottom_n=0),
        TournamentConfig(format="swiss", rounds=1),
        generations=1,
        profile_ids=["cooperative_hardship"],
        strategy_ids=["empathetic_payment_plan"],
        concurrency=1,
    )

    assert len(results) == 1
    evolved = store.list_evolved_strategies()
    assert evolved
    assert evolved[0][0].id.startswith("evo_")


@pytest.mark.asyncio
async def test_run_evolution_cycle_can_harden_profiles(tmp_path) -> None:
    config = load_app_config("config")
    store = SimulationStore(tmp_path / "runs.sqlite")

    await run_evolution_cycle(
        config,
        store,
        EvolutionConfig(evolver_model_id="local-scripted", cull_bottom_n=0),
        TournamentConfig(format="swiss", rounds=1),
        generations=1,
        profile_ids=["cooperative_hardship"],
        strategy_ids=["empathetic_payment_plan"],
        hardening_config=HardeningConfig(enabled=True, hardener_model_id="local-scripted"),
        concurrency=1,
    )

    hardened = store.list_evolved_profiles()
    assert hardened
    assert hardened[0][0].id.startswith("hard_")


@pytest.mark.asyncio
async def test_run_evolution_cycle_feeds_hardened_profiles_into_next_generation(tmp_path) -> None:
    config = load_app_config("config")
    store = SimulationStore(tmp_path / "runs.sqlite")

    await run_evolution_cycle(
        config,
        store,
        EvolutionConfig(evolver_model_id="local-scripted", cull_bottom_n=0),
        TournamentConfig(format="swiss", rounds=1),
        generations=2,
        profile_ids=["cooperative_hardship"],
        strategy_ids=["empathetic_payment_plan"],
        hardening_config=HardeningConfig(enabled=True, hardener_model_id="local-scripted"),
        concurrency=1,
    )

    hardened_ids = {profile.id for profile, _ in store.list_evolved_profiles()}
    run_profile_ids = {run.profile_id for run in store.list_runs(status="completed")}
    assert hardened_ids & run_profile_ids


@pytest.mark.asyncio
async def test_run_evolution_cycle_culls_lowest_evolved_strategies(tmp_path) -> None:
    config = load_app_config("config")
    store = SimulationStore(tmp_path / "runs.sqlite")

    await run_evolution_cycle(
        config,
        store,
        EvolutionConfig(evolver_model_id="local-scripted", population_size=2, cull_bottom_n=1),
        TournamentConfig(format="swiss", rounds=1),
        generations=3,
        profile_ids=["cooperative_hardship"],
        strategy_ids=["empathetic_payment_plan"],
        concurrency=1,
    )

    active_evolved = store.list_evolved_strategies()
    all_evolved = store.list_evolved_strategies(include_culled=True)
    assert len(all_evolved) > len(active_evolved)
    assert len(active_evolved) <= 1
