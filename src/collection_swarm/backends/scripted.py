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
        if "documentation_first" in system or "liquidation" in system:
            tactic = "confirm the account in writing and explain the liquidation context clearly"
        elif "official_self_service" in system or "secure_official_channel" in system:
            tactic = "send a secure official self-service path without taking sensitive data here"
        elif "cash_flow_aligned" in system:
            tactic = "match any installment to your cash flow and essential expenses"
        elif "complaint_acknowledgment" in system or "pause_and_review" in system:
            tactic = "acknowledge the complaint and schedule a no-pressure review"
        elif "payment_plan" in system or "payment plan" in system:
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
        if any(term in history for term in ["liquidation", "cancelled", "official channel"]):
            return (
                "Liquidation does not automatically cancel a valid balance, but you should not have to rely on a call. "
                "I can send an official written account summary and payment-channel instructions for your review."
            )
        if any(term in history for term in ["scam", "cpf", "pix", "card details"]):
            return (
                "I will not ask for CPF, card, bank, or Pix details in this conversation. "
                "Please use only the official written channel after you verify the account summary."
            )
        if any(term in history for term in ["complaint", "banco central", "unfair", "betrayed"]):
            return "I hear the concern. I can document the complaint, pause pressure, and send the account details for review before any payment discussion."
        if any(term in history for term in ["can't", "hardship", "afford", "written proof", "verify"]):
            return (
                "I understand. We can send written validation and discuss options after you review it. "
                "If it helps, we can also look at a smaller first payment or a callback date."
            )
        return "What amount or date would feel realistic for you so we can keep the account moving forward?"

    def _debtor_response(self, system: str, history: str) -> str:
        if "liquidation_confusion" in system or "liquidation context" in system:
            if "liquidation does not automatically cancel" not in history:
                return "I heard Will Bank was liquidated, so I thought this card balance might be cancelled or frozen."
            return "If you send the official written summary and safe payment channel, I can review it before deciding. [END_CONVERSATION]"
        if "scam_concern" in system or "suspicious" in system:
            if "official written channel" not in history and "secure official" not in history:
                return "How do I know this is not a scam? I am not giving CPF, Pix, card, or bank details on this call."
            return "Send it through the official channel. If it matches my records, I can pay there. [END_CONVERSATION]"
        if "overindebtedness" in system or "80 per month" in system:
            return "I want to avoid more credit problems, but I can only manage about $80 per month after rent and groceries."
        if "bank_mistrust" in system or "complaint" in system or "indignant" in system:
            if "document the complaint" not in history:
                return "Will Bank failed customers first, and now you are calling me for money? I may file another complaint."
            return "Send the documentation and note my complaint. I am not agreeing today, but I will review it. [END_CONVERSATION]"
        if "dispute" in system or "written proof" in system:
            if "written validation" not in history and "written proof" not in history:
                return "Before I talk about payment, I need written proof that this debt is mine."
            return "Once I receive and review the proof, I can talk again, but I am not committing today. [END_CONVERSATION]"
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
