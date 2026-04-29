from __future__ import annotations

from collection_swarm.config import load_app_config
from collection_swarm.runner import build_matrix


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
