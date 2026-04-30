"""Debtor participant."""

from __future__ import annotations

from collection_swarm.backends.base import LLMResponse
from collection_swarm.backends.router import LLMRouter
from collection_swarm.models import LLMMessage, Message, Profile


class DebtorAgent:
    def __init__(self, router: LLMRouter, model_id: str) -> None:
        self.router = router
        self.model_id = model_id

    async def generate_turn(self, profile: Profile, history: list[Message]) -> LLMResponse:
        messages = [_system_message(profile), *_history_messages(history)]
        return await self.router.complete(self.model_id, messages)


def _system_message(profile: Profile) -> LLMMessage:
    constraints = "\n".join(f"- {constraint.text}" for constraint in profile.constraints) or "- None"
    content = f"""You are the Debtor in a synthetic debt collection simulation.

Stay in character and respond as a realistic consumer, not as an assistant.
Profile tags:
- archetype: {profile.archetype}
- financial_situation: {profile.financial_situation}
- emotional_state: {profile.emotional_state}
- primary_objection: {profile.primary_objection}
- responsiveness: {profile.responsiveness}
- demographics: {profile.demographics}

Backstory:
{profile.backstory}

Hard constraints you must not violate:
{constraints}

Keep each reply to 1-3 concise sentences.
If the conversation reaches a natural stopping point, append [END_CONVERSATION].
"""
    return LLMMessage(role="system", content=content)


def _history_messages(history: list[Message]) -> list[LLMMessage]:
    messages: list[LLMMessage] = []
    for turn in history:
        role = "assistant" if turn.role == "debtor" else "user"
        messages.append(LLMMessage(role=role, content=f"{turn.role.title()}: {turn.content}"))
    return messages
