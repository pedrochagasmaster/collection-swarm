from __future__ import annotations

from collection_swarm.agents.judge import verify_constraints
from collection_swarm.models import Constraint, ConstraintRule, Message, Profile


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
