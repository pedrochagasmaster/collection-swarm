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

### Data Models

See implementation plan section 1.2 for the canonical Pydantic models
(`EloRating`, `EloUpdate`, `TournamentConfig`, `TournamentResult`) and
section 1.3 for the SQLite schema (`elo_ratings`, `elo_history`, `tournaments`).
They are the single source of truth for this feature.

---

### CLI Interface

```bash
# Run a Swiss tournament (4 rounds, default settings)
collection-swarm tournament --format swiss --rounds 4

# Run a round-robin tournament (every strategy vs every profile)
collection-swarm tournament --format round_robin

# Show the current Elo leaderboard (separate command)
collection-swarm leaderboard
collection-swarm leaderboard --type strategy
collection-swarm leaderboard --type profile

# Reset all Elo ratings to 1500 (separate command)
collection-swarm reset-elo
```

---

### Web API Endpoints

```
GET  /api/arena/leaderboard              → { strategies: [...], profiles: [...] }
                                           Query param: ?entity_type=strategy|profile (optional filter)
GET  /api/arena/history/{entity_id}      → [{ rating_before, rating_after, opponent_id, ... }]
POST /api/jobs/tournaments               → Start a tournament (returns WebRunJob snapshot, same as other jobs)
GET  /api/arena/tournaments              → List completed tournaments
GET  /api/arena/tournaments/{id}         → Single tournament result
```

Tournament progress is polled via the existing `GET /api/jobs/{job_id}` endpoint,
consistent with single-simulation and matrix jobs.

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
| `models.py` | New `StrategyLineage` and `EvolutionConfig` models (additive; `Strategy` is unchanged) |
| `store.py` | New `evolved_strategies` table; new methods `save_evolved_strategy`, `get_full_strategy_pool`, etc. |
| `runner.py` | New `run_evolution_cycle()` that runs tournament → evolve → cull → repeat |
| `cli.py` | New `evolve` command with `--generations`, `--population-size`, `--evolver-model` |
| `web/` | Strategy pool page, genealogy tree visualization, evolution job launcher |

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
| New: `src/collection_swarm/adversarial.py` | Debtor profile hardening, realism checks, drift anchoring |
| `models.py` | New `ProfileLineage` and `HardeningConfig` models (additive; `Profile` is unchanged) |
| `store.py` | New `evolved_profiles` table; methods mirror `evolved_strategies` |
| `runner.py` | `run_evolution_cycle` extended with optional `HardeningConfig` for co-evolution |
| `web/` | "Debtor Pool" tab added to Evolution page |

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

## Implementation Plan: Options A → B → C → D

The following plan is grounded in the actual codebase structure and accounts for
side effects, regressions, UI changes, and test coverage at every step.

---

### Phase 1: Option A — Elo Arena + Tournaments

#### 1.1 New File: `src/collection_swarm/arena.py`

Core module — pure functions, no IO or async. Contains:

- **`elo_expected(rating_a, rating_b) -> float`** — standard expected-score formula.
- **`elo_update(rating, expected, actual, k) -> float`** — single Elo update.
- **`effective_score(judgment, scoring="payment_x_compliance") -> float`** — converts `Judgment` to game score. When `scoring="payment_x_compliance"`: `payment_probability * compliance_score`. When `scoring="payment_only"`: `payment_probability` alone. Returns 0.0 if judgment is None.
- **`k_factor(games_played, initial=32, stable=16, threshold=30) -> float`** — K decay.
- **`update_ratings(strategy_rating, profile_rating, judgment) -> tuple[EloUpdate, EloUpdate]`** — computes both sides' updates from one game result. Each side uses its own `games_played` for K-factor calculation (a new strategy with 2 games uses K=32 even if the opponent profile has 50 games and uses K=16).
- **`swiss_pairings(strategy_ratings, profile_ratings, history) -> list[tuple[str, str]]`** — Swiss matchmaker. Sorts both pools by Elo descending, pairs #1 with #1, etc. Avoids repeat matchups within a tournament (uses `history` set of `(strategy_id, profile_id)` tuples). Falls back to next-available if all opponents at a rank have been played. When pools differ in size (e.g., 13 strategies, 15 profiles), the smaller pool limits pairings per round — the 2 leftover profiles get a bye (no game, no rating change). Unpaired entities are prioritized in the next round.
- **`round_robin_pairings(strategy_ids, profile_ids) -> list[tuple[str, str]]`** — Cartesian product (every strategy × every profile).

**Side effects / regressions:** None — pure functions. No existing code is modified.

**Tests:** `tests/test_arena.py`
- `test_elo_expected_equal_ratings` — both at 1500, expected = 0.5.
- `test_elo_expected_strong_vs_weak` — 1800 vs 1200, expected > 0.9.
- `test_elo_update_win` — winner gains, loser loses, sum is zero.
- `test_elo_update_draw` — equal ratings + 0.5 score → no movement.
- `test_effective_score_multiplies_payment_and_compliance` — 0.8 × 0.9 = 0.72.
- `test_effective_score_none_judgment` — returns 0.0.
- `test_k_factor_decay` — K=32 when games < 30, K=16 when ≥ 30.
- `test_swiss_pairings_pairs_by_rank` — top strategy gets top profile.
- `test_swiss_pairings_avoids_repeats` — second round skips already-played.
- `test_round_robin_pairings_covers_all` — len = strategies × profiles.

