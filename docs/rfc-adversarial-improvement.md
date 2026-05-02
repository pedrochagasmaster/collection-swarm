# RFC: Adversarial Self-Improvement for Collection Swarm

**Status:** Draft / Exploration  
**Author:** AI Agent  
**Date:** 2026-05-02

---

## Motivation

Collection Swarm currently runs **open-loop** simulations: strategies and debtor profiles are hand-authored in YAML, conversations are generated, and a Judge scores them — but **nothing feeds back** into the agents to make them better over time. The system discovers *which existing strategy works best* but never **invents new strategies** or **hardens debtors against weak tactics**.

AlphaGo's breakthrough was *adversarial self-play*: the system improved by playing against itself, with each generation forcing the next to be stronger. We can apply the same principle here. The Collector and Debtor are already natural adversaries — one wants payment, the other resists. By closing the loop so that outcomes drive the evolution of both sides, we get a system that autonomously discovers better collection strategies *and* stress-tests them against increasingly realistic resistance.

Below are **five concrete architectural options**, ordered from lowest to highest implementation complexity. They are **not mutually exclusive** — the recommended path starts with Option A, layers on B, then graduates to C or D.

---

## The Current Architecture (Baseline)

```
YAML Strategy ──► Collector Agent ──┐
                                    ├── Conversation ──► Judge ──► SQLite
YAML Profile  ──► Debtor Agent   ──┘                               │
                                                                   ▼
                                                             Playbook (static)
```

**Key limitations:**
- Strategies are static text — humans write them, the system only ranks them.
- Debtor profiles never adapt; a profile that is "too easy" stays easy forever.
- No generation-over-generation improvement loop.
- The Judge is uncalibrated — it may reward surface-level compliance over actual effectiveness.

---

## Option A — Elo-Rated Arena with Tournament Selection

### Concept
Treat every (Strategy, Profile) matchup as a **competitive game** with a measurable outcome. Assign each strategy and each profile an **Elo rating**. Run round-robin or Swiss-system **tournaments** where:
- A strategy that achieves high `payment_probability` against tough debtors **gains Elo**.
- A debtor profile that resists payment against strong strategies **gains Elo**.
- Strategies are ranked by Elo rather than raw averages — this corrects for difficulty.

### AlphaGo Analogy
This is the equivalent of AlphaGo's **rating system** — it doesn't yet generate new players, but it properly measures who is strongest and pairs strong vs. strong to accelerate learning signal.

### Complexity: Low
- No new LLM calls beyond existing simulations.
- Elo math is deterministic (~50 lines).
- Biggest change is the tournament scheduler and matchmaking logic.

---

### Deep Dive: Why Elo Fixes the Current Ranking Problem

Today, `compare_strategies` in `analysis/statistics.py` ranks by `AVG(payment_probability)` across all simulations for a given profile. This is a **flat average** that ignores difficulty. Consider:

- Strategy X scores 90% payment probability against `cooperative_hardship` (easy) and 10% against `hostile_avoidant` (hard). Average: 50%.
- Strategy Y scores 60% against both. Average: 60%.

The current system recommends Strategy Y. But Strategy X is dramatically better against the easy profile and might be better overall if tested against harder opponents — we just don't know, because the flat average treats all opponents as equally informative.

Elo fixes this. A win against a high-rated debtor is worth more than a win against a low-rated one. Strategy X's 10% against a 1800-Elo debtor is more informative than Strategy Y's 60% against a 1200-Elo debtor.

More importantly, Elo on the **debtor side** tells us which profiles are genuinely hard. Today we guess based on archetype labels (`hostile` sounds harder than `cooperative`). With Elo, we'd have empirical proof: `scam_suspicious` might turn out to be harder than `hostile_avoidant` because it consistently resists even the best strategies.

---

### How a Simulation Maps to a "Game"

The mapping from Collection Swarm simulation to a two-player game:

| Game Concept | Collection Swarm Equivalent |
|---|---|
| **Player A** | Strategy (e.g. `empathetic_payment_plan`) |
| **Player B** | Profile (e.g. `hostile_avoidant`) |
| **Game board** | `SimulationEngine` — turn loop, stalemate detection, `max_turns=12` |
| **Moves** | Each `generate_turn()` call by Collector or Debtor |
| **Outcome** | `Judgment.payment_probability` from the Judge (0.0 to 1.0) |
| **Player A wins** | `payment_probability >= 0.5` (strategy extracted value) |
| **Player B wins** | `payment_probability < 0.5` (debtor resisted) |

