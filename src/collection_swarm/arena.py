"""Elo arena utilities for adversarial collection tournaments."""

from __future__ import annotations

from collection_swarm.models import EloRating, EloUpdate, Judgment


def elo_expected(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def elo_update(rating: float, expected: float, actual: float, k: float) -> float:
    return rating + k * (actual - expected)


def effective_score(judgment: Judgment | None, scoring: str = "payment_x_compliance") -> float:
    if judgment is None:
        return 0.0
    if scoring == "payment_only":
        return judgment.payment_probability
    if scoring != "payment_x_compliance":
        raise ValueError(f"unsupported arena scoring mode '{scoring}'")
    return judgment.payment_probability * judgment.compliance_score


def k_factor(games_played: int, initial: float = 32, stable: float = 16, threshold: int = 30) -> float:
    return initial if games_played < threshold else stable


def update_ratings(
    strategy_rating: EloRating,
    profile_rating: EloRating,
    judgment: Judgment | None,
    simulation_id: str,
    scoring: str = "payment_x_compliance",
    k_factor_initial: float = 32,
    k_factor_stable: float = 16,
    k_factor_threshold: int = 30,
) -> tuple[EloUpdate, EloUpdate]:
    strategy_score = effective_score(judgment, scoring=scoring)
    profile_score = 1 - strategy_score
    strategy_expected = elo_expected(strategy_rating.rating, profile_rating.rating)
    profile_expected = elo_expected(profile_rating.rating, strategy_rating.rating)

    strategy_k = k_factor(strategy_rating.games_played, k_factor_initial, k_factor_stable, k_factor_threshold)
    profile_k = k_factor(profile_rating.games_played, k_factor_initial, k_factor_stable, k_factor_threshold)

    return (
        EloUpdate(
            entity_type="strategy",
            entity_id=strategy_rating.entity_id,
            opponent_id=profile_rating.entity_id,
            conversation_model=strategy_rating.conversation_model,
            judge_model=strategy_rating.judge_model,
            simulation_id=simulation_id,
            rating_before=strategy_rating.rating,
            rating_after=elo_update(strategy_rating.rating, strategy_expected, strategy_score, strategy_k),
            effective_score=strategy_score,
            expected_score=strategy_expected,
        ),
        EloUpdate(
            entity_type="profile",
            entity_id=profile_rating.entity_id,
            opponent_id=strategy_rating.entity_id,
            conversation_model=profile_rating.conversation_model,
            judge_model=profile_rating.judge_model,
            simulation_id=simulation_id,
            rating_before=profile_rating.rating,
            rating_after=elo_update(profile_rating.rating, profile_expected, profile_score, profile_k),
            effective_score=profile_score,
            expected_score=profile_expected,
        ),
    )


def swiss_pairings(
    strategy_ratings: list[EloRating],
    profile_ratings: list[EloRating],
    history: set[tuple[str, str]],
) -> list[tuple[str, str]]:
    strategies = sorted(strategy_ratings, key=lambda item: (item.games_played, -item.rating, item.entity_id))
    profiles = sorted(profile_ratings, key=lambda item: (_bye_priority(item.games_played), -item.rating, item.entity_id))
    target = min(len(strategies), len(profiles))
    matched = _match_without_repeats(strategies[:target], profiles, history)
    if len(matched) == target:
        return matched

    unused_profiles = {profile.entity_id for profile in profiles}
    pairings: list[tuple[str, str]] = []
    for strategy in strategies[:target]:
        available = [profile for profile in profiles if profile.entity_id in unused_profiles]
        if not available:
            break
        profile = next(
            (candidate for candidate in available if (strategy.entity_id, candidate.entity_id) not in history),
            available[0],
        )
        pairings.append((strategy.entity_id, profile.entity_id))
        unused_profiles.remove(profile.entity_id)
    return pairings


def _match_without_repeats(
    strategies: list[EloRating],
    profiles: list[EloRating],
    history: set[tuple[str, str]],
) -> list[tuple[str, str]]:
    def search(index: int, used_profiles: set[str], pairings: list[tuple[str, str]]) -> list[tuple[str, str]] | None:
        if index == len(strategies):
            return pairings
        strategy = strategies[index]
        for profile in profiles:
            if profile.entity_id in used_profiles or (strategy.entity_id, profile.entity_id) in history:
                continue
            result = search(
                index + 1,
                used_profiles | {profile.entity_id},
                [*pairings, (strategy.entity_id, profile.entity_id)],
            )
            if result is not None:
                return result
        return None

    return search(0, set(), []) or []


def _bye_priority(games_played: int) -> int:
    return 0 if games_played == 0 else 1


def round_robin_pairings(strategy_ids: list[str], profile_ids: list[str]) -> list[tuple[str, str]]:
    return [(strategy_id, profile_id) for strategy_id in strategy_ids for profile_id in profile_ids]
