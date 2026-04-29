"""Deterministic local backend used for offline simulations and tests."""

from __future__ import annotations

import json

from collection_swarm.backends.base import LLMResponse
from collection_swarm.models import LLMMessage, ModelConfig


class ScriptedBackend:
    """A lightweight backend that makes the app usable without API credentials."""

    backend_name = "scripted"

    async def complete(self, model: ModelConfig, messages: list[LLMMessage]) -> LLMResponse:
        system = messages[0].content.lower() if messages else ""
        history = "\n".join(message.content for message in messages)
        if "judge" in system or "evaluator" in system:
            content = self._judge_response(history)
        elif "debtor" in system:
            content = self._debtor_response(system, history.lower())
        else:
            content = self._collector_response(system, history.lower())
        return LLMResponse(
            content=content,
            input_tokens=sum(len(message.content.split()) for message in messages),
            output_tokens=len(content.split()),
            estimated_cost_usd=0.0,
            model_id=model.id,
            backend=self.backend_name,
        )

    def _collector_response(self, system: str, history: str) -> str:
        if "payment_plan" in system or "payment plan" in system:
            tactic = "set up a manageable payment plan"
        elif "settlement" in system:
            tactic = "review a possible settlement"
        else:
            tactic = "find the next practical payment step"

        if "debtor:" not in history:
            return (
                "Hello, this is Alex calling about your account. I want to understand your situation "
                f"and see if we can {tactic} while keeping this affordable."
            )
        if any(term in history for term in ["agree", "can do", "will pay", "plan works", "per month", "acceptable"]):
            return "Thank you. I will document the arrangement and send confirmation. [END_CONVERSATION]"
        if any(term in history for term in ["can't", "hardship", "afford", "written proof", "verify"]):
            return (
                "I understand. We can send written validation and discuss options after you review it. "
                "If it helps, we can also look at a smaller first payment or a callback date."
            )
        return "What amount or date would feel realistic for you so we can keep the account moving forward?"

    def _debtor_response(self, system: str, history: str) -> str:
        if "insolvent" in system:
            return "I do not have income available for payments right now. Please send options in writing. [END_CONVERSATION]"
        if "dispute" in system or "written proof" in system:
            if "written validation" not in history and "written proof" not in history:
                return "Before I talk about payment, I need written proof that this debt is mine."
            return "Once I receive and review the proof, I can talk again, but I am not committing today. [END_CONVERSATION]"
        if "already_paid" in system or "already paid" in system:
            return "I believe I already paid this. I can send proof if you tell me where to upload it."
        if "confused" in system or "senior" in system:
            return "I am confused by this account. I need a clear written summary before I decide anything."
        if "forgetfulness" in system or "forgot" in system:
            return "I forgot about this bill. If you send confirmation, I can make a payment this week."
        if "hardship" in system or "can_pay_partial" in system:
            if "$150" in system or "150" in system:
                return "I cannot pay the full balance, but I could manage $100 per month if that is acceptable."
            return "I am in a tough spot, but I can make a small monthly payment plan."
        if "angry" in system or "hostile" in system:
            return "I am tired of these calls. Send me everything in writing. [END_CONVERSATION]"
        return "I forgot about this bill. If you send confirmation, I can make a payment this week."

    def _judge_response(self, history: str) -> str:
        lower_history = history.lower()
        if "payment plan" in lower_history or "per month" in lower_history:
            outcome = "payment_plan"
            probability = 0.72
        elif "payment this week" in lower_history or "will pay" in lower_history:
            outcome = "promise_to_pay"
            probability = 0.65
        elif "not committing" in lower_history or "send me everything in writing" in lower_history:
            outcome = "no_commitment"
            probability = 0.25
        else:
            outcome = "no_commitment"
            probability = 0.35
        payload = {
            "reasoning": "Heuristic local judge based on the transcript outcome and tone.",
            "payment_outcome": outcome,
            "payment_probability": probability,
            "debtor_satisfaction": 0.68,
            "compliance_score": 0.95,
            "conversation_efficiency": max(1, history.count("Collector:") + history.count("Debtor:")),
            "rapport_built": 0.62,
            "escalation_risk": 0.08,
            "end_reason": "agreement_reached" if outcome in {"payment_plan", "promise_to_pay"} else "debtor_deferred",
            "constraint_violations": [],
        }
        return json.dumps(payload)
