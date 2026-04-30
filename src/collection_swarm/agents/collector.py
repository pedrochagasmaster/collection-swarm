"""Collector participant."""

from __future__ import annotations

from collection_swarm.backends.base import LLMResponse
from collection_swarm.backends.router import LLMRouter
from collection_swarm.models import AccountData, CollectorPromptConfig, LLMMessage, Message, Strategy


class CollectorAgent:
    def __init__(self, router: LLMRouter, model_id: str, prompts: CollectorPromptConfig) -> None:
        self.router = router
        self.model_id = model_id
        self.prompts = prompts

    async def generate_turn(self, strategy: Strategy, account: AccountData, history: list[Message]) -> LLMResponse:
        messages = [
            LLMMessage(role="system", content=_system_prompt(self.prompts, strategy, account)),
            LLMMessage(role="user", content=_history_prompt(self.prompts, history)),
        ]
        return await self.router.complete(self.model_id, messages)


def _system_prompt(prompts: CollectorPromptConfig, strategy: Strategy, account: AccountData) -> str:
    return prompts.system.format(strategy=strategy, account=account).strip()


def _history_prompt(prompts: CollectorPromptConfig, history: list[Message]) -> str:
    if not history:
        return prompts.history_empty.strip()
    transcript = "\n".join(f"{message.role.title()}: {message.content}" for message in history)
    return prompts.history.format(transcript=transcript).strip()
