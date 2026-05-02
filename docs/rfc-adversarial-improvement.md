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

### What Changes
| Component | Change |
|-----------|--------|
| `models.py` | Add `EloRating` model; add `elo` field to `StrategyStats` |
| `store.py` | New `elo_ratings` table tracking rating history per entity |
| New: `src/collection_swarm/arena.py` | Tournament scheduler (Swiss / round-robin), Elo calculator, matchmaking |
| `runner.py` | New `run_tournament()` function that uses arena matchmaking instead of Cartesian matrix |
| `analysis/` | Elo-based leaderboards replace raw average rankings |
| `cli.py` | New `tournament` command |
| `web/` | Live Elo leaderboard page |

### AlphaGo Analogy
This is the equivalent of AlphaGo's **rating system** — it doesn't yet generate new players, but it properly measures who is strongest and pairs strong vs. strong to accelerate learning signal.

### Complexity: Low
- No new LLM calls beyond existing simulations.
- Elo math is deterministic (~50 lines).
- Biggest change is the tournament scheduler and matchmaking logic.

### Key Design Decisions

**Elo Calculation:** After each simulation, use the standard Elo formula:

```
E_a = 1 / (1 + 10^((R_b - R_a) / 400))
new_R_a = R_a + K * (S_a - E_a)
```

Where `S_a` (the "score") is derived from the Judge's `payment_probability` for the strategy side, and `1 - payment_probability` for the debtor side. K-factor starts at 32 for new entities, decays to 16 after 30 games.

**Matchmaking:** Swiss-system pairing — match entities with similar Elo to maximize information gain per game. This avoids wasting simulations on lopsided matchups.

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
