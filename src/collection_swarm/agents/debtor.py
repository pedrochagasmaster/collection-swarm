"""Debtor participant."""

from __future__ import annotations

from collection_swarm.backends.base import LLMResponse
from collection_swarm.backends.router import LLMRouter
from collection_swarm.models import DebtorPromptConfig, LLMMessage, Message, Profile


class DebtorAgent:
    def __init__(self, router: LLMRouter, model_id: str, prompts: DebtorPromptConfig) -> None:
        self.router = router
        self.model_id = model_id
        self.prompts = prompts

    async def generate_turn(self, profile: Profile, history: list[Message]) -> LLMResponse:
        messages = [_system_message(self.prompts, profile), *_history_messages(self.prompts, history)]
        return await self.router.complete(self.model_id, messages)


def _system_message(prompts: DebtorPromptConfig, profile: Profile) -> LLMMessage:
    constraints = "\n".join(f"- {constraint.text}" for constraint in profile.constraints) or prompts.constraints_empty
    content = prompts.system.format(profile=profile, constraints=constraints).strip()
    return LLMMessage(role="system", content=content)


def _history_messages(prompts: DebtorPromptConfig, history: list[Message]) -> list[LLMMessage]:
    messages: list[LLMMessage] = []
    for turn in history:
        role = "assistant" if turn.role == "debtor" else "user"
        content = prompts.history_message.format(role=turn.role.title(), content=turn.content)
        messages.append(LLMMessage(role=role, content=content))
    return messages