#### 1.2 Model Changes: `src/collection_swarm/models.py`

Add at end of file (after `model_dump_jsonable`):

```python
DRAW_THRESHOLD = 0.05  # effective_score within 0.5 ± this is a draw

class EloRating(BaseModel):
    entity_type: Literal["strategy", "profile"]
    entity_id: str
    rating: float = 1500.0
    games_played: int = 0
    wins: int = 0       # effective_score > 0.5 + DRAW_THRESHOLD
    losses: int = 0     # effective_score < 0.5 - DRAW_THRESHOLD
    draws: int = 0      # effective_score within 0.5 ± DRAW_THRESHOLD

class EloUpdate(BaseModel):
    entity_type: Literal["strategy", "profile"]
    entity_id: str
    opponent_id: str
    simulation_id: str
    rating_before: float
    rating_after: float
    effective_score: float
    expected_score: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TournamentConfig(BaseModel):
    format: Literal["round_robin", "swiss"] = "swiss"
    rounds: int = 4
    reps_per_pairing: int = 1
    k_factor_initial: float = 32.0
    k_factor_stable: float = 16.0
    k_factor_threshold: int = 30
    scoring: Literal["payment_x_compliance", "payment_only"] = "payment_x_compliance"
    # "payment_x_compliance": S = payment_probability * compliance_score (recommended)
    # "payment_only": S = payment_probability (ignores compliance — use only for debugging)

class TournamentResult(BaseModel):
    id: str = Field(default_factory=lambda: f"tourn_{uuid4().hex[:10]}")
    config: TournamentConfig
    rounds_completed: int = 0
    total_games: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    total_cost_usd: float = 0.0
```

**Side effects / regressions:**
- New models are purely additive. No existing model changes.
- `models.py` has `from __future__ import annotations` so forward references work.
- `Literal` is already imported. `uuid4`, `datetime`, `timezone` are already imported.
- `test_models.py` — check it still passes (it only tests `PaymentOutcome`, `ConstraintRule`).

**Tests:** `tests/test_models.py` — add tests for `EloRating` defaults, `TournamentConfig` validation.

#### 1.3 Store Changes: `src/collection_swarm/store.py`

Add inside `_init_schema()` after the `runs` table CREATE:

```sql
CREATE TABLE IF NOT EXISTS elo_ratings (...)
CREATE TABLE IF NOT EXISTS elo_history (...)
CREATE TABLE IF NOT EXISTS tournaments (...)
```

Add methods to `SimulationStore`:
- `get_elo_ratings(entity_type=None) -> list[EloRating]`
- `get_elo_rating(entity_type, entity_id) -> EloRating` (returns default 1500 if not found)
- `save_elo_update(update: EloUpdate, tournament_id: str | None) -> None`
- `save_tournament(result: TournamentResult) -> None`
- `get_tournament(tournament_id: str) -> TournamentResult`
- `list_tournaments() -> list[TournamentResult]`
- `get_elo_history(entity_id: str) -> list[EloUpdate]`
- `reset_elo_ratings() -> None` (DELETE FROM elo_ratings + elo_history)

**Side effects / regressions:**
- `_init_schema()` already uses `CREATE TABLE IF NOT EXISTS`, so adding more tables is safe for existing DBs.
- The new tables don't affect the existing `runs` table or any existing queries.
- `test_store.py` uses `tmp_path` for fresh DBs, so the schema additions are automatically tested.
- CRITICAL: The `save_elo_update` method must update both `elo_ratings` (upsert) and insert into `elo_history`. Use `INSERT OR REPLACE` for `elo_ratings` keyed on `(entity_type, entity_id)`.

**Tests:** `tests/test_store.py` — add:
- `test_elo_rating_defaults_to_1500`
- `test_save_and_read_elo_update`
- `test_elo_history_returns_chronological_updates`
- `test_reset_elo_ratings_clears_all`
- `test_save_and_read_tournament`

#### 1.4 Runner Changes: `src/collection_swarm/runner.py`

Add `run_tournament()` async function:

```python
async def run_tournament(
    config: AppConfig,
    store: SimulationStore,
    tournament_config: TournamentConfig,
    profile_ids: list[str] | None = None,
    strategy_ids: list[str] | None = None,
    conversation_model: str | None = None,
    judge_model: str | None = None,
    concurrency: int = 2,
    on_round_complete: Callable | None = None,
) -> TournamentResult:
```

