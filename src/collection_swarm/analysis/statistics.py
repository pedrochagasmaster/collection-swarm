"""Deterministic strategy ranking helpers."""

from __future__ import annotations

from dataclasses import dataclass
from math import erf, sqrt

from collection_swarm.models import StrategyComparison, StrategyStats
from collection_swarm.store import SimulationStore


@dataclass(frozen=True)
class StrategyRanking:
    profile_id: str
    strategies: list[StrategyStats]
    comparisons: list[StrategyComparison]
    needs_more_data: list[str]

    @property
    def recommended_strategy_id(self) -> str | None:
        return self.strategies[0].strategy_id if self.strategies else None

    @property
    def statistically_tied(self) -> bool:
        return any(comparison.tied for comparison in self.comparisons[:1])


def compare_strategies(
    profile_id: str,
    store: SimulationStore,
    significance_level: float = 0.05,
    min_samples_for_significance: int = 3,
) -> StrategyRanking:
    """Rank strategies by mean payment probability for a profile."""
    strategies = store.get_strategy_comparison(profile_id)
    samples = store.get_payment_probability_samples(profile_id)
    comparisons: list[StrategyComparison] = []
    needs_more_data: list[str] = []
    if not strategies:
        return StrategyRanking(profile_id=profile_id, strategies=[], comparisons=[], needs_more_data=[])

    best_id = strategies[0].strategy_id
    best_samples = samples.get(best_id, [])
    for challenger in strategies[1:]:
        challenger_samples = samples.get(challenger.strategy_id, [])
        p_value = mann_whitney_u_p_value(best_samples, challenger_samples)
        significant = (
            len(best_samples) >= min_samples_for_significance
            and len(challenger_samples) >= min_samples_for_significance
            and p_value < significance_level
        )
        tied = not significant
        comparisons.append(
            StrategyComparison(
                profile_id=profile_id,
                strategy_a=best_id,
                strategy_b=challenger.strategy_id,
                p_value=p_value,
                significant=significant,
                tied=tied,
            )
        )
        if tied:
            needs_more_data.append(challenger.strategy_id)
    return StrategyRanking(
        profile_id=profile_id,
        strategies=strategies,
        comparisons=comparisons,
        needs_more_data=needs_more_data,
    )


def bootstrap_ci(values: list[float], confidence: float = 0.95) -> tuple[float, float]:
    """Deterministic small-sample CI using normal approximation around the mean."""
    if not values:
        return (0.0, 0.0)
    if len(values) == 1:
        return (values[0], values[0])
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    z = 1.96 if confidence == 0.95 else 1.96
    margin = z * sqrt(variance / len(values))
    return (max(0.0, mean - margin), min(1.0, mean + margin))


def mann_whitney_u_p_value(a: list[float], b: list[float]) -> float:
    """Approximate two-sided Mann-Whitney U p-value without scipy.

    This is sufficient for deterministic ranking signals in the CLI. Small samples
    are deliberately treated as non-significant so the playbook asks for more data.
    """
    n1 = len(a)
    n2 = len(b)
    if n1 < 2 or n2 < 2:
        return 1.0
    combined = sorted([(value, "a") for value in a] + [(value, "b") for value in b], key=lambda item: item[0])
    ranks: list[tuple[str, float]] = []
    index = 0
    while index < len(combined):
        end = index + 1
        while end < len(combined) and combined[end][0] == combined[index][0]:
            end += 1
        average_rank = (index + 1 + end) / 2
        for _, group in combined[index:end]:
            ranks.append((group, average_rank))
        index = end
    rank_sum_a = sum(rank for group, rank in ranks if group == "a")
    u1 = rank_sum_a - n1 * (n1 + 1) / 2
    mean_u = n1 * n2 / 2
    std_u = sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    if std_u == 0:
        return 1.0
    z = abs((u1 - mean_u) / std_u)
    return max(0.0, min(1.0, 2 * (1 - _normal_cdf(z))))


def _normal_cdf(z: float) -> float:
    return 0.5 * (1 + erf(z / sqrt(2)))
