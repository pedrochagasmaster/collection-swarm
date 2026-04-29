"""Deterministic strategy ranking helpers."""

from __future__ import annotations

from dataclasses import dataclass

from collection_swarm.models import StrategyStats
from collection_swarm.store import SimulationStore


@dataclass(frozen=True)
class StrategyRanking:
    profile_id: str
    strategies: list[StrategyStats]

    @property
    def recommended_strategy_id(self) -> str | None:
        return self.strategies[0].strategy_id if self.strategies else None


def compare_strategies(profile_id: str, store: SimulationStore) -> StrategyRanking:
    """Rank strategies by mean payment probability for a profile."""
    return StrategyRanking(profile_id=profile_id, strategies=store.get_strategy_comparison(profile_id))
