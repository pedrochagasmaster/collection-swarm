from __future__ import annotations

import pytest

from collection_swarm.arena import (
    effective_score,
    elo_expected,
    elo_update,
    k_factor,
    round_robin_pairings,
    swiss_pairings,
    update_ratings,
)
from collection_swarm.models import EloRating, Judgment, PaymentOutcome


def _judgment(payment: float = 0.8, compliance: float = 0.9) -> Judgment:
    return Judgment(
        reasoning="scored",
        payment_outcome=PaymentOutcome.PAYMENT_PLAN,
        payment_probability=payment,
        debtor_satisfaction=0.7,
        compliance_score=compliance,
        conversation_efficiency=2,
        rapport_built=0.6,
        escalation_risk=0.1,
    )


def test_elo_expected_equal_ratings() -> None:
    assert elo_expected(1500, 1500) == pytest.approx(0.5)


def test_elo_expected_strong_vs_weak() -> None:
    assert elo_expected(1800, 1200) > 0.9


def test_elo_update_win_is_zero_sum_for_equal_k() -> None:
    winner = elo_update(1500, expected=0.5, actual=1.0, k=32)
    loser = elo_update(1500, expected=0.5, actual=0.0, k=32)

    assert winner > 1500
    assert loser < 1500
    assert (winner - 1500) + (loser - 1500) == pytest.approx(0)


def test_elo_update_draw_equal_ratings_no_movement() -> None:
    assert elo_update(1500, expected=0.5, actual=0.5, k=32) == pytest.approx(1500)


def test_effective_score_multiplies_payment_and_compliance() -> None:
    assert effective_score(_judgment(payment=0.8, compliance=0.9)) == pytest.approx(0.72)


def test_effective_score_none_judgment() -> None:
    assert effective_score(None) == 0.0


def test_k_factor_decay() -> None:
    assert k_factor(29) == 32
    assert k_factor(30) == 16


def test_update_ratings_returns_strategy_and_profile_updates() -> None:
    strategy = EloRating(entity_type="strategy", entity_id="s1")
    profile = EloRating(entity_type="profile", entity_id="p1")

    strategy_update, profile_update = update_ratings(strategy, profile, _judgment(payment=0.3, compliance=0.9), "sim_1")

    assert strategy_update.entity_type == "strategy"
    assert profile_update.entity_type == "profile"
    assert strategy_update.opponent_id == "p1"
    assert profile_update.opponent_id == "s1"
    assert strategy_update.rating_after < strategy_update.rating_before
    assert profile_update.rating_after > profile_update.rating_before


def test_update_ratings_uses_each_side_games_for_k_factor() -> None:
    strategy = EloRating(entity_type="strategy", entity_id="s1", games_played=2)
    profile = EloRating(entity_type="profile", entity_id="p1", games_played=50)

    strategy_update, profile_update = update_ratings(strategy, profile, _judgment(payment=1.0, compliance=1.0), "sim_1")

    assert strategy_update.rating_after - strategy_update.rating_before == pytest.approx(16.0)
    assert profile_update.rating_after - profile_update.rating_before == pytest.approx(-8.0)


def test_swiss_pairings_pairs_by_rank() -> None:
    strategies = [
        EloRating(entity_type="strategy", entity_id="s2", rating=1400),
        EloRating(entity_type="strategy", entity_id="s1", rating=1600),
    ]
    profiles = [
        EloRating(entity_type="profile", entity_id="p2", rating=1300),
        EloRating(entity_type="profile", entity_id="p1", rating=1700),
    ]

    assert swiss_pairings(strategies, profiles, history=set()) == [("s1", "p1"), ("s2", "p2")]


def test_swiss_pairings_avoids_repeats() -> None:
    strategies = [
        EloRating(entity_type="strategy", entity_id="s1", rating=1600),
        EloRating(entity_type="strategy", entity_id="s2", rating=1500),
    ]
    profiles = [
        EloRating(entity_type="profile", entity_id="p1", rating=1600),
        EloRating(entity_type="profile", entity_id="p2", rating=1500),
    ]

    assert swiss_pairings(strategies, profiles, history={("s1", "p1")}) == [("s1", "p2"), ("s2", "p1")]


def test_swiss_pairings_finds_non_greedy_no_repeat_assignment() -> None:
    strategies = [
        EloRating(entity_type="strategy", entity_id="s1", rating=1600),
        EloRating(entity_type="strategy", entity_id="s2", rating=1500),
    ]
    profiles = [
        EloRating(entity_type="profile", entity_id="p1", rating=1600),
        EloRating(entity_type="profile", entity_id="p2", rating=1500),
    ]

    assert swiss_pairings(strategies, profiles, history={("s2", "p2")}) == [("s1", "p2"), ("s2", "p1")]


def test_swiss_pairings_prioritizes_unplayed_byes_next_round() -> None:
    strategies = [
        EloRating(entity_type="strategy", entity_id="s1", games_played=1, rating=1700),
        EloRating(entity_type="strategy", entity_id="s2", games_played=0, rating=1400),
    ]
    profiles = [
        EloRating(entity_type="profile", entity_id="p1", games_played=1, rating=1700),
        EloRating(entity_type="profile", entity_id="p2", games_played=0, rating=1400),
        EloRating(entity_type="profile", entity_id="p3", games_played=0, rating=1300),
    ]

    assert swiss_pairings(strategies, profiles, history=set()) == [("s2", "p2"), ("s1", "p3")]


def test_round_robin_pairings_covers_all() -> None:
    assert round_robin_pairings(["s1", "s2"], ["p1", "p2", "p3"]) == [
        ("s1", "p1"),
        ("s1", "p2"),
        ("s1", "p3"),
        ("s2", "p1"),
        ("s2", "p2"),
        ("s2", "p3"),
    ]