Flow:
1. Resolve `conversation_model` and `judge_model` — if `None`, use `config.default_conversation_model` / `config.default_judge_model`. All games in a tournament use the same model pair for consistency (Elo ratings are only comparable when the underlying LLM is held constant).
2. Resolve `profile_ids` and `strategy_ids` — if `None`, use all from config. Validate each ID exists via `config.profile()` / `config.strategy()`.
3. Initialize Elo ratings for all strategies and profiles (load from store via `get_elo_rating()`, which returns default 1500 if not found).
4. For each round (1..`tournament_config.rounds`):
   a. Generate pairings via `arena.swiss_pairings()` or `arena.round_robin_pairings()`.
   b. For `reps_per_pairing` repetitions, convert each pairing `(strategy_id, profile_id)` to a `MatrixCell(strategy_id, profile_id, conversation_model, judge_model)`.
   c. Run all cells concurrently using `asyncio.gather` with `asyncio.Semaphore(concurrency)`, each cell creating a `SimulationEngine` via the existing `_make_engine` pattern.
   d. For each completed simulation with a `Judgment`, call `arena.update_ratings()` to compute `EloUpdate` pairs, then persist via `store.save_elo_update()` and `store.save_run()`.
   e. For failed simulations (no judgment), skip Elo update but still save the run.
   f. Call `on_round_complete` callback if provided (for web progress reporting).
5. Build final `TournamentResult` with leaderboards read from `store.get_elo_ratings()` and save via `store.save_tournament()`.

**Side effects / regressions:**
- `build_matrix` and `run_matrix` are unchanged. No regression on existing matrix runs.
- Existing `RunSummary` dataclass is unchanged.
- Import of `TournamentConfig`, `TournamentResult`, `EloRating`, `EloUpdate` from models.
- Import of `arena` functions.
- The `concurrency` semaphore pattern mirrors the existing `run_matrix` implementation.

**Tests:** `tests/test_runner.py` — add:
- `test_run_tournament_swiss_completes` — 2 strategies × 2 profiles × 2 rounds, scripted backend.
- `test_run_tournament_round_robin_completes`
- `test_run_tournament_updates_elo_ratings` — check ratings diverged from 1500 after tournament.
- `test_run_tournament_saves_results` — simulation results in store.

#### 1.5 CLI Changes: `src/collection_swarm/cli.py`

Add `tournament` command:

```python
@cli.command()
@click.option("--format", "tournament_format", type=click.Choice(["swiss", "round_robin"]), default="swiss")
@click.option("--rounds", default=4, type=int)
@click.option("--profiles", default=None)
@click.option("--strategies", default=None)
@click.option("--conversation-model", default=None)
@click.option("--judge-model", default=None)
@click.option("--concurrency", default=2, type=int)
@click.pass_context
def tournament(ctx, tournament_format, rounds, profiles, strategies, conversation_model, judge_model, concurrency):
```

Also add `leaderboard` command:

```python
@cli.command()
@click.option("--type", "entity_type", type=click.Choice(["strategy", "profile", "all"]), default="all")
@click.pass_context
def leaderboard(ctx, entity_type):
```

Also add `reset-elo` command:

```python
@cli.command("reset-elo")
@click.pass_context
def reset_elo(ctx):
```

**Side effects / regressions:**
- New Click commands don't affect existing commands.
- Need to import `TournamentConfig` from models and `run_tournament` from runner.
- The `_print_result` helper is unchanged.
- `test_cli.py` uses `CliRunner` — existing tests pass because new commands are additive.

**Tests:** `tests/test_cli.py` — add:
- `test_tournament_cli_swiss` — `CliRunner().invoke(cli, ["tournament", "--rounds", "1", ...])`.
- `test_leaderboard_cli` — runs after tournament produces output.
- `test_reset_elo_cli` — resets and confirms empty leaderboard.

#### 1.6 Web API Changes: `src/collection_swarm/web/app.py`

Add endpoints inside `create_app()`:

```python
# ── Arena / Tournament APIs ─────────────────────────────────────

@app.get("/api/arena/leaderboard")
def arena_leaderboard(entity_type: str | None = Query(None)):
    ...

@app.get("/api/arena/history/{entity_id}")
def arena_history(entity_id: str):
    ...

@app.post("/api/jobs/tournaments")
async def launch_tournament(payload: TournamentLaunchRequest):
    ...

@app.get("/api/arena/tournaments")
def list_tournaments():
    ...

@app.get("/api/arena/tournaments/{tournament_id}")
def get_tournament(tournament_id: str):
    ...
```

Add `TournamentLaunchRequest` Pydantic model near other request models:

```python
class TournamentLaunchRequest(BaseModel):
    format: str = "swiss"
    rounds: int = Field(default=4, ge=1, le=20)
    profile_ids: list[str] | None = None
    strategy_ids: list[str] | None = None
    conversation_model: str | None = None
    judge_model: str | None = None
    reps_per_pairing: int = Field(default=1, ge=1, le=10)
    concurrency: int = Field(default=2, ge=1, le=10)
```

