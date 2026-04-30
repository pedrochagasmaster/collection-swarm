from __future__ import annotations

from collection_swarm.agents.judge import _parse_judgment, verify_constraints
from collection_swarm.models import Constraint, ConstraintRule, Message, PaymentOutcome, Profile


def test_verify_constraints_flags_payment_above_profile_max() -> None:
    profile = Profile(
        id="p",
        archetype="cooperative",
        financial_situation="hardship",
        debt_amount=1000,
        debt_age_days=90,
        debt_type="medical",
        prior_contact_count=1,
        emotional_state="anxious",
        primary_objection="inability_to_pay",
        responsiveness="high",
        demographics="family_provider",
        backstory="Synthetic profile.",
        constraints=[
            Constraint(
                text="Will never agree above $150/month.",
                rule=ConstraintRule(type="max_payment", amount=150, frequency="monthly"),
            )
        ],
    )

    violations = verify_constraints([Message(role="debtor", content="I can do $200 per month.")], profile)

    assert violations


def test_verify_constraints_accepts_required_written_proof() -> None:
    profile = Profile(
        id="p",
        archetype="disputer",
        financial_situation="can_pay_partial",
        debt_amount=500,
        debt_age_days=45,
        debt_type="utility",
        prior_contact_count=0,
        emotional_state="calm",
        primary_objection="wants_written_proof",
        responsiveness="medium",
        demographics="young_professional",
        backstory="Synthetic profile.",
        constraints=[
            Constraint(
                text="Will always demand written proof first.",
                rule=ConstraintRule(type="required_action", action="demand_written_proof"),
            )
        ],
    )

    violations = verify_constraints([Message(role="debtor", content="Send written proof first.")], profile)

    assert violations == []


def test_parse_judgment_accepts_fenced_json_and_common_outcome_alias() -> None:
    judgment = _parse_judgment(
        """```json
{
  "reasoning": "Agreement reached.",
  "payment_outcome": "payment_plan_agreed",
  "payment_probability": 0.95,
  "debtor_satisfaction": 0.95,
  "compliance_score": 1.0,
  "conversation_efficiency": 2,
  "rapport_built": 0.8,
  "escalation_risk": 0.05,
  "end_reason": "agreement_reached",
  "constraint_violations": []
}
```""",
        turn_count=2,
    )

    assert judgment.payment_outcome == PaymentOutcome.PAYMENT_PLAN
    assert judgment.payment_probability == 0.95


def test_parse_judgment_maps_pending_outcome_to_no_commitment() -> None:
    judgment = _parse_judgment(
        """{
  "reasoning": "Conversation is still ongoing.",
  "payment_outcome": "pending_verification",
  "payment_probability": 85,
  "debtor_satisfaction": 90,
  "compliance_score": 100,
  "conversation_efficiency": 0.85,
  "rapport_built": 90,
  "escalation_risk": 5,
  "end_reason": "ongoing",
  "constraint_violations": []
}""",
        turn_count=6,
    )

    assert judgment.payment_outcome == PaymentOutcome.NO_COMMITMENT
    assert judgment.payment_probability == 0.85
    assert judgment.compliance_score == 1.0
    assert judgment.escalation_risk == 0.05
    assert judgment.conversation_efficiency == 6


def test_parse_judgment_maps_negotiating_outcome_to_no_commitment() -> None:
    judgment = _parse_judgment(
        """{
  "reasoning": "The debtor is negotiating between a plan and settlement.",
  "payment_outcome": "Negotiating plan or settlement",
  "payment_probability": 0.85,
  "debtor_satisfaction": 0.8,
  "compliance_score": 1.0,
  "conversation_efficiency": 0.85,
  "rapport_built": 0.8,
  "escalation_risk": 0.1,
  "end_reason": "Ongoing",
  "constraint_violations": []
}""",
        turn_count=6,
    )

    assert judgment.payment_outcome == PaymentOutcome.NO_COMMITMENT
    assert judgment.end_reason == "Ongoing"


def test_parse_judgment_accepts_live_aliases_and_ten_point_scores() -> None:
    judgment = _parse_judgment(
        """{
  "reasoning": "The debtor promised to call back.",
  "payment_outcome": "promised",
  "payment_probability": 4,
  "debtor_satisfaction": 5,
  "compliance_score": 9,
  "conversation_efficiency": 6,
  "rapport_built": 4,
  "escalation_risk": 5,
  "end_reason": "debtor_promised_callback",
  "constraint_violations": []
}""",
        turn_count=6,
    )

    assert judgment.payment_outcome == PaymentOutcome.PROMISE_TO_PAY
    assert judgment.payment_probability == 0.4
    assert judgment.compliance_score == 0.9
    assert judgment.escalation_risk == 0.5
