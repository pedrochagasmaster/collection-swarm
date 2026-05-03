# Arena & Elo System

::: collection_swarm.arena

The arena module implements an Elo rating system for ranking collection strategies against debtor profiles in adversarial tournaments. Strategies gain rating when they produce high payment probability with good compliance; profiles gain rating when they resist collection attempts.

---

## Core Concepts

The arena treats each simulation as a **game** between a strategy and a profile:

- A **strategy wins** when it achieves high payment probability and compliance.
- A **profile wins** when the strategy fails (low payment or compliance violations).
- The **draw zone** is controlled by `DRAW_THRESHOLD = 0.05`.

Ratings start at **1500** and move up or down after each game, using the standard Elo expected-score formula.

---

## Rating Functions

### `elo_expected()`

```python
def elo_expected(rating_a: float, rating_b: float) -> float
```

Compute the expected score for player A against player B using the standard Elo formula:

$$E_A = \frac{1}{1 + 10^{(R_B - R_A) / 400}}$$

| Parameter | Type | Description |
|---|---|---|
| `rating_a` | `float` | Current rating of player A |
| `rating_b` | `float` | Current rating of player B |

**Returns:** A float between 0 and 1 representing A's expected score.

---

### `elo_update()`

```python
def elo_update(rating: float, expected: float, actual: float, k: float) -> float
```

Compute the new rating after a game:

$$R' = R + K \times (S - E)$$

| Parameter | Type | Description |
|---|---|---|
| `rating` | `float` | Current rating |
| `expected` | `float` | Expected score from `elo_expected()` |
| `actual` | `float` | Actual score achieved (0.0–1.0) |
| `k` | `float` | K-factor controlling rating volatility |

**Returns:** The updated rating.

---

### `effective_score()`

```python
def effective_score(
    judgment: Judgment | None,
    scoring: str = "payment_x_compliance",
) -> float
```

Convert a `Judgment` into a single scalar score for the strategy.

| Scoring Mode | Formula | Use Case |
|---|---|---|
| `payment_x_compliance` (default) | `payment_probability × compliance_score` | Balanced scoring — high payment alone is insufficient without compliance |
| `payment_only` | `payment_probability` | Testing scenarios where compliance is controlled separately |

!!! warning "None Judgment"
    If `judgment` is `None` (e.g., the simulation errored), the effective score is `0.0` — a total loss for the strategy.

---

### `k_factor()`

```python
def k_factor(
    games_played: int,
    initial: float = 32,
    stable: float = 16,
    threshold: int = 30,
) -> float
```

Adaptive K-factor that starts high for new entities and decreases after sufficient games.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `games_played` | `int` | — | Number of games the entity has played |
| `initial` | `float` | `32` | K-factor for entities below the threshold |
| `stable` | `float` | `16` | K-factor for entities at or above the threshold |
| `threshold` | `int` | `30` | Games-played cutoff between initial and stable phases |

```
K-factor
  32 ┤ ████████████████████████████████
     │                                 │
  16 ┤                                 ████████████████
     │
     └──────────────────────────────────────────────────
     0                              30           games
```

!!! info "Rationale"
    New strategies and profiles need larger rating adjustments to converge quickly. Once they have 30+ games, the K-factor halves to stabilize their rating.

---

## Rating Updates

### `update_ratings()`

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

Compute rating changes for both the strategy and the profile after one simulation.

**Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `strategy_rating` | `EloRating` | — | Current strategy rating state |
| `profile_rating` | `EloRating` | — | Current profile rating state |
| `judgment` | `Judgment \| None` | — | Simulation judgment (or `None` on error) |
| `simulation_id` | `str` | — | ID of the simulation that produced this result |
| `scoring` | `str` | `"payment_x_compliance"` | Scoring mode for `effective_score()` |
| `k_factor_initial` | `float` | `32` | Initial K-factor |
| `k_factor_stable` | `float` | `16` | Stable K-factor |
| `k_factor_threshold` | `int` | `30` | Games threshold |