Unlike chess (binary win/loss), our outcomes are **continuous** (0.0–1.0). We use the raw `payment_probability` as the score `S` rather than clamping to 0/1, which gives the Elo system richer signal per game.

The compliance dimension is handled separately: a strategy that wins via non-compliant tactics gets its `payment_probability` **penalized** before Elo. Specifically:

```
effective_score = payment_probability * compliance_score
```

This means a strategy that scores 80% payment probability but only 50% compliance gets an effective score of 0.40 — worse than an honest strategy that gets 50% payment probability with 100% compliance (effective 0.50). This embeds the business constraint directly into the competitive signal.

---

### Elo Math (Detailed)

Standard Elo with two adaptations: (1) continuous scores instead of binary, (2) K-factor decay.

```
# Expected score for player A against player B
E_a = 1 / (1 + 10^((R_b - R_a) / 400))

# Actual score (for strategy side)
S_strategy = payment_probability * compliance_score

# Actual score (for debtor side — inverse)
S_debtor = 1 - S_strategy

# K-factor: starts high for provisional ratings, decays after N games
K = 32 if games_played < 30 else 16

# Rating update
new_R_strategy = R_strategy + K * (S_strategy - E_strategy)
new_R_debtor   = R_debtor   + K * (S_debtor   - E_debtor)
```

**Starting rating:** All entities begin at **1500** (chess convention).

**Why K=32→16:** Early games should move ratings quickly (the system is still figuring out where everyone belongs). After 30 games, the rating stabilizes and updates should be smaller. This is exactly how FIDE handles new chess players.

**Worked example:**

1. `empathetic_payment_plan` (Elo 1500) plays `hostile_avoidant` (Elo 1500).
2. Expected score for both: `E = 1 / (1 + 10^0) = 0.5`.
3. Judge scores: `payment_probability = 0.3`, `compliance_score = 0.9`.
4. Effective score: `S_strategy = 0.3 * 0.9 = 0.27`. `S_debtor = 0.73`.
5. K = 32 (both are new).
6. `new_R_strategy = 1500 + 32 * (0.27 - 0.5) = 1500 - 7.36 = 1492.6`
7. `new_R_debtor = 1500 + 32 * (0.73 - 0.5) = 1500 + 7.36 = 1507.4`

The debtor "wins" this game, so it gains rating and the strategy loses rating. After 50+ games across all matchups, the Elo rankings reflect true relative strength far better than flat averages.

---

### Tournament Formats

Two formats, each useful for different purposes:

#### Round-Robin (exhaustive)

Every strategy plays every profile once (or N times). This is essentially what the current `build_matrix` / `run_matrix` already does — but with Elo updates after each game instead of a flat aggregation at the end.

- **Pairings:** 13 strategies × 15 profiles = **195 games** per round. With `default_repetitions: 3`, that's 585 games.
- **Best for:** Initial calibration, establishing baseline Elo for all entities.
- **Downside:** Expensive. Many games are uninformative (e.g., best strategy vs. easiest debtor).

#### Swiss-System (efficient)

After each round, pair entities with **similar Elo**. Strong strategies face hard debtors; weak strategies face easy debtors. Every game is maximally informative.

- **Pairings per round:** `min(num_strategies, num_profiles)` games. With 13 strategies and 15 profiles, that's ~13 games per round.
- **Rounds:** Typically `ceil(log2(N))` rounds are enough to rank N players. For 13 strategies, ~4 rounds = ~52 games (vs. 195 for round-robin).
- **Best for:** Budget-constrained runs. Reaches stable Elo with ~4× fewer simulations than round-robin.
- **Downside:** Some matchups are never tested. Coverage matrix has gaps.

**Swiss pairing algorithm:**

1. Sort strategies by Elo (descending). Sort profiles by Elo (descending).
2. Pair the #1 strategy with the #1 profile, #2 with #2, etc.
3. If a strategy has already played a given profile in this tournament, slide to the next available profile (avoid repeat matchups within a tournament).
4. Run all games in the round concurrently.
5. Update Elo ratings.
6. Re-sort and repeat for the next round.

