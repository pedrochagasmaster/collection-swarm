---
title: Tournaments & Elo
layout: default
nav_order: 11
---

# Tournaments & Elo Rating System
{: .no_toc }

Competitive strategy evaluation using Elo ratings, Swiss pairing, and round-robin tournaments.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Source:** `src/collection_swarm/arena.py`

## Overview

The arena module implements an **Elo rating system** adapted for the collection domain. Strategies compete against profiles: a strategy that achieves high payment with good compliance gains rating, while a profile that resists collection gains rating.

This creates a natural adversarial dynamic — the system simultaneously identifies the best strategies and the toughest profiles.

## Elo Mathematics

### Expected Score

```python
def elo_expected(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
```

Standard Elo formula. A 400-point rating difference corresponds to a 10:1 expected score ratio.

### Rating Update

```python
def elo_update(rating: float, expected: float, actual: float, k: float) -> float:
    return rating + k * (actual - expected)
```

The K-factor determines how much a single game affects the rating.

### Adaptive K-Factor

```python
def k_factor(games_played: int, initial: float = 32, stable: float = 16, threshold: int = 30) -> float:
    return initial if games_played < threshold else stable
```

| Phase | K-Factor | Effect |
|:------|:---------|:-------|
| New entity (< 30 games) | 32 | Ratings change quickly |
| Established entity (≥ 30 games) | 16 | Ratings stabilize |

## Effective Score

```python
def effective_score(judgment: Judgment | None, scoring: str = "payment_x_compliance") -> float
```

The effective score determines who "won" a simulation:

| Scoring Mode | Formula |
|:-------------|:--------|
| `payment_x_compliance` | `payment_probability × compliance_score` |
| `payment_only` | `payment_probability` |

The **strategy** gets the effective score; the **profile** gets `1 - effective_score`. This means:
- High payment + high compliance → strategy wins
- Low payment or low compliance → profile wins

### Draw Threshold

Outcomes within 0.05 of 0.50 are classified as draws (`DRAW_THRESHOLD = 0.05`).

## Rating Updates

```python
def update_ratings(
    strategy_rating: EloRating,
    profile_rating: EloRating,
    judgment: Judgment | None,
    simulation_id: str,
    scoring: str = "payment_x_compliance",
    k_factor_initial: float = 32,
    k_factor_stable: float = 16,
    k_factor_threshold: int = 30,
) -> tuple[EloUpdate, EloUpdate]
```

After each simulation, this function:

1. Computes the effective score from the judgment.
2. Calculates expected scores for both the strategy and profile.
3. Determines K-factors based on games played.
4. Produces two `EloUpdate` objects (one for strategy, one for profile).

Both updates are returned as a tuple and saved to the store.

## Tournament Formats

### Swiss Pairing

```python
def swiss_pairings(
    strategy_ratings: list[EloRating],
    profile_ratings: list[EloRating],
    history: set[tuple[str, str]],
) -> list[tuple[str, str]]
```

Swiss pairing produces balanced matchups:

1. **Sort strategies** by games played (ascending), then rating (descending).
2. **Sort profiles** with bye priority (profiles with 0 games get priority), then by rating.
3. **Attempt optimal matching** — use backtracking search to find pairings that avoid repeating previous matchups.
4. **Fallback** — if perfect matching is impossible, greedily pair strategies with available profiles, preferring non-repeat matchups.

This ensures:
- Entities with fewer games play first.
- Similarly-rated opponents are paired together.
- Repeat matchups are minimized.

### Round Robin

```python
def round_robin_pairings(strategy_ids: list[str], profile_ids: list[str]) -> list[tuple[str, str]]
```

Simply produces every `(strategy, profile)` combination. Used when complete coverage is more important than efficiency.

## Tournament Execution

Tournament execution is handled by `runner.run_tournament()` (see [Runner & Orchestration]({% link runner.md %})). The arena module provides the mathematical primitives; the runner orchestrates the full tournament lifecycle.

### Tournament Flow

```
For each round:
  1. Get current Elo ratings
  2. Generate pairings (Swiss or Round Robin)
  3. Run simulations for all pairings
  4. Update Elo ratings from results
  5. Record history
  6. Notify round completion callback

After all rounds:
  Save tournament result to store
```
