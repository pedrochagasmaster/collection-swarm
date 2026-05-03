# `arena.py` — Elo math and pairings

<span class="cs-kicker">collection_swarm/arena.py</span>

A 130-line module of pure functions: standard Elo, an effective-score
helper that combines payment probability and compliance, and Swiss /
round-robin pairings. No side effects, no I/O. The runner is the only
caller.

<dl class="cs-summary">
  <dt>Imports</dt><dd>domain models only</dd>
  <dt>Side effects</dt><dd>None</dd>
  <dt>Determinism</dt><dd>Pure functions</dd>
</dl>

## Elo primitives

```python
def elo_expected(rating_a: float, rating_b: float) -> float:
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def elo_update(rating: float, expected: float, actual: float, k: float) -> float:
    return rating + k * (actual - expected)
```

Standard chess-style Elo. The "actual" is the score in `[0, 1]`.

## `effective_score(judgment, scoring="payment_x_compliance")`

Maps a `Judgment` to a 0–1 score depending on the scoring mode:

| Mode                       | Formula                                              |
| -------------------------- | ---------------------------------------------------- |
| `payment_x_compliance` (default) | `payment_probability * compliance_score`        |
| `payment_only`             | `payment_probability`                                |

Anything else raises `ValueError`. This is the only place the scoring
policy lives — both the `runner` and `update_ratings` route through it.

## `k_factor(games_played, initial=32, stable=16, threshold=30)`

Returns `initial` until an entity has played `threshold` games, then
`stable`. The defaults match `config/simulation.yaml > arena`.

## `update_ratings(strategy_rating, profile_rating, judgment, simulation_id, …)`

Symmetric update for one Simulation:

```python
strategy_score = effective_score(judgment, scoring=scoring)
profile_score = 1 - strategy_score
strategy_expected = elo_expected(strategy_rating.rating, profile_rating.rating)
profile_expected = elo_expected(profile_rating.rating, strategy_rating.rating)

strategy_k = k_factor(strategy_rating.games_played, k_factor_initial, k_factor_stable, k_factor_threshold)
profile_k = k_factor(profile_rating.games_played, k_factor_initial, k_factor_stable, k_factor_threshold)

return (
    EloUpdate(entity_type="strategy", ..., rating_after=elo_update(rs, exp_s, score_s, k_s), ...),
    EloUpdate(entity_type="profile",  ..., rating_after=elo_update(rp, exp_p, score_p, k_p), ...),
)
```

The Profile is the "opponent" — a successful collection means the
Strategy beat the Profile, so the Profile's score is `1 - strategy_score`.
This framing is how a hard Profile climbs the Profile leaderboard:
strategies that fail against it score it higher.

## Pairings

### `swiss_pairings(strategy_ratings, profile_ratings, history)`

Pairs strategies and profiles for the next round of a Swiss tournament:

1. Sort strategies by `(games_played, -rating, entity_id)` so under-played
   entities go first, ties broken by rating.
2. Sort profiles the same way, with `_bye_priority(games_played)` putting
   not-yet-played profiles first.
3. Try `_match_without_repeats` (depth-first search) to find a perfect
   pairing where no `(strategy, profile)` tuple already exists in
   `history`.
4. If no perfect matching exists, fall back to a greedy fallback that
   prefers no-repeat matches but accepts repeats rather than dropping
   entities.

The DFS is bounded by the number of entities in a round, which is
typically <= 50. No memoization needed.

### `round_robin_pairings(strategy_ids, profile_ids)`

Cartesian product. Every Strategy plays every Profile this round. Use
this when populations are small and you want exhaustive coverage.

## How tournaments use this

`runner.run_tournament` calls `swiss_pairings` (or
`round_robin_pairings`) once per round, builds `MatrixCell`s, dispatches
them, and threads the resulting `Judgment`s through `update_ratings`.
Every `EloUpdate` lands in `elo_history` via
`store.save_elo_update(update, tournament_id=...)`.

## Why payment × compliance

See [Arena & evolution](../concepts/arena-and-evolution.md#why-payment-compliance-not-payment-alone).
The short version: a strategy that lands payments by violating
regulation is unusable in production, so the arena penalizes
non-compliance multiplicatively rather than as a soft constraint.
