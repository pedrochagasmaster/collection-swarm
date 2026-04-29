from __future__ import annotations

from collection_swarm.analysis.statistics import bootstrap_ci, mann_whitney_u_p_value


def test_bootstrap_ci_single_sample_is_exact() -> None:
    assert bootstrap_ci([0.72]) == (0.72, 0.72)


def test_mann_whitney_detects_separated_samples() -> None:
    assert mann_whitney_u_p_value([0.9, 0.92, 0.95, 0.91], [0.1, 0.2, 0.15, 0.12]) < 0.05