**Returns:** A tuple of `(strategy_update, profile_update)`, each an `EloUpdate` dataclass.

**Score Relationship**

The strategy and profile scores are complementary:

```
strategy_score = effective_score(judgment, scoring)
profile_score  = 1 - strategy_score
```

A perfect strategy score of 1.0 means the profile scored 0.0, and vice versa.

---

### `EloUpdate` Dataclass

Each update captures the full audit trail:

```python
class EloUpdate(BaseModel):
    entity_type: Literal["strategy", "profile"]
    entity_id: str
    opponent_id: str
    conversation_model: str
    judge_model: str
    simulation_id: str
    rating_before: float
    rating_after: float
    effective_score: float
    expected_score: float
```

---

## Pairing Algorithms

### `swiss_pairings()`

```python
def swiss_pairings(
    strategy_ratings: list[EloRating],
    profile_ratings: list[EloRating],
    history: set[tuple[str, str]],
) -> list[tuple[str, str]]
```

Generate one round of pairings using a Swiss-system approach.

**Behavior:**

1. Strategies are sorted by `(games_played, -rating, entity_id)` — under-played strategies get priority.
2. Profiles are sorted with **bye priority** — profiles with zero games are prioritized, then sorted by `(-rating, entity_id)`.
3. The algorithm attempts a **backtracking search** to find pairings that avoid repeat matchups from `history`.
4. If a perfect matching without repeats is impossible, it falls back to a greedy approach that prefers novel pairings but allows repeats when necessary.

**Parameters**

| Parameter | Type | Description |
|---|---|---|
| `strategy_ratings` | `list[EloRating]` | Current strategy ratings |
| `profile_ratings` | `list[EloRating]` | Current profile ratings |
| `history` | `set[tuple[str, str]]` | Set of `(strategy_id, profile_id)` pairs already played |

**Returns:** A `list[tuple[str, str]]` of `(strategy_id, profile_id)` pairings for the round.

!!! tip "When to Use Swiss vs. Round Robin"
    Use **Swiss pairings** when the pool is large and you want efficient convergence — each round targets the most informative matchups. Use **round robin** when you need exhaustive coverage across a small pool.

---

### `round_robin_pairings()`

```python
def round_robin_pairings(
    strategy_ids: list[str],
    profile_ids: list[str],
) -> list[tuple[str, str]]
```

Generate all possible `(strategy, profile)` pairs — a full Cartesian product.

```python
pairings = round_robin_pairings(
    ["empathetic_plan", "firm_deadline"],
    ["cooperative_hardship", "angry_disputer"],
)
# [
#     ("empathetic_plan", "cooperative_hardship"),
#     ("empathetic_plan", "angry_disputer"),
#     ("firm_deadline", "cooperative_hardship"),
#     ("firm_deadline", "angry_disputer"),
# ]
```

---

## Draw Threshold

```python
DRAW_THRESHOLD = 0.05
```

Defined in `collection_swarm.models`, the draw threshold determines when a game outcome is considered a draw rather than a win or loss. When the effective score falls within `DRAW_THRESHOLD` of `0.5`, neither side gains a decisive advantage.

---

## End-to-End Example

```python
from collection_swarm.arena import update_ratings, swiss_pairings
from collection_swarm.models import EloRating, Judgment

strategy = EloRating(entity_type="strategy", entity_id="empathetic_plan", rating=1520, games_played=5)
profile = EloRating(entity_type="profile", entity_id="angry_disputer", rating=1480, games_played=3)

judgment = Judgment(
    reasoning="Strategy maintained compliance while securing commitment.",
    payment_probability=0.65,
    compliance_score=0.92,
    debtor_satisfaction=0.7,
    escalation_risk=0.15,
)

strategy_update, profile_update = update_ratings(strategy, profile, judgment, simulation_id="sim_001")

print(f"Strategy: {strategy_update.rating_before:.0f} → {strategy_update.rating_after:.0f}")
print(f"Profile:  {profile_update.rating_before:.0f} → {profile_update.rating_after:.0f}")
```
