from __future__ import annotations

import pytest

from collection_swarm.config import load_app_config
from collection_swarm.models import TournamentConfig
from collection_swarm.runner import build_matrix, run_tournament
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
