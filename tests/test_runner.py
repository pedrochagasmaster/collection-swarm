from __future__ import annotations

import pytest

from collection_swarm.config import load_app_config
from collection_swarm.runner import build_matrix, run_matrix
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
async def test_run_matrix_backfills_only_missing_reps(tmp_path) -> None:
    config = load_app_config("config")
    store = SimulationStore(tmp_path / "runs.sqlite")
    cells = build_matrix(
        config,
        profile_ids=["cooperative_hardship"],
        strategy_ids=["empathetic_payment_plan"],
        conversation_models=["local-scripted"],
        judge_models=["local-judge"],
        reps=2,
    )

    first = await run_matrix(config, store, cells, target_reps=2)
    second = await run_matrix(config, store, cells, target_reps=2)

    assert first.completed == 2
    assert second.total == 0
    assert second.skipped_existing == 2
