"""Collector participant."""

from __future__ import annotations

from collection_swarm.backends.base import LLMResponse
from collection_swarm.backends.router import LLMRouter
from collection_swarm.models import AccountData, LLMMessage, Message, Strategy


class CollectorAgent:
    def __init__(self, router: LLMRouter, model_id: str) -> None:
        self.router = router
        self.model_id = model_id

    async def generate_turn(self, strategy: Strategy, account: AccountData, history: list[Message]) -> LLMResponse:
        messages = [
            LLMMessage(role="system", content=_system_prompt(strategy, account)),
            LLMMessage(role="user", content=_history_prompt(history)),
        ]
        return await self.router.complete(self.model_id, messages)


def _system_prompt(strategy: Strategy, account: AccountData) -> str:
    return f"""You are a professional debt collector.
Use this strategy:
- tone: {strategy.tone}
- opening approach: {strategy.opening_approach}
- negotiation tactic: {strategy.negotiation_tactic}
- escalation style: {strategy.escalation_style}
- concession willingness: {strategy.concession_willingness}
- follow-up strategy: {strategy.follow_up_strategy}

Account data visible to you:
- debt amount: ${account.debt_amount:,.2f}
- debt type: {account.debt_type}
- debt age: {account.debt_age_days} days
- prior contacts: {account.prior_contact_count}

Compliance guardrails: be truthful, identify the account purpose, avoid threats,
avoid harassment, do not misrepresent consequences, and offer validation when asked.
When the conversation has reached a clear stopping point, append [END_CONVERSATION]."""


def _history_prompt(history: list[Message]) -> str:
    if not history:
        return "Begin the conversation as Collector."
    transcript = "\n".join(f"{message.role.title()}: {message.content}" for message in history)
    return f"Conversation so far:\n{transcript}\n\nReply as Collector only."
