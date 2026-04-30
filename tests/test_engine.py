from __future__ import annotations

import pytest

from collection_swarm.agents.collector import CollectorAgent
from collection_swarm.agents.debtor import DebtorAgent
from collection_swarm.agents.judge import Judge
from collection_swarm.backends.router import LLMRouter
from collection_swarm.config import load_app_config
from collection_swarm.engine import SimulationEngine, stalemate_detected, strip_end_signal
from collection_swarm.models import EndedBy, Message


def test_strip_end_signal_removes_marker() -> None:
    content, ended = strip_end_signal("Thanks [END_CONVERSATION]")

    assert content == "Thanks"
    assert ended is True


def test_stalemate_detected_for_repeated_pairs() -> None:
    transcript = [
        Message(role="collector", content="Can you pay?"),
        Message(role="debtor", content="No."),
        Message(role="collector", content="Can you pay?"),
        Message(role="debtor", content="No."),
        Message(role="collector", content="Can you pay?"),
        Message(role="debtor", content="No."),
        Message(role="collector", content="Can you pay?"),
        Message(role="debtor", content="No."),
    ]

    assert stalemate_detected(transcript, window=3, threshold=0.9)


async def test_engine_runs_scripted_simulation() -> None:
    config = load_app_config("config")
    router = LLMRouter(config.models, cursor_sdk_prompts=config.prompts.cursor_sdk)
    settings = config.simulation.conversation
    engine = SimulationEngine(
        CollectorAgent(router, "local-scripted", config.prompts.collector),
        DebtorAgent(router, "local-scripted", config.prompts.debtor),
        Judge(router, "local-judge", config.prompts.judge),
        max_turns=settings.max_turns,
    )

    result = await engine.run_simulation(
        config.profile("cooperative_hardship"),
        config.strategy("empathetic_payment_plan"),
    )

    assert result.status == "completed"
    assert result.ended_by in {EndedBy.COLLECTOR, EndedBy.DEBTOR, EndedBy.TURN_LIMIT, EndedBy.STALEMATE}
    assert result.transcript
    assert result.judgment is not None