**Side effects / regressions:**
- New endpoints don't conflict with any existing path prefix (`/api/arena/` is new).
- Job launching follows the exact same pattern as `_run_single_job` / `_run_matrix_job` with `WebRunJob` and `asyncio.create_task`.
- Need to add `kind="tournament"` to `WebRunJob` support.
- The `_run_tournament_job` background task saves results per round, same pattern as `_run_matrix_job`.
- Tournament progress is polled via existing `GET /api/jobs/{job_id}`.

**Tests:** `tests/test_web.py` — add `TestArena` class:
- `test_leaderboard_empty` — returns empty lists when no tournaments run.
- `test_launch_tournament_job` — launch + poll to completion.
- `test_leaderboard_after_tournament` — ratings exist after tournament.
- `test_arena_history` — returns chronological EloUpdates.

#### 1.7 Frontend: `static/index.html` + `static/app.js` + `static/styles.css`

**index.html:** Add sidebar nav button for "Arena" page in the "Analysis" section, after "Compliance" and before "Model Benchmarks":

```html
<button class="nav-link" data-page="arena" onclick="navigateTo('arena')">
  <svg ...><!-- trophy/crown icon --></svg>
  Arena
</button>
```

**app.js:** Add `case 'arena': await renderArena(); break;` to `renderPage` switch.

Add `renderArena()` function (~150 lines) that:
1. Fetches `GET /api/arena/leaderboard`.
2. Renders two leaderboard tables (strategies sorted by Elo desc, profiles sorted by Elo desc).
3. Each row shows: rank, entity_id, rating (with color-coded badge), games_played, W-L-D.
4. Click a row to expand Elo history chart (sparkline of rating over time, fetched from `/api/arena/history/{id}`).
5. "Launch Tournament" button at top that opens a config form (format, rounds, profile/strategy selection) and POSTs to `/api/jobs/tournaments`, then polls progress.

**styles.css:** Add leaderboard table styles reusing existing table patterns. Add rating badge styles (green > 1550, yellow 1450-1550, red < 1450). Add Elo sparkline styles.

**Side effects / regressions:**
- Adding a nav button to `index.html` shifts the sidebar. Verify all `data-page` attributes are unique.
- Adding a `case` to the `renderPage` switch requires the function to exist or the `default` case catches it.
- The `emptyState()` and `skeleton()` helpers are reused — no new global utilities needed.
- Mobile sidebar breakpoints already handle scrollable nav — additional items should work.
- `test_web.py TestSPA` tests `index_returns_html` — "Collection Swarm" in text still passes.

#### 1.8 Simulation YAML Changes: `config/simulation.yaml`

Add optional `arena` section:

```yaml
arena:
  default_format: swiss
  default_rounds: 4
  k_factor_initial: 32
  k_factor_stable: 16
  k_factor_threshold: 30
  scoring: payment_x_compliance
```

Add to `models.py`:

```python
class ArenaSettings(BaseModel):
    default_format: Literal["swiss", "round_robin"] = "swiss"
    default_rounds: int = Field(default=4, ge=1)
    k_factor_initial: float = 32.0
    k_factor_stable: float = 16.0
    k_factor_threshold: int = 30
    scoring: Literal["payment_x_compliance", "payment_only"] = "payment_x_compliance"
```

Update `SimulationSettings` in `models.py` — add field: `arena: ArenaSettings = Field(default_factory=ArenaSettings)`.

Update `load_simulation_settings` in `config.py` — add `"arena"` key parsing after `"objection_taxonomy"`, with `raw.get("arena", {})` passed to `ArenaSettings.model_validate()`.

**Side effects / regressions:**
- `ArenaSettings` has all defaults, so existing `simulation.yaml` files without `arena` section work unchanged. `SimulationSettings` uses a `default_factory` so the missing key produces valid defaults.
- `load_simulation_settings` currently accesses `conversation`, `matrix`, `compliance`, `objection_taxonomy`. Adding `arena` follows the same pattern.
- `test_config.py` calls `load_app_config("config")` with the existing `simulation.yaml` — passes because `ArenaSettings()` provides defaults.
- The `ArenaSettings` defaults are used by the `tournament` CLI command when no flags are provided, but `TournamentConfig` is the per-run config that can override them.

---

### Phase 2: Option B — LLM-Driven Strategy Evolution

#### 2.1 New File: `src/collection_swarm/evolution.py`

Core module. Contains:

- **`EvolutionConfig`** — Pydantic model with `population_size`, `mutation_rate`, `crossover_rate`, `cull_bottom_n`, `evolver_model_id`.
- **`StrategyLineage`** — tracks parent_ids, generation, mutation_type, mutation_description.
- **`evolve_strategies(top_strategies, bottom_strategies, failure_transcripts, config, router) -> list[Strategy]`** — async function that prompts an LLM "Evolver" with:
  - Top-K strategies and their Elo ratings.
  - Bottom-K strategies and their failure transcripts.
  - Asks for mutations, crossovers, and fixes.
  - Parses output as YAML, validates with `Strategy.model_validate()`.
  - Returns new `Strategy` objects with generated IDs using the pattern `evo_{generation}_{mutation_type}_{uuid4().hex[:6]}` (e.g., `evo_2_mutate_a3f1b2`). UUIDs prevent collisions across concurrent runs.
