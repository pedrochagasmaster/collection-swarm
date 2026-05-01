"""Judge evaluator and deterministic Constraint verification."""

from __future__ import annotations

import json
import re

from pydantic import ValidationError

from collection_swarm.backends.base import LLMResponse
from collection_swarm.backends.router import LLMRouter
from collection_swarm.models import JudgePromptConfig, Judgment, LLMMessage, Message, PaymentOutcome, Profile


class Judge:
    def __init__(self, router: LLMRouter, model_id: str, prompts: JudgePromptConfig) -> None:
        self.router = router
        self.model_id = model_id
        self.prompts = prompts
        self.last_response: LLMResponse | None = None

    async def evaluate(self, transcript: list[Message], profile: Profile) -> Judgment:
        response = await self.router.complete(
            self.model_id,
            [
                LLMMessage(role="system", content=_system_prompt(self.prompts)),
                LLMMessage(role="user", content=_transcript_prompt(self.prompts, transcript, profile)),
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
                        f"Debtor agreed to {amount:.0f}, exceeding max payment constraint of {rule.amount:.0f}."
                    )
                    break
        elif rule.type == "required_action" and rule.action:
            if rule.action == "demand_written_proof" and not _mentions_written_proof(lower_debtor_text):
                violations.append("Debtor never demanded written proof despite required_action constraint.")
            elif rule.action == "cite_liquidator_and_official_channel" and not _mentions_liquidator(
                "\n".join(turn.content for turn in transcript if turn.role == "collector").lower()
            ):
                violations.append(
                    "Collector never disclosed the liquidator or an official channel despite required_action constraint."
                )
    return violations


# Match agreement utterances expressed in Brazilian Portuguese ("posso pagar
# R$ 80", "topo R$ 100", "fechado em 150 reais") or in English ("I can do
# $200", "I will pay 50"). Currency symbol is optional so values written in
# Portuguese without "R$" are still detected.
_AGREEMENT_PATTERN = re.compile(
    r"\b(?:i can|i could|i will|i'll|i agree|agree to|can do|will pay|"
    r"posso pagar|consigo pagar|aceito pagar|topo|combinado em|fechado em|"
    r"vou pagar|pago)\b"
    r"[^.\n]{0,80}?"
    r"(?:r\$\s*|\$\s*)?"
    r"(\d[\d.,]*)"
    r"(?:\s*reais)?",
    re.IGNORECASE,
)


def _agreed_amounts(text: str) -> list[float]:
    amounts: list[float] = []
    for match in _AGREEMENT_PATTERN.finditer(text):
        raw = match.group(1)
        amounts.append(_parse_brazilian_or_us_number(raw))
    return amounts


def _parse_brazilian_or_us_number(raw: str) -> float:
    """Parse a number that may use either US (1,234.56) or BR (1.234,56) format."""

    cleaned = raw.strip().rstrip(".,")
    if "," in cleaned and "." in cleaned:
        # Whichever separator appears last is the decimal separator.
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Lone commas are decimal separators only when followed by exactly two
        # digits (typical Brazilian "80,00"); otherwise they are thousands.
        decimal_part = cleaned.rsplit(",", 1)[1]
        if len(decimal_part) == 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    return float(cleaned)


def _mentions_written_proof(text: str) -> bool:
    return any(
        phrase in text
        for phrase in [
            "written proof",
            "written validation",
            "validate",
            "validation notice",
            "fatura detalhada",
            "contrato",
            "comprovante",
            "documenta\u00e7\u00e3o",
            "prova documental",
            "por escrito",
        ]
    )


def _mentions_liquidator(text: str) -> bool:
    return any(
        phrase in text
        for phrase in [
            "liquidante",
            "liquida\u00e7\u00e3o",
            "efb regimes",
            "willbank.com.br",
            "bcb.gov.br",
            "banco central",
        ]
    )


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
            "pending_verification": PaymentOutcome.NO_COMMITMENT,
            "verification_pending": PaymentOutcome.NO_COMMITMENT,
            "in_progress": PaymentOutcome.NO_COMMITMENT,
            "ongoing": PaymentOutcome.NO_COMMITMENT,
            "no_resolution": PaymentOutcome.NO_COMMITMENT,
            "none": PaymentOutcome.NO_COMMITMENT,
            "no_payment": PaymentOutcome.NO_COMMITMENT,
            "refused": PaymentOutcome.REFUSAL,
            "hangup": PaymentOutcome.HANG_UP,
            "promised": PaymentOutcome.PROMISE_TO_PAY,
            "promised_callback": PaymentOutcome.PROMISE_TO_PAY,
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

    score_fields = (
        "payment_probability",
        "debtor_satisfaction",
        "compliance_score",
        "rapport_built",
        "escalation_risk",
    )
    scale = 100 if any(isinstance(data.get(field), (int, float)) and data[field] > 10 for field in score_fields) else 10
    for field in score_fields:
        value = data.get(field)
        if isinstance(value, (int, float)) and value > 1:
            data[field] = value / scale


def _system_prompt(prompts: JudgePromptConfig) -> str:
    return prompts.system.strip()


def _transcript_prompt(prompts: JudgePromptConfig, transcript: list[Message], profile: Profile) -> str:
    lines = "\n".join(f"{turn.role.title()}: {turn.content}" for turn in transcript)
    constraints = "\n".join(f"- {constraint.text}" for constraint in profile.constraints) or "- none"
    account = profile.account_data
    return prompts.transcript.format(account=account, constraints=constraints, transcript=lines).strip()
