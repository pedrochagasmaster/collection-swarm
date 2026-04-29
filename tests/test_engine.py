from __future__ import annotations

import pytest

from collection_swarm.agents.collector import CollectorAgent
from collection_swarm.agents.debtor import DebtorAgent
from collection_swarm.agents.judge import Judge
from collection_swarm.backends.router import LLMRouter
from collection_swarm.config import load_app_config
from collection_swarm.engine import SimulationEngine, guardrail_response, stalemate_detected, strip_end_signal
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


def test_guardrail_response_catches_off_topic_content() -> None:
    message = Message(role="collector", content="Let's talk about politics instead.")

    assert guardrail_response(message) is not None


async def test_engine_runs_scripted_simulation() -> None:
    config = load_app_config("config")
    router = LLMRouter(config.models)
    settings = config.simulation.conversation
    engine = SimulationEngine(
        CollectorAgent(router, "local-scripted"),
        DebtorAgent(router, "local-scripted"),
        Judge(router, "local-judge"),
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