- **`cull_strategies(strategy_pool, elo_ratings, keep_n) -> list[Strategy]`** — removes lowest-Elo strategies, but never removes seed (generation 0) strategies.
- **`_build_evolver_prompt(top, bottom, transcripts) -> str`** — prompt engineering.
- **`_parse_evolved_strategies(llm_output) -> list[dict]`** — YAML extraction from LLM response.

**Side effects / regressions:**
- New file, no existing code modified.
- Uses `LLMRouter.complete()` for the Evolver call — same interface as agents.
- Evolved strategies need a model ID for the evolver. This must be a configured model (e.g., `cursor-composer-2` or an NIM model). Error if not configured.

**Risk: Incoherent strategies.** Mitigation:
- Validate every evolved strategy with `Strategy.model_validate()` — Pydantic rejects invalid shapes.
- Gate evolved strategies: they enter the pool with provisional Elo (1500) and must survive one tournament round to stay. Strategies that score below a minimum threshold after 5 games are auto-culled.
- Log all evolved strategies with their lineage for auditability.

**Tests:** `tests/test_evolution.py`
- `test_parse_evolved_strategies_valid_yaml` — mock LLM output → valid Strategy objects.
- `test_parse_evolved_strategies_rejects_garbage` — malformed output → empty list, no crash.
- `test_cull_strategies_preserves_seed` — generation-0 strategies never removed.
- `test_cull_strategies_removes_lowest_elo`
- Integration test with scripted backend: `test_evolve_strategies_produces_valid_output` — uses scripted backend returning canned YAML.

#### 2.2 Store Changes for Evolution

Add to `_init_schema()`:

```sql
CREATE TABLE IF NOT EXISTS evolved_strategies (
    id TEXT PRIMARY KEY,
    generation INTEGER NOT NULL DEFAULT 0,
    parent_ids_json TEXT,
    mutation_type TEXT,
    mutation_description TEXT,
    strategy_json TEXT NOT NULL,
    elo_rating REAL DEFAULT 1500.0,
    created_at TEXT NOT NULL,
    culled_at TEXT
);
```

Add methods:
- `save_evolved_strategy(strategy, lineage) -> None`
- `list_evolved_strategies(include_culled=False) -> list[tuple[Strategy, StrategyLineage]]`
- `cull_evolved_strategy(strategy_id) -> None`
- `get_full_strategy_pool(config) -> dict[str, Strategy]` — merges seed YAML strategies + non-culled evolved strategies.

**Side effects / regressions:**
- `AppConfig.strategies` currently returns only YAML-loaded strategies. The `get_full_strategy_pool` approach keeps config unchanged and merges at the runner level.
- `build_matrix` uses `config.strategies` directly — it's unchanged unless explicitly passed evolved strategy IDs.
- `run_tournament` will call `get_full_strategy_pool` to include evolved strategies in the tournament pool.
- **Regression risk:** `config.strategy(id)` will raise `KeyError` for evolved strategy IDs since they're not in YAML. Need to add a fallback that checks the store. This modifies `AppConfig` or (better) the tournament runner bypasses `config.strategy()` and loads from store directly.

#### 2.3 Runner Changes for Evolution

Add `run_evolution_cycle()`:

```python
async def run_evolution_cycle(
    config: AppConfig,
    store: SimulationStore,
    evolution_config: EvolutionConfig,
    tournament_config: TournamentConfig,
    generations: int = 5,
    concurrency: int = 2,
    on_generation_complete: Callable | None = None,
) -> list[TournamentResult]:
```

Flow per generation:
1. Load current strategy pool (seed + survived evolved).
2. Run a tournament (reuse `run_tournament`).
3. Read Elo leaderboard. Extract top-K and bottom-K.
4. Fetch failure transcripts for bottom-K from store.
5. Call `evolve_strategies()` to generate new candidates.
6. Save new strategies to `evolved_strategies` table.
7. Cull bottom-N strategies (never cull seed).
8. Repeat.

#### 2.4 CLI for Evolution

```python
@cli.command("evolve")
@click.option("--generations", default=5, type=int)
@click.option("--population-size", default=20, type=int)
@click.option("--evolver-model", default=None, help="Model ID for the strategy evolver LLM.")
@click.option("--tournament-rounds", default=4, type=int)
@click.option("--concurrency", default=2, type=int)
@click.pass_context
def evolve(ctx, generations, population_size, evolver_model, tournament_rounds, concurrency):
```

#### 2.5 Web API for Evolution

```
POST /api/jobs/evolution       → Launch evolution cycle
GET  /api/evolution/pool       → Current strategy pool (seed + evolved, with Elo and lineage)
GET  /api/evolution/genealogy  → Strategy family tree (parent_ids → children)
```

