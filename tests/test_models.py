import pytest
from pydantic import ValidationError

from collection_swarm.models import ConstraintRule, EloRating, Profile, TournamentConfig


def test_constraint_rule_requires_amount_for_max_payment():
    with pytest.raises(ValidationError):
        ConstraintRule(type="max_payment")


def test_profile_exposes_account_data():
    profile = Profile(
        id="sample",
        archetype="cooperative",
        financial_situation="hardship",
        debt_amount=500,
        debt_age_days=45,
        debt_type="medical",
        prior_contact_count=1,
        emotional_state="anxious",
        primary_objection="inability_to_pay",
        responsiveness="high",
        demographics="family_provider",
        backstory="Needs time.",
    )

    assert profile.account_data.debt_amount == 500
    assert profile.account_data.debt_type == "medical"


def test_elo_rating_defaults():
    rating = EloRating(entity_type="strategy", entity_id="empathetic_payment_plan")

    assert rating.rating == 1500.0
    assert rating.games_played == 0
    assert rating.wins == 0
    assert rating.losses == 0
    assert rating.draws == 0


def test_tournament_config_defaults_and_validation():
    config = TournamentConfig()

    assert config.format == "swiss"
    assert config.rounds == 4
    assert config.scoring == "payment_x_compliance"

    with pytest.raises(ValidationError):
        TournamentConfig(format="knockout")