The Swiss system is where the real efficiency win comes from. If `assertive_settlement` is clearly the best strategy, we don't need to waste simulations proving it beats `cooperative_hardship`. We want to know how it performs against `scam_suspicious` and `hostile_avoidant` — the hard cases. Swiss matchmaking automatically focuses there.

---

### What Elo Reveals That Flat Averages Cannot

With the current system, the playbook might say: "For `hostile_avoidant`, use `liquidation_explainer` (mean payment probability: 45%)." But this hides crucial information:

1. **How hard is `hostile_avoidant` really?** If its Elo is 1650 (high), that 45% is impressive — it means `liquidation_explainer` is good at cracking tough debtors. If its Elo is only 1350, that 45% is mediocre.

2. **Is `liquidation_explainer` a specialist or a generalist?** A strategy might have moderate flat averages but high Elo because it consistently beats the toughest profiles. The playbook should differentiate between "jack of all trades" and "specialist against hard cases."

3. **Which matchups are genuinely uncertain?** If both entities have high Elo, the expected score is ~0.5 and the game is a toss-up. These matchups are where more data would be most valuable — and where strategy refinements matter most.

4. **Rating stability / confidence:** An entity with 50 games has a much more reliable rating than one with 3 games. The `games_played` count becomes a built-in confidence metric. The system can flag: "Strategy X is rated 1580 but has only 5 games — rating is provisional."

---

### Composite Scoring: Blending Multiple Judgment Dimensions

The Judge produces multiple scores. How do we boil them down to a single "game score" for Elo?

**Option 1 — Payment probability × compliance (recommended for start):**
```
S = payment_probability * compliance_score
```
Simple, interpretable, and directly embeds the business constraint. A 100% payment probability with 0% compliance (illegal tactics) gets S=0.

**Option 2 — Weighted composite:**
```
S = w1 * payment_probability + w2 * compliance_score + w3 * rapport_built
    - w4 * escalation_risk
```
With weights configurable in `simulation.yaml`. More expressive, but requires tuning the weights. This is equivalent to defining what "winning" means for the business.

**Option 3 — Separate Elo per dimension:**
Each strategy gets an Elo for `payment_probability`, a separate Elo for `compliance_score`, a separate Elo for `rapport_built`, etc. This is the most informative but the most complex to interpret. Useful for analysis ("Strategy X is #1 at payment extraction but #8 at compliance").

The recommendation is to start with Option 1 and make the scoring function pluggable so users can upgrade to Option 2 or 3 without structural changes.

---

### Handling Noise and Variance

LLM outputs are stochastic — the same strategy vs. the same profile can produce different transcripts and different Judge scores each time. This is inherent noise, and Elo handles it naturally:

- **Each game is one data point.** Noise means individual games might produce "upsets" (a weak strategy gets lucky). But over many games, the ratings converge to the true skill level.
- **K-factor decay** helps: early games (K=32) move ratings fast despite noise. Later games (K=16) are more conservative, avoiding overreaction to outliers.
- **Repeated matchups are valuable:** Unlike chess where the same players replay rarely, we can re-run the same (strategy, profile) pair. Each repetition refines the Elo estimate. The Swiss system can be extended to re-match pairs where the rating uncertainty is highest (similar to TrueSkill's approach of targeting the most uncertain matchups).

**Rating confidence via Glicko-2 (optional upgrade):** If variance turns out to be a problem, the system could upgrade from basic Elo to Glicko-2, which tracks a **rating deviation** (σ) per entity. Entities with high σ are uncertain; the matchmaker prioritizes them. This is a drop-in replacement for the Elo formula — same input/output interface, just richer internal state.

---

### Integration with Existing Infrastructure

The arena layer sits between the existing `runner.py` and `engine.py`. It doesn't replace the matrix run system — it's an alternative orchestration mode.

```
                    ┌─────────────────────┐
                    │      CLI / Web      │
                    │  "tournament" cmd   │
                    └────────┬────────────┘
                             │
                  ┌──────────▼──────────┐
                  │      arena.py       │
                  │  - Elo ratings      │
                  │  - Swiss matchmaker │
                  │  - Round scheduler  │
                  └──────────┬──────────┘
                             │ produces MatrixCell
                  ┌──────────▼──────────┐
                  │     runner.py       │
                  │  run_cell() reused  │
                  └──────────┬──────────┘
                             │
                  ┌──────────▼──────────┐
                  │     engine.py       │
                  │  run_simulation()   │
                  └──────────┬──────────┘
                             │
                  ┌──────────▼──────────┐
                  │     store.py        │
                  │  save_run() +       │
                  │  save_elo_update()  │
                  └─────────────────────┘
```

Key reuse points:
- `SimulationEngine.run_simulation()` is unchanged. The arena just decides *which* simulations to run.
- `SimulationStore.save_run()` is unchanged. Elo persistence is additive (new table, no schema migration on `runs`).
- `MatrixCell` is reused as the pairing unit — the arena outputs `MatrixCell` objects, same as `build_matrix`.
- The existing `run_matrix` path remains available for users who want the brute-force Cartesian approach.

---

### New Data Model

```python
class EloRating(BaseModel):
    """Current Elo rating for a strategy or profile."""
    entity_type: Literal["strategy", "profile"]
    entity_id: str
    rating: float = 1500.0
    games_played: int = 0
    wins: int = 0            # games where effective score > 0.5
    losses: int = 0          # games where effective score < 0.5
    draws: int = 0           # games where effective score ≈ 0.5 (±0.05)

class EloUpdate(BaseModel):
    """Single Elo rating change from one game."""
    entity_type: Literal["strategy", "profile"]
    entity_id: str
    opponent_id: str
    simulation_id: str       # links back to SimulationResult.id
    rating_before: float
    rating_after: float
    effective_score: float   # S_strategy or S_debtor
    expected_score: float    # E from Elo formula
    timestamp: datetime

class TournamentConfig(BaseModel):
    """Settings for a tournament run."""
    format: Literal["round_robin", "swiss"] = "swiss"
    rounds: int = 4
    repetitions_per_pairing: int = 1
    k_factor_initial: float = 32.0
    k_factor_stable: float = 16.0
    k_factor_threshold: int = 30     # games_played before K drops
    scoring: Literal["payment_x_compliance", "weighted", "payment_only"] = "payment_x_compliance"

class TournamentResult(BaseModel):
    """Summary of a completed tournament."""
    id: str
    config: TournamentConfig
    rounds_completed: int
    total_games: int
    strategy_leaderboard: list[EloRating]  # sorted by rating desc
    profile_leaderboard: list[EloRating]   # sorted by rating desc (hardest first)
    started_at: datetime
    completed_at: datetime
    total_cost_usd: float
```

### New SQLite Tables

```sql
CREATE TABLE IF NOT EXISTS elo_ratings (
    entity_type TEXT NOT NULL,     -- 'strategy' or 'profile'
    entity_id   TEXT NOT NULL,
    rating      REAL NOT NULL DEFAULT 1500.0,
    games_played INTEGER NOT NULL DEFAULT 0,
    wins         INTEGER NOT NULL DEFAULT 0,
    losses       INTEGER NOT NULL DEFAULT 0,
    draws        INTEGER NOT NULL DEFAULT 0,
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS elo_history (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type    TEXT NOT NULL,
    entity_id      TEXT NOT NULL,
    opponent_id    TEXT NOT NULL,
    simulation_id  TEXT NOT NULL,
    tournament_id  TEXT,
    rating_before  REAL NOT NULL,
    rating_after   REAL NOT NULL,
    effective_score REAL NOT NULL,
    expected_score  REAL NOT NULL,
    timestamp      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tournaments (
    id              TEXT PRIMARY KEY,
    config_json     TEXT NOT NULL,
    rounds_completed INTEGER NOT NULL DEFAULT 0,
    total_games     INTEGER NOT NULL DEFAULT 0,
    started_at      TEXT NOT NULL,
    completed_at    TEXT,
    total_cost_usd  REAL NOT NULL DEFAULT 0.0
);
```

---

### CLI Interface

```bash
# Run a Swiss tournament (4 rounds, default settings)
collection-swarm tournament --format swiss --rounds 4

# Run a round-robin tournament (every strategy vs every profile)
collection-swarm tournament --format round_robin

# Show the current Elo leaderboard
collection-swarm tournament --leaderboard

# Show Elo history for a specific strategy
collection-swarm tournament --history empathetic_payment_plan

# Reset all Elo ratings to 1500
collection-swarm tournament --reset
```

---

### Web API Endpoints

```
GET  /api/arena/leaderboard              → { strategies: [...], profiles: [...] }
GET  /api/arena/leaderboard/strategies   → [{ entity_id, rating, games_played, ... }]
GET  /api/arena/leaderboard/profiles     → [{ entity_id, rating, games_played, ... }]
GET  /api/arena/history/{entity_id}      → [{ rating_before, rating_after, opponent_id, ... }]
POST /api/arena/tournaments              → Start a tournament (returns tournament_id)
GET  /api/arena/tournaments/{id}         → Tournament status and results
GET  /api/arena/tournaments/{id}/rounds  → Per-round pairings and outcomes
```

---

### What the Leaderboard Tells You (Concrete Example)

After a 4-round Swiss tournament with the existing 13 strategies × 15 profiles:

```
STRATEGY LEADERBOARD
Rank  Strategy                         Elo    Games  W-L-D
──────────────────────────────────────────────────────────
 1    liquidation_explainer           1587     12    9-2-1
 2    empathetic_payment_plan         1562     12    8-3-1
 3    problem_solving_callback        1548     12    7-4-1
 4    blocked_balance_hardship_plan   1531     12    7-5-0
 5    assertive_settlement            1519     12    6-5-1
 ...
12    whatsapp_self_service           1438     12    3-8-1
13    consignado_confirmation         1412     12    2-9-1

PROFILE LEADERBOARD (hardest debtors)
Rank  Profile                          Elo    Games  Resisted
────────────────────────────────────────────────────────────
 1    hostile_avoidant                1612     12    10
 2    scam_suspicious                 1589     12     9
 3    feirao_serial_renegotiator      1571     12     8
 ...
14    young_first_credit_card         1398     12     2
15    consignado_payroll_steady       1371     12     1
```

From this you immediately know:
- `liquidation_explainer` is the strongest strategy **after adjusting for opponent difficulty**.
- `hostile_avoidant` is genuinely the toughest debtor to collect from — not just by label, by empirical performance against all strategies.
- `consignado_confirmation` is weak — but it might still be the *correct* strategy for `consignado_payroll_steady` (which is easy). Elo tells you it's weak *in general*, while the per-matchup data tells you where it's appropriate.

---

### Relation to Future Options (B, C, D)

Option A is the **foundation** that every subsequent option builds on:

- **Option B (Strategy Evolution):** The Elo leaderboard tells the Evolver which strategies are top-K (mutate them) and bottom-K (fix them). Without Elo, the Evolver would use flat averages and make worse decisions.
- **Option C (Debtor Hardening):** Profile Elo tells the Hardener which debtors are already hard (don't waste effort) and which are too easy (harden them). The co-evolutionary loop needs Elo to balance the arms race.
- **Option D (Judge Calibration):** Elo stability metrics (rating variance over time) can detect when the Judge is noisy — if ratings swing wildly despite many games, the Judge is inconsistent. This triggers calibration.

---

## Option B — LLM-Driven Strategy Evolution (Genetic Prompts)

### Concept
Use the Judge's feedback to **generate new strategies** automatically. After a tournament round:

1. Take the **top-K** strategies by Elo.
2. Take the **bottom-K** strategies.
3. Prompt an LLM "Strategy Evolver" to:
   - **Mutate** top strategies (small variations: change tone, adjust a tactic).
   - **Crossover** two top strategies (combine the opening from one with the negotiation tactic of another).
   - **Analyze failures** of bottom strategies and propose targeted fixes.
4. Add the new strategies to the pool, run another tournament round.
5. **Cull** the weakest strategies each generation to keep the pool manageable.

### What Changes
| Component | Change |
|-----------|--------|
| New: `src/collection_swarm/evolution.py` | Strategy mutation, crossover, and generation via LLM calls |
| `models.py` | `Strategy` gets `generation: int`, `parent_ids: list[str]`, `mutation_type: str` fields |
| `config.py` | Support loading strategies from DB (evolved) in addition to YAML (seed) |
| `store.py` | New `strategy_pool` table for evolved strategies with lineage tracking |
| `arena.py` | Integration: after tournament round → evolve → next round |
| `cli.py` | New `evolve` command with `--generations`, `--population-size`, `--mutation-rate` |
| `web/` | Strategy genealogy tree visualization |

### AlphaGo Analogy
This is the equivalent of AlphaGo's **policy network improvement** — each generation of strategies is informed by the outcomes of the previous generation. The LLM acts as the "gradient update" by reading game results and proposing better moves.

### Complexity: Medium
- Requires a new "Evolver" LLM role with carefully designed prompts.
- The strategy space is **text**, not weights — evolution operates on YAML fields and natural-language descriptions.
- Risk: LLM-generated strategies might be incoherent. Mitigation: validate with Pydantic, gate with a minimum Elo threshold after evaluation.

### Example Evolver Prompt

```
You are a debt collection strategy designer. Below are the results of the latest
tournament round.

TOP STRATEGIES (high Elo):
{top_strategies_with_scores}

BOTTOM STRATEGIES (low Elo):
{bottom_strategies_with_scores}

FAILURE ANALYSIS — transcripts where bottom strategies failed:
{failure_excerpts}

Generate 3 new strategies by:
1. Mutating the best strategy with a small change (explain what you changed and why)
2. Crossing over the top two strategies (take the best element from each)
3. Fixing the most common failure pattern in bottom strategies

Output each strategy as a YAML block matching this schema: {strategy_schema}
```

---

## Option C — Adversarial Debtor Hardening (Red Team Loop)

### Concept
The debtor side also evolves. After each generation:

1. Identify which **debtor behaviors** most strategies fail against (high debtor Elo = hard to collect from).
2. Prompt a "Profile Evolver" LLM to create **harder debtor variants**:
   - Add new objections discovered from transcripts.
   - Tighten constraints (lower max payment, add new required actions).
   - Introduce new emotional states or backstory elements that make the debtor more resistant.
3. Run the evolved strategies against the hardened debtors.
4. Strategies that still perform well against hardened debtors are **robust**; others are exposed as brittle.

### What Changes
| Component | Change |
|-----------|--------|
| New: `src/collection_swarm/adversarial.py` | Debtor profile hardening, adversarial scenario generation |
| `evolution.py` | Extended to handle both strategy and profile evolution |
| `models.py` | `Profile` gets `generation`, `parent_id`, `hardening_type` |
| `store.py` | `profile_pool` table for evolved profiles |
| `arena.py` | Co-evolution loop: evolve strategies → harden debtors → repeat |
| `analysis/` | Robustness metrics: strategy performance vs debtor generation |

### AlphaGo Analogy
This is the core of AlphaGo's self-play: **both sides improve simultaneously**. A strategy that beats generation-5 debtors might fail against generation-6 debtors, forcing it to evolve further. This is the adversarial pressure that drives genuine improvement.

### Complexity: Medium-High
- The debtor evolution prompt must preserve profile coherence (a "cooperative hardship" debtor shouldn't suddenly become "hostile" without reason).
- Need to distinguish between "legitimately harder" and "unrealistically hard" — the Judge or a meta-evaluator should flag profiles that no real debtor would match.
- Introduces a co-evolutionary dynamic that could diverge (arms race to absurdity). Mitigation: anchor each generation to the seed profiles and cap drift.

### Co-Evolution Loop

```
┌──────────────────────────────────────────────────────────┐
│                    Generation N                           │
│                                                          │
│   Strategy Pool (gen N) ──► Tournament ◄── Profile Pool  │
│          │                    │                  │        │
│          ▼                    ▼                  ▼        │
│   Judge + Elo Update    Transcript Archive   Judge + Elo │
│          │                    │                  │        │
│          ▼                    ▼                  ▼        │
│   Evolve Strategies    Analyze Failures    Harden Profiles│
│          │                                      │        │
│          └──────────► Generation N+1 ◄──────────┘        │
└──────────────────────────────────────────────────────────┘
```

---

## Option D — Reward-Model Calibration (Judge Self-Improvement)

### Concept
The Judge is the "referee" — if it scores poorly, the whole system optimizes for the wrong thing. This option closes the loop on the Judge itself:

1. **Human calibration set:** Domain experts score ~50 transcripts manually. These become ground truth.
2. **Judge consistency check:** Run the Judge on the calibration set; measure correlation with human scores. If correlation is low, the Judge prompt or model is miscalibrated.
3. **Judge prompt evolution:** Use an LLM to iterate on the Judge's system prompt, optimizing for correlation with human scores (essentially, prompt-tuning the Judge).
4. **Multi-judge ensemble:** Run multiple Judge variants (different models, different prompts) and use agreement/disagreement to identify transcripts where scoring is uncertain.
5. **Adversarial Judge probing:** Generate edge-case transcripts designed to expose Judge inconsistencies (e.g., a compliant conversation that sounds aggressive, or a non-compliant one that sounds polite).

### What Changes
| Component | Change |
|-----------|--------|
| New: `src/collection_swarm/calibration.py` | Human-label loader, correlation metrics, judge prompt optimizer |
| `agents/judge.py` | Support multiple judge prompt variants, ensemble scoring |
| `store.py` | `calibration_labels` table, `judge_variants` table |
| `cli.py` | New `calibrate` command |
| `web/` | Judge calibration dashboard showing per-metric correlation |

### AlphaGo Analogy
AlphaGo had a **value network** that estimated game outcomes — it was trained on actual game results, not just heuristics. Similarly, calibrating the Judge against human ground truth makes the entire evaluation pipeline more trustworthy, which in turn makes strategy evolution more meaningful.

### Complexity: Medium
- Requires initial human labeling effort (~50 transcripts).
- The prompt optimization loop is lightweight (run judge on calibration set, compute correlation, mutate prompt, repeat).
- Multi-judge ensemble adds latency/cost but is architecturally simple.

---

## Option E — Full Self-Play with Strategy Embedding Space

### Concept
The most ambitious option. Instead of evolving strategies as text, **embed strategies in a continuous space** and use gradient-free optimization:

1. **Embed** each strategy's YAML fields into a vector using an embedding model.
2. **Map** Elo ratings to the embedding space — identify which regions of strategy-space are high-performing.
3. Use **CMA-ES** (Covariance Matrix Adaptation Evolution Strategy) or **Bayesian Optimization** to sample new strategy vectors from promising regions.
4. **Decode** vectors back to YAML strategies via an LLM ("Given this embedding and its neighbors, generate a coherent strategy").
5. Evaluate, update Elo, update the embedding landscape, repeat.

### What Changes
| Component | Change |
|-----------|--------|
| New: `src/collection_swarm/embedding.py` | Strategy embedding, similarity search, landscape visualization |
| New: `src/collection_swarm/optimizer.py` | CMA-ES or Bayesian optimization over strategy embeddings |
| `evolution.py` | Uses optimizer to propose new strategies instead of/alongside LLM mutation |
| `store.py` | `strategy_embeddings` table with vector storage |
| Dependencies | `numpy`, `scipy` (for CMA-ES), optionally `sentence-transformers` |

### AlphaGo Analogy
This is closest to AlphaGo's **Monte Carlo Tree Search + neural network** approach — instead of random exploration, the system learns which parts of the strategy space are worth exploring and focuses there.

### Complexity: High
- Requires an embedding model (adds a dependency).
- The embed → decode round-trip is lossy; decoded strategies might not be coherent.
- CMA-ES assumes a smooth landscape; the text → Elo mapping may be very noisy.
- Best suited as a refinement after Options A-C prove the basic loop works.

---

## Recommended Implementation Path

```
Phase 1: Option A — Elo Arena + Tournaments
   │  (2-3 modules, ~500 lines, no new LLM costs)
   │  Validates the competitive framing and matchmaking
   │
   ▼
Phase 2: Option B — Strategy Evolution
   │  (1 new module + prompts, ~400 lines, moderate LLM cost)
   │  The system starts generating novel strategies
   │
   ▼
Phase 3: Option C — Adversarial Debtor Hardening
   │  (1 new module, ~300 lines, moderate LLM cost)
   │  Both sides co-evolve; strategies become robust
   │
   ▼
Phase 4: Option D — Judge Calibration
   │  (1 module + data collection, ~400 lines)
   │  Ensures the scoring signal is trustworthy
   │
   ▼
Phase 5 (Optional): Option E — Embedding-Based Optimization
   (Research-grade; only if Phases 1-4 show the text-based
    evolution loop has plateaued)
```

---

## How Each Option Maps to AlphaGo's Architecture

| AlphaGo Component | Collection Swarm Equivalent | Option |
|---|---|---|
| **Game rules** | SimulationEngine turn loop + end conditions | Existing |
| **Elo rating system** | Elo-rated arena for strategies and profiles | A |
| **Self-play game generation** | Tournament scheduler + matchmaking | A |
| **Policy network (move selection)** | Collector strategy (prompt + params) | B |
| **Policy improvement (REINFORCE)** | LLM-based strategy evolution from game outcomes | B |
| **Opponent pool / league** | Evolved debtor profiles as adversaries | C |
| **Value network (position evaluation)** | Judge agent scoring transcripts | D |
| **Value network training** | Judge calibration against human labels | D |
| **MCTS (search)** | Embedding-space exploration of strategy landscape | E |

---

## Concrete Data Model Changes (Preview)

These are the key new models that would be introduced across Options A-C:

```python
class EloRating(BaseModel):
    entity_type: Literal["strategy", "profile"]
    entity_id: str
    rating: float = 1500.0
    games_played: int = 0
    rating_history: list[tuple[datetime, float]] = Field(default_factory=list)

class TournamentRound(BaseModel):
    id: str
    generation: int
    pairings: list[tuple[str, str]]  # (strategy_id, profile_id)
    results: list[str]  # simulation_result IDs
    started_at: datetime
    completed_at: datetime | None = None

class StrategyLineage(BaseModel):
    """Tracks how a strategy was created."""
    strategy_id: str
    generation: int
    parent_ids: list[str]
    mutation_type: Literal["seed", "mutate", "crossover", "fix"]
    mutation_description: str

class ProfileLineage(BaseModel):
    """Tracks how a debtor profile was hardened."""
    profile_id: str
    generation: int
    parent_id: str | None
    hardening_type: Literal["seed", "add_objection", "tighten_constraint", "new_backstory"]
    hardening_description: str
```

---

## Cost Considerations

| Option | Extra LLM Calls per Generation | Estimated Cost (100 strategies, 15 profiles) |
|--------|-------------------------------|----------------------------------------------|
| A (Elo Arena) | 0 (reuses existing simulation calls) | Same as current matrix runs |
| B (Strategy Evolution) | ~10-20 evolver calls per generation | +$0.50-2.00 per generation |
| C (Profile Hardening) | ~5-10 hardener calls per generation | +$0.25-1.00 per generation |
| D (Judge Calibration) | ~50 judge calls for calibration set | One-time ~$1.00 |
| E (Embedding Space) | ~20 embedding + decode calls | +$1.00-3.00 per generation |

The dominant cost remains the **simulation calls** themselves (Collector + Debtor + Judge per game), not the evolution/hardening overhead.

---

## Open Questions

1. **Convergence criteria:** When should evolution stop? Options: fixed generation count, Elo plateau detection, or a target win rate against seed debtors.
2. **Diversity preservation:** Pure Elo selection can collapse to a single dominant strategy. Should we enforce population diversity (e.g., niching, novelty search)?
3. **Compliance guardrails during evolution:** Evolved strategies must still pass compliance checks. Should non-compliant mutations be rejected outright, or penalized in Elo?
4. **Profile realism anchoring:** How far can evolved profiles drift from real debtor archetypes before they become unrealistic? Should each hardened profile be validated by the Judge for realism?
5. **Transferability:** Do evolved strategies transfer across LLM backends (e.g., a strategy evolved on GPT-4 might not work the same on Claude)?

---

## Next Steps

If the team wants to proceed, the recommended first step is **Option A (Elo Arena)**:

1. Add `EloRating` model and `elo_ratings` table to the store.
2. Build `arena.py` with Elo math and Swiss-system matchmaking.
3. Add `run_tournament()` to `runner.py`.
4. Wire up a `tournament` CLI command and basic web leaderboard.
5. Run a tournament with the existing 13 strategies × 15 profiles to validate.

This gives us the foundation (proper competitive rating, matchmaking, tournament infrastructure) that every subsequent option builds on — and it's implementable without any new LLM calls or dependencies.