#### 2.6 Frontend for Evolution

Add "Evolution" page to sidebar (in Analysis section). Renders:
- **Strategy Pool Table:** All strategies (seed marked with badge, evolved with generation number), sorted by Elo.
- **Genealogy Tree:** Visual representation of strategy lineage (parent → children). CSS-only tree using indentation and connecting lines.
- **Launch Evolution Button:** Config form (generations, population size, evolver model dropdown). POSTs to `/api/jobs/evolution`, polls progress like matrix jobs.
- **Generation Timeline:** Shows which strategies were created/culled each generation.

**Side effects / regressions:**
- `renderPage` switch gets a new `case 'evolution'`.
- Sidebar gets another nav button — verify mobile scroll still works with 12+ items.
- Evolution jobs use `WebRunJob` with `kind="evolution"` — the job snapshot format is compatible.
- **CRITICAL:** Evolved strategies stored in SQLite are NOT in `config/collector_strategies.yaml`. Any code path that calls `config.strategy(id)` with an evolved ID will fail. Audit all callers:
  - `engine.py` `run_simulation()` receives `Strategy` object directly — SAFE.
  - `runner.py` `run_cell()` calls `config.strategy(cell.strategy_id)` — NEEDS FIX for evolved strategies.
  - `web/app.py` `_run_single_job` calls `config.strategy()` — NEEDS FIX.
  - `web/app.py` compliance/playbook/dashboard endpoints use `config.strategies` dict — need to merge evolved strategies.
  
  **Fix approach — `EntityResolver` helper (added to `store.py`):**

  ```python
  class EntityResolver:
      """Resolves strategies and profiles from YAML config + evolved entities in DB."""
      def __init__(self, config: AppConfig, store: SimulationStore) -> None:
          self._config = config
          self._store = store

      def strategy(self, strategy_id: str) -> Strategy:
          try:
              return self._config.strategy(strategy_id)
          except KeyError:
              evolved = self._store.get_evolved_strategy(strategy_id)
              if evolved is None:
                  raise KeyError(f"unknown strategy '{strategy_id}'")
              return evolved

      def profile(self, profile_id: str) -> Profile:
          try:
              return self._config.profile(profile_id)
          except KeyError:
              evolved = self._store.get_evolved_profile(profile_id)
              if evolved is None:
                  raise KeyError(f"unknown profile '{profile_id}'")
              return evolved

      def all_strategies(self) -> dict[str, Strategy]:
          return {**self._config.strategies, **self._store.get_evolved_strategy_pool()}

      def all_profiles(self) -> dict[str, Profile]:
          return {**self._config.profiles, **self._store.get_evolved_profile_pool()}
  ```

  All callers that currently call `config.strategy(id)` or `config.profile(id)` should be updated to use `EntityResolver` when evolved entities are in play (Phase 2+). Phase 1 does not need this — all entities come from YAML config.

---

### Phase 3: Option C — Adversarial Debtor Hardening

#### 3.1 New File: `src/collection_swarm/adversarial.py`

- **`HardeningConfig`** — `hardener_model_id`, `max_drift` (max Elo distance from seed), `realism_check` (bool).
- **`ProfileLineage`** — tracks parent_id, generation, hardening_type, description.
- **`harden_profiles(easy_profiles, winning_transcripts, config, router) -> list[Profile]`** — async function that prompts an LLM "Hardener" to:
  - Analyze transcripts where the strategy won easily.
  - Propose tougher debtor variants: new objections, tighter constraints, modified backstories.
  - Preserve core archetype (a `cooperative` debtor stays cooperative, just harder).
  - Output as YAML, validated with `Profile.model_validate()`.
- **`check_realism(profile, router, model_id) -> float`** — asks Judge-role LLM "Is this debtor profile realistic? Score 0-1." Rejects profiles below threshold.
- **`_build_hardener_prompt(profiles, transcripts) -> str`**

**Side effects / regressions:**
- Same pattern as `evolution.py` — new file, uses `LLMRouter.complete()`.
- Hardened profiles stored in DB, same `KeyError` issue as evolved strategies.
- **Constraint coherence risk:** A hardened profile might have `max_payment: 10` which is below any realistic amount. Mitigation: validate constraints against `debt_amount` (max_payment should be ≥ 1% of debt).
- **Arms race divergence risk:** Debtors get unrealistically hard, strategies get unrealistically aggressive. Mitigation: anchor drift — each hardened profile's Elo cannot exceed seed Elo + `max_drift`. If it does, stop hardening that lineage.

**Tests:** `tests/test_adversarial.py`
- `test_harden_profiles_preserves_archetype`
- `test_harden_profiles_adds_constraint`
- `test_check_realism_rejects_absurd_profile`
- `test_hardened_profile_validates_with_pydantic`

#### 3.2 Store Changes for Hardened Profiles

