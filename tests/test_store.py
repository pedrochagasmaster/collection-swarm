from __future__ import annotations

from collection_swarm.models import EndedBy, Judgment, Message, PaymentOutcome, SimulationResult
from collection_swarm.store import SimulationStore


def _result() -> SimulationResult:
    return SimulationResult(
        id="sim_test",
        profile_id="cooperative_hardship",
        strategy_id="empathetic_payment_plan",
        conversation_model="local-scripted",
        judge_model="local-scripted",
        turn_count=2,
        ended_by=EndedBy.DEBTOR,
        transcript=[
            Message(role="collector", content="Can we set up a plan?"),
            Message(role="debtor", content="I can pay $100 per month."),
        ],
        judgment=Judgment(
            reasoning="Good plan.",
            payment_outcome=PaymentOutcome.PAYMENT_PLAN,
            payment_probability=0.8,
            debtor_satisfaction=0.7,
            compliance_score=0.95,
            conversation_efficiency=2,
            rapport_built=0.6,
            escalation_risk=0.05,
        ),
    )


def test_store_saves_and_reads_simulation(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")
    store.save_run(_result())

    loaded = store.get_run("sim_test")

    assert loaded.profile_id == "cooperative_hardship"
    assert loaded.judgment is not None
    assert loaded.judgment.payment_probability == 0.8
    assert store.count_by_status() == {"completed": 1}


def test_strategy_comparison_and_best_transcript(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")
    store.save_run(_result())

    stats = store.get_strategy_comparison("cooperative_hardship")

    assert stats[0].strategy_id == "empathetic_payment_plan"
    assert store.get_best_transcript("cooperative_hardship", "empathetic_payment_plan")[1].role == "debtor"
