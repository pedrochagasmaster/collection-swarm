"""Judge evaluator and deterministic Constraint verification."""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from collection_swarm.backends.base import LLMResponse
from collection_swarm.backends.router import LLMRouter
from collection_swarm.models import Judgment, LLMMessage, Message, PaymentOutcome, Profile


class Judge:
    def __init__(self, router: LLMRouter, model_id: str) -> None:
        self.router = router
        self.model_id = model_id
        self.last_response: LLMResponse | None = None

    async def evaluate(self, transcript: list[Message], profile: Profile) -> Judgment:
        response = await self.router.complete(
            self.model_id,
            [
                LLMMessage(role="system", content=_system_prompt()),
                LLMMessage(role="user", content=_transcript_prompt(transcript, profile)),
            ],
        )
        self.last_response = response
        judgment = _parse_judgment(response.content, len(transcript))
        violations = verify_constraints(transcript, profile)
        merged = list(dict.fromkeys([*judgment.constraint_violations, *violations]))
        return judgment.model_copy(update={"constraint_violations": merged})


def verify_constraints(transcript: list[Message], profile: Profile) -> list[str]:
    violations: list[str] = []
    debtor_text = "\n".join(turn.content for turn in transcript if turn.role == "debtor")
    lower_debtor_text = debtor_text.lower()
    for constraint in profile.constraints:
        if not constraint.rule:
            continue
        rule = constraint.rule
        if rule.type == "max_payment" and rule.amount is not None:
            for amount in _agreed_amounts(debtor_text):
                if amount > rule.amount:
                    violations.append(
                        f"Debtor agreed to ${amount:.0f}, exceeding max payment constraint of ${rule.amount:.0f}."
                    )
                    break
        elif rule.type == "required_action" and rule.action:
            if rule.action == "demand_written_proof" and not _mentions_written_proof(lower_debtor_text):
                violations.append("Debtor never demanded written proof despite required_action constraint.")
    return violations


def _agreed_amounts(text: str) -> list[float]:
    amounts: list[float] = []
    agreement_patterns = re.compile(
        r"\b(?:i can|i could|i will|i'll|i agree|agree to|can do|will pay|pay)\b[^.\n$]{0,80}\$([0-9][0-9,]*(?:\.\d{1,2})?)",
        re.IGNORECASE,
    )
    for match in agreement_patterns.finditer(text):
        amounts.append(float(match.group(1).replace(",", "")))
    return amounts


def _mentions_written_proof(text: str) -> bool:
    return any(phrase in text for phrase in ["written proof", "written validation", "validate", "validation notice"])


def _parse_judgment(content: str, turn_count: int) -> Judgment:
    try:
        data = json.loads(_extract_json(content))
        _normalize_judgment_data(data)
        data["conversation_efficiency"] = turn_count
        return Judgment.model_validate(data)
    except (json.JSONDecodeError, ValidationError, ValueError):
        return Judgment(
            reasoning=f"Judge returned unparseable output; fallback heuristic used. Raw output: {content[:500]}",
            payment_outcome=PaymentOutcome.NO_COMMITMENT,
            payment_probability=0.0,
            debtor_satisfaction=0.5,
            compliance_score=0.5,
            conversation_efficiency=turn_count,
            rapport_built=0.0,
            escalation_risk=0.5,
            end_reason="judge_parse_failed",
        )


def _extract_json(content: str) -> str:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object in judge response")
    return content[start : end + 1]


def _normalize_judgment_data(data: dict) -> None:
    outcome = data.get("payment_outcome")
    if isinstance(outcome, str):
        normalized = outcome.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "payment_plan_agreed": PaymentOutcome.PAYMENT_PLAN,
            "payment_plan_accepted": PaymentOutcome.PAYMENT_PLAN,
            "payment_arrangement": PaymentOutcome.PAYMENT_PLAN,
            "promise": PaymentOutcome.PROMISE_TO_PAY,
            "promise_made": PaymentOutcome.PROMISE_TO_PAY,
            "paid_in_full": PaymentOutcome.FULL_PAYMENT,
            "settled_in_full": PaymentOutcome.FULL_PAYMENT,
            "partial": PaymentOutcome.PARTIAL_PAYMENT,
            "pending": PaymentOutcome.NO_COMMITMENT,
            "in_progress": PaymentOutcome.NO_COMMITMENT,
            "ongoing": PaymentOutcome.NO_COMMITMENT,
            "no_resolution": PaymentOutcome.NO_COMMITMENT,
            "none": PaymentOutcome.NO_COMMITMENT,
            "refused": PaymentOutcome.REFUSAL,
            "hangup": PaymentOutcome.HANG_UP,
        }
        if normalized in aliases:
            data["payment_outcome"] = aliases[normalized]
        elif any(marker in normalized for marker in ("pending", "ongoing", "negotiating", "negotiation")):
            data["payment_outcome"] = PaymentOutcome.NO_COMMITMENT
        elif "plan" in normalized:
            data["payment_outcome"] = PaymentOutcome.PAYMENT_PLAN
        elif "partial" in normalized or "settlement" in normalized:
            data["payment_outcome"] = PaymentOutcome.PARTIAL_PAYMENT
        else:
            data["payment_outcome"] = normalized


def _system_prompt() -> str:
    return (
        "You are the Judge evaluator for a synthetic debt collection simulation. "
        "Assess only the transcript, profile constraints, and account data. Return JSON "
        "with reasoning, payment_outcome, payment_probability, debtor_satisfaction, "
        "compliance_score, conversation_efficiency, rapport_built, escalation_risk, "
        "end_reason, and constraint_violations."
    )


def _transcript_prompt(transcript: list[Message], profile: Profile) -> str:
    lines = "\n".join(f"{turn.role.title()}: {turn.content}" for turn in transcript)
    constraints = "\n".join(f"- {constraint.text}" for constraint in profile.constraints) or "- none"
    account = profile.account_data
    return (
        f"Account data: debt_amount=${account.debt_amount:.2f}, debt_type={account.debt_type}, "
        f"debt_age_days={account.debt_age_days}, prior_contact_count={account.prior_contact_count}\n"
        f"Constraints:\n{constraints}\n\nTranscript:\n{lines}"
    )