```sql
CREATE TABLE IF NOT EXISTS evolved_profiles (
    id TEXT PRIMARY KEY,
    generation INTEGER NOT NULL DEFAULT 0,
    parent_id TEXT,
    hardening_type TEXT,
    hardening_description TEXT,
    profile_json TEXT NOT NULL,
    elo_rating REAL DEFAULT 1500.0,
    created_at TEXT NOT NULL,
    culled_at TEXT
);
```

Methods mirror `evolved_strategies`: `save_evolved_profile`, `list_evolved_profiles`, `cull_evolved_profile`, `get_full_profile_pool`.

#### 3.3 Co-Evolution Runner

Modify `run_evolution_cycle` to accept an optional `HardeningConfig`. When provided:
1. After each tournament, evolve strategies AND harden profiles.
2. Both pools grow; both get culled.
3. The next tournament uses both expanded pools.

**Side effects / regressions:**
- `run_evolution_cycle` signature changes (new optional param). Existing callers pass `None` → behavior unchanged.
- Same `config.profile(id)` KeyError issue as with evolved strategies. Same fix: `ProfileResolver` or store fallback.
- **Dashboard regression:** `GET /api/dashboard` returns `profiles: list(config.profiles.keys())`. Evolved profiles won't appear unless we merge. Same for `strategies`. The dashboard endpoint must be updated to include evolved entities.

#### 3.4 Web API and Frontend for Hardening

- Extend `/api/evolution/pool` to include profiles.
- Add "Debtor Pool" tab to the Evolution page showing hardened profiles with lineage.
- Add toggle to Evolution launch form: "Enable debtor hardening" checkbox.

---

### Phase 4: Option D — Judge Calibration

#### 4.1 New File: `src/collection_swarm/calibration.py`

- **`CalibrationLabel`** — Pydantic model: `transcript_id` (must match a `SimulationResult.id` in the store), `human_scores: dict[str, float]` (keys are Judge metric names: `payment_probability`, `compliance_score`, `debtor_satisfaction`, `rapport_built`, `escalation_risk` — all 0.0–1.0), `labeler_id: str`, `timestamp: datetime`.
- **`CalibrationResult`** — per-metric Pearson correlation (`dict[str, float]`), per-metric MAE (`dict[str, float]`), and overall calibration score (mean of per-metric correlations).
- **`load_calibration_labels(path) -> list[CalibrationLabel]`** — load from JSON file. Expected format:
  ```json
  [
    {
      "transcript_id": "sim_abc123",
      "human_scores": { "payment_probability": 0.7, "compliance_score": 0.9, ... },
      "labeler_id": "analyst_maria",
      "timestamp": "2026-05-01T12:00:00Z"
    }
  ]
  ```
  Raises `FileNotFoundError` if path doesn't exist. Raises `ValidationError` if any label fails Pydantic validation.
- **`evaluate_judge(labels, store) -> CalibrationResult`** — for each labeled transcript, compare Judge's stored `Judgment` scores against human labels. Compute per-metric correlation.
- **`optimize_judge_prompt(labels, config, router, iterations=10) -> tuple[str, CalibrationResult]`** — LLM-driven prompt optimization loop:
  1. Run Judge on calibration set with current prompt.
  2. Compute correlation.
  3. Ask an "Optimizer" LLM to suggest prompt improvements based on where the Judge disagrees with humans.
  4. Test improved prompt.
  5. Keep the prompt with highest correlation.
  6. Repeat for N iterations.

**Side effects / regressions:**
- The Judge prompt lives in `config/prompts.yaml` under `judge.system` and `judge.transcript`. `optimize_judge_prompt` returns a new prompt string but does NOT modify the YAML file. The caller decides whether to save it.
- **CRITICAL:** If the optimized prompt is auto-saved to YAML, ALL subsequent simulations use the new prompt. This changes Judge behavior, which changes all Elo ratings. Recommendation: store optimized prompts in a `judge_prompt_variants` table and allow selecting which variant to use per tournament/simulation.
- No regression on existing Judge code — `judge.py` is unchanged.

#### 4.2 Store Changes for Calibration

```sql
CREATE TABLE IF NOT EXISTS calibration_labels (
    transcript_id TEXT NOT NULL,
    metric TEXT NOT NULL,
    human_score REAL NOT NULL,
    labeler_id TEXT,
    labeled_at TEXT NOT NULL,
    PRIMARY KEY (transcript_id, metric, labeler_id)
);

CREATE TABLE IF NOT EXISTS judge_prompt_variants (
    id TEXT PRIMARY KEY,
    system_prompt TEXT NOT NULL,
    transcript_prompt TEXT NOT NULL,
    calibration_score REAL,
    created_at TEXT NOT NULL
);
```

#### 4.3 CLI for Calibration

```python
@cli.command("calibrate")
@click.option("--labels", type=click.Path(path_type=Path), required=True, help="Path to calibration labels JSON.")
@click.option("--optimize", is_flag=True, help="Run LLM-driven prompt optimization.")
@click.option("--iterations", default=10, type=int)
@click.pass_context
def calibrate(ctx, labels, optimize, iterations):
```

