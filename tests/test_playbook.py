from __future__ import annotations

from collection_swarm.analysis.playbook import generate_playbook
from collection_swarm.analysis.statistics import compare_strategies
from collection_swarm.models import Judgment, Message, SimulationResult
from collection_swarm.store import SimulationStore


def test_generate_playbook_includes_objections(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")
    store.save_run(
        SimulationResult(
            id="sim_playbook",
            profile_id="cooperative_hardship",
            strategy_id="empathetic_payment_plan",
            conversation_model="local-scripted",
            judge_model="local-judge",
            ended_by="collector",
            turn_count=2,
            transcript=[
                Message(role="collector", content="Can we discuss options?"),
                Message(role="debtor", content="I cannot pay the full balance."),
            ],
            judgment=Judgment(
                reasoning="ok",
                payment_outcome="payment_plan",
                payment_probability=0.7,
                debtor_satisfaction=0.7,
                compliance_score=0.95,
                conversation_efficiency=2,
                rapport_built=0.6,
                escalation_risk=0.05,
            ),
        )
    )

    markdown = generate_playbook([compare_strategies("cooperative_hardship", store)], [], store)

    assert "Recommended Strategy" in markdown
    assert "inability_to_pay" in markdown