#### 4.4 Web API for Calibration

```
POST /api/calibration/labels     → Upload calibration labels (JSON body)
GET  /api/calibration/results    → Current calibration metrics (per-metric correlation)
POST /api/jobs/calibration       → Launch prompt optimization
GET  /api/calibration/variants   → List judge prompt variants with scores
```

#### 4.5 Frontend for Calibration

Add "Calibration" page to sidebar (in Analysis section). Renders:
- **Calibration Dashboard:** Per-metric correlation bars (green > 0.8, yellow 0.5-0.8, red < 0.5).
- **Upload Labels:** File input + JSON paste area for calibration labels.
- **Prompt Variants Table:** All judge prompt variants with their calibration scores. Active variant highlighted.
- **Launch Optimization Button:** Starts prompt optimization job.

---

### Cross-Cutting Concerns

#### Database Migration Safety

All new tables use `CREATE TABLE IF NOT EXISTS`. Existing databases get new tables on first access. No ALTER TABLE on `runs`. Zero-downtime upgrade.

#### Config Backward Compatibility

All new config sections (`arena`, `evolution`, `adversarial`, `calibration`) are optional with full defaults. Existing `simulation.yaml` files work unchanged. `SimulationSettings` uses `Field(default_factory=...)` or `| None = None` for new fields.

#### Import Graph

```
arena.py      → models.py (EloRating, EloUpdate, Judgment)
evolution.py  → models.py (Strategy, StrategyLineage), backends/router.py
adversarial.py → models.py (Profile, ProfileLineage), backends/router.py
calibration.py → models.py (Judgment, CalibrationLabel), store.py, backends/router.py
runner.py     → arena.py, evolution.py, adversarial.py (optional imports)
```

No circular imports. `arena.py` has zero IO dependencies (pure functions). `evolution.py` and `adversarial.py` depend on `LLMRouter` but not on each other.

#### Test Isolation

All tests use `tmp_path` for databases. No test depends on external LLM services — scripted/heuristic backends are used. Evolution and adversarial tests mock `LLMRouter.complete()` to return canned YAML. Calibration tests use synthetic labels.

#### Existing Test Regression Checklist

| Test File | Risk | Mitigation |
|-----------|------|------------|
| `test_models.py` | New model imports could shadow | New models are at end of file, no name conflicts |
| `test_engine.py` | None — engine unchanged | No risk |
| `test_store.py` | New `_init_schema()` tables | `CREATE IF NOT EXISTS` — safe |
| `test_runner.py` | `build_matrix` unchanged | No risk |
| `test_web.py` | New endpoints added | Existing endpoint paths unchanged |
| `test_cli.py` | New commands added | Existing commands unchanged |
| `test_judge.py` | Judge unchanged | No risk |
| `test_config.py` | New optional config sections | Defaults cover missing YAML keys |
| `test_playbook.py` | Playbook uses `compare_strategies` | Strategy rankings unchanged |
| `test_cursor_sdk_backend.py` | Backend unchanged | No risk |
| `test_model_evaluation.py` | Model eval unchanged | No risk |
| `test_env.py` | Env loading unchanged | No risk |

#### UI Regression Checklist

| Area | Risk | Mitigation |
|------|------|------------|
| Sidebar nav | New buttons push existing items down | Verify mobile scroll handles 12+ nav items |
| `renderPage` switch | New cases must have matching functions | Add functions before adding cases |
| Dashboard | Must still work with 0 tournaments | Leaderboard widget shows "No tournaments yet" |
| Runs list | Unchanged — tournament sims appear as regular runs | Tournament runs have same schema as matrix runs |
| Playbook | Uses existing strategy rankings | Evolved strategies appear in rankings only if they have completed runs |
| Compliance | Uses `config.strategies` loop | Must merge evolved strategies into the loop or compliance misses them |
| Benchmarks | Unchanged | No risk |
| Manual sessions | Unchanged | Evolved strategies must be selectable in the dropdown — add to `run-options` endpoint |
| Launch Run | Uses `run-options` for dropdowns | Must include evolved strategies/profiles or users can't launch simulations with them |
| `run-options` endpoint | Returns `config.profiles` and `config.strategies` only | Must merge evolved entities from store (Phase 2+) |

#### Cost Guardrails

- Tournament simulations use the same models as matrix runs — no additional per-simulation cost.
- Evolution LLM calls (Phase 2) use a configurable model — can use a cheap model (scripted for testing, small model for production).
- Hardening LLM calls (Phase 3) same approach.
- Calibration optimization (Phase 4) is bounded by `--iterations` flag.
- All phases log estimated cost via existing `estimated_cost_usd` tracking.

#### Observability

- All tournament rounds are persisted with timestamps — enables post-hoc analysis of Elo convergence.
- Evolution lineage is fully tracked — can reconstruct the genealogy of any evolved strategy.
- Calibration results are stored with prompt variants — can compare Judge accuracy over time.
