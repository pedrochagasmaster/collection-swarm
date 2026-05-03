# Data Flow

This document traces data through every major workflow in Collection Swarm — from a single simulation through batch matrix runs, competitive tournaments, evolutionary cycles, and the analysis pipeline.

---

## Single Simulation Lifecycle

A single simulation is the atomic unit of the system. Every higher-level workflow (matrix, tournament, evolution) ultimately calls `SimulationEngine.run_simulation()`.

```mermaid
sequenceDiagram
    participant Caller as CLI / Runner / Web
    participant Config as AppConfig
    participant Engine as SimulationEngine
    participant Collector as CollectorAgent
    participant Debtor as DebtorAgent
    participant Judge
    participant Router as LLMRouter
    participant Backend as LLMBackend
    participant Store as SimulationStore

    Caller->>Config: load_app_config(config_dir)
    Note over Config: Loads YAML:<br/>profiles, strategies,<br/>models, prompts,<br/>simulation settings

    Caller->>Router: LLMRouter(models, cursor_sdk_prompts)
    Caller->>Engine: SimulationEngine(collector, debtor, judge, settings)
    Caller->>Engine: run_simulation(profile, strategy)

    Note over Engine: Create SimulationResult<br/>status="running"

    rect rgb(240, 248, 255)
        Note over Engine,Backend: Conversation Loop (up to max_turns)

        Engine->>Collector: generate_turn(strategy, account_data, transcript)
        Note over Collector: Build system prompt:<br/>strategy fields + account data
        Note over Collector: Build user prompt:<br/>conversation history
        Collector->>Router: complete(model_id, [system, user])
        Router->>Backend: complete(model_config, messages)
        Backend-->>Router: LLMResponse(content, tokens, cost)
        Router-->>Collector: LLMResponse
        Collector-->>Engine: LLMResponse

        Note over Engine: Strip end signal<br/>Append Message(role="collector")<br/>Accumulate tokens + cost

        alt Collector sent [END_CONVERSATION]
            Note over Engine: ended_by = COLLECTOR → exit loop
        end

        Engine->>Debtor: generate_turn(profile, transcript)
        Note over Debtor: Build system prompt:<br/>profile fields + constraints
        Note over Debtor: Map history to<br/>user/assistant messages
        Debtor->>Router: complete(model_id, messages)
        Router->>Backend: complete(model_config, messages)
        Backend-->>Router: LLMResponse
        Router-->>Debtor: LLMResponse
        Debtor-->>Engine: LLMResponse

        Note over Engine: Strip end signal<br/>Append Message(role="debtor")<br/>Accumulate tokens + cost

        alt Debtor sent [END_CONVERSATION]
            Note over Engine: ended_by = DEBTOR → exit loop
        end

        alt Stalemate detected
            Note over Engine: SequenceMatcher similarity<br/>≥ threshold over window<br/>ended_by = STALEMATE → exit loop
        end
    end

    alt No explicit end
        Note over Engine: ended_by = TURN_LIMIT
    end

    Engine->>Judge: evaluate(transcript, profile)
    Note over Judge: Build system + transcript prompts<br/>with account data and constraints
    Judge->>Router: complete(model_id, [system, user])
    Router->>Backend: complete(model_config, messages)
    Backend-->>Judge: LLMResponse (JSON)

    Note over Judge: Parse JSON → Judgment<br/>Normalize outcome aliases<br/>Scale scores (100→1.0 or 10→1.0)<br/>Run deterministic constraint checks<br/>Merge violations

    Judge-->>Engine: Judgment

    Note over Engine: Finalize SimulationResult:<br/>turn_count, judgment,<br/>ended_at, token totals

    Engine-->>Caller: SimulationResult
    Caller->>Store: save_run(result)
```

### End Conditions

The conversation loop terminates under four conditions:

| Condition | `ended_by` Value | Detection |
|---|---|---|
| Collector includes `[END_CONVERSATION]` | `collector` | String search in response content |
| Debtor includes `[END_CONVERSATION]` | `debtor` | String search in response content |
| Consecutive turns are too similar | `stalemate` | `SequenceMatcher.ratio() ≥ threshold` over a sliding window of pair-wise turns |
| Turn count reaches `max_turns` | `turn_limit` | Simple counter check |

### Token & Cost Tracking

Every `LLMResponse` carries `input_tokens`, `output_tokens`, and `estimated_cost_usd`. The engine accumulates these across all collector turns, debtor turns, and the judge evaluation into `SimulationResult.total_input_tokens`, `total_output_tokens`, and `estimated_cost_usd`.

---

## Batch / Matrix Run Flow

The matrix run executes the **Cartesian product** of selected profiles, strategies, conversation models, and judge models — optionally repeated.

```mermaid
flowchart TB
    START(["CLI: collection-swarm run"]) --> CONFIG["Load AppConfig"]
    CONFIG --> MATRIX["build_matrix()<br/><small>profiles × strategies × conv_models × judge_models × reps</small>"]
    MATRIX --> CELLS["List[MatrixCell]<br/><small>Each cell = one simulation</small>"]
    CELLS --> SEMAPHORE["asyncio.Semaphore(concurrency)"]

    SEMAPHORE --> GATHER["asyncio.gather(*tasks)"]

    subgraph Parallel["Concurrent Execution"]
        GATHER --> CELL1["run_cell(cell₁)"]
        GATHER --> CELL2["run_cell(cell₂)"]
        GATHER --> CELLN["run_cell(cellₙ)"]
    end

    CELL1 --> SIM1["SimulationEngine.run_simulation()"]
    CELL2 --> SIM2["SimulationEngine.run_simulation()"]
    CELLN --> SIMN["SimulationEngine.run_simulation()"]

    SIM1 --> RESULTS["List[SimulationResult]"]
    SIM2 --> RESULTS
    SIMN --> RESULTS

    RESULTS --> SAVE["store.save_runs(results)"]
    SAVE --> SUMMARY["RunSummary<br/><small>completed, failed, total</small>"]
```

### MatrixCell

Each `MatrixCell` is a frozen, hashable tuple of:

```
(profile_id, strategy_id, conversation_model, judge_model)
```

This makes cells suitable as dictionary keys for coverage tracking and backfill detection.

!!! info "Backfill Support"
    The store provides `get_backfill_needed(target_reps, cells)` to identify matrix cells that have fewer completed runs than the target repetition count, enabling incremental matrix completion.

---

## Tournament Flow

Tournaments use **Elo ratings** to competitively rank strategies against profiles over multiple rounds.

```mermaid
flowchart TB
    START(["CLI: collection-swarm tournament"]) --> CONFIG["Load AppConfig"]
    CONFIG --> TCONFIG["TournamentConfig<br/><small>format, rounds, reps_per_pairing,<br/>k_factor, scoring</small>"]
    TCONFIG --> INIT["Initialize TournamentResult<br/>Load strategy + profile pools<br/><small>(config + evolved)</small>"]

    INIT --> ROUND_LOOP

    subgraph ROUND_LOOP["For each round (1..rounds)"]
        RATINGS["Fetch current Elo ratings<br/><small>store.get_elo_rating()</small>"]
        RATINGS --> PAIR_TYPE{Format?}

        PAIR_TYPE -->|Swiss| SWISS["swiss_pairings()<br/><small>Sort by games_played + rating<br/>Backtrack to avoid repeats</small>"]
        PAIR_TYPE -->|Round Robin| RR["round_robin_pairings()<br/><small>Full Cartesian product</small>"]

        SWISS --> PAIRINGS["List[(strategy_id, profile_id)]"]
        RR --> PAIRINGS

        PAIRINGS --> EXPAND["Expand by reps_per_pairing<br/>→ List[MatrixCell]"]
        EXPAND --> RUN["asyncio.gather: run each cell"]
        RUN --> SAVE_RUNS["store.save_runs()"]
        SAVE_RUNS --> ELO_UPDATE

        subgraph ELO_UPDATE["Elo Update per Simulation"]
            SCORE["effective_score(judgment, scoring)<br/><small>payment_prob × compliance or payment_only</small>"]
            SCORE --> EXPECTED["elo_expected(rating_a, rating_b)<br/><small>1 / (1 + 10^((Rb-Ra)/400))</small>"]
            EXPECTED --> NEW_RATING["elo_update(rating, expected, actual, k)<br/><small>R' = R + K × (S - E)</small>"]
            NEW_RATING --> PERSIST["store.save_elo_update()"]
        end
    end

    ROUND_LOOP --> FINALIZE["result.completed_at = utc_now()<br/>store.save_tournament(result)"]
    FINALIZE --> DONE(["TournamentResult<br/><small>id, rounds_completed, total_games, cost</small>"])
```

### Swiss Pairing Algorithm

Swiss pairings prevent repeat matchups and balance play:

1. **Sort strategies** by `(games_played ascending, rating descending)` — under-played strategies get priority.
2. **Sort profiles** with a bye priority — profiles with zero games are matched first.
3. **Backtracking search** attempts to find a perfect assignment where no `(strategy, profile)` pair repeats from `history`.
4. **Fallback**: if no repeat-free assignment exists, greedy matching selects the best available profile per strategy.

### Elo Rating System

| Parameter | Default | Purpose |
|---|---|---|
| `k_factor_initial` | 32.0 | Rating volatility for entities with < `threshold` games |
| `k_factor_stable` | 16.0 | Rating volatility for established entities |
| `k_factor_threshold` | 30 | Games played before switching to stable K |
| `scoring` | `payment_x_compliance` | Score formula: `payment_probability × compliance_score` |

Strategies **win** when their effective score > 0.55 (above the draw threshold). Profiles win when strategies score below 0.45.

---

## Evolution Cycle Flow

The evolution cycle alternates between **tournament evaluation** and **LLM-driven strategy mutation**, with optional **profile hardening**.

```mermaid
flowchart TB
    START(["CLI: collection-swarm evolve"]) --> CONFIG["Load AppConfig + EvolutionConfig"]
    CONFIG --> INIT["Initialize active_strategy_ids<br/>Initialize active_profile_ids"]

    INIT --> GEN_LOOP

    subgraph GEN_LOOP["For each generation (1..generations)"]
        TOURNAMENT["run_tournament()<br/><small>Evaluate current population</small>"]
        TOURNAMENT --> RANK["Sort strategies by Elo rating"]

        RANK --> SELECT_TOP["Select top_k strategies<br/><small>Best performers</small>"]
        RANK --> SELECT_BOTTOM["Select bottom_k strategies<br/><small>Worst performers</small>"]

        SELECT_TOP --> TRANSCRIPTS["Load failure transcripts<br/><small>From bottom strategy runs</small>"]
        SELECT_BOTTOM --> TRANSCRIPTS

        TRANSCRIPTS --> EVOLVE["evolve_strategies()<br/><small>LLM generates improved YAML</small>"]

        EVOLVE --> PARSE["Parse YAML → Strategy objects<br/><small>Fallback: clone top strategy</small>"]

        PARSE --> SAVE_EVOLVED["store.save_evolved_strategy()<br/><small>With StrategyLineage</small>"]
        SAVE_EVOLVED --> UPDATE_POOL["Add evolved IDs to<br/>active_strategy_ids"]

        UPDATE_POOL --> CULL_CHECK{cull_bottom_n > 0?}
        CULL_CHECK -->|Yes| CULL["cull_strategies()<br/><small>Keep seeds + top evolved<br/>up to population_size</small>"]
        CULL --> REMOVE["store.cull_evolved_strategy()<br/><small>Set culled_at timestamp</small>"]
        CULL_CHECK -->|No| HARDEN_CHECK

        REMOVE --> HARDEN_CHECK{hardening enabled?}
        HARDEN_CHECK -->|Yes| HARDEN["harden_profiles()<br/><small>LLM generates harder variants</small>"]
        HARDEN --> SAVE_PROFILES["store.save_evolved_profile()<br/><small>With ProfileLineage</small>"]
        SAVE_PROFILES --> ADD_PROFILES["Add hardened IDs to<br/>active_profile_ids"]
        HARDEN_CHECK -->|No| NEXT_GEN
        ADD_PROFILES --> NEXT_GEN["Next generation"]
    end

    GEN_LOOP --> DONE(["List[TournamentResult]<br/><small>One per generation</small>"])
```

### Strategy Evolution

The evolver LLM receives:

- **Top strategies** — high Elo performers (YAML dump)
- **Bottom strategies** — low Elo performers (YAML dump)
- **Failure transcripts** — up to 5 transcripts from bottom-strategy runs

It produces new strategies as YAML under a `strategies:` key. Each evolved strategy gets:

- A unique `evo_{gen}_mutate_{hash}` ID
- A `StrategyLineage` record tracking parent IDs, generation, and mutation type

!!! note "Fallback"
    If the LLM fails to produce valid YAML, the system clones the top strategy as a deterministic fallback mutation.

### Strategy Culling

The `cull_strategies()` function preserves:

1. **All seed strategies** — original config-defined strategies are never culled.
2. **Top evolved strategies** — sorted by Elo rating, kept up to `population_size - len(seeds)`.

Culled strategies receive a `culled_at` timestamp and are excluded from future tournament pools.

### Profile Hardening

When enabled, the hardener LLM creates more challenging debtor profiles:

- Input: easy profiles (from bottom-k in Elo) + winning transcripts
- Output: harder profile variants with tighter constraints
- Fallback: adds an official-channel-request constraint to the parent profile

---

## Analysis Pipeline Flow

The analysis pipeline runs after simulations are complete and produces the **Collection Playbook**.

```mermaid
flowchart TB
    START(["CLI: collection-swarm analyze"]) --> LOAD_CONFIG["Load AppConfig"]
    LOAD_CONFIG --> STORE["SimulationStore"]

    subgraph Statistics["Strategy Ranking"]
        STORE --> COMPARE["compare_strategies(profile_id)<br/><small>For each profile</small>"]
        COMPARE --> SQL_RANK["SQL: AVG(payment_probability)<br/>GROUP BY strategy_id<br/>ORDER BY DESC"]
        SQL_RANK --> RANKING["StrategyRanking<br/><small>profile_id, strategies[]</small>"]
    end

    subgraph Compliance["Compliance Checking"]
        STORE --> EXCLUSIONS["check_exclusions()<br/><small>For each profile × strategy</small>"]
        EXCLUSIONS --> SQL_COMPLIANCE["SQL: AVG(compliance_score),<br/>AVG(escalation_risk)"]
        SQL_COMPLIANCE --> CHECK{"compliance < min<br/>OR escalation > max?"}
        CHECK -->|Yes| EXCLUDE["ComplianceExclusion<br/><small>profile, strategy, reason</small>"]
        CHECK -->|No| SKIP["No exclusion"]
    end

    subgraph Objections["Objection Extraction"]
        STORE --> TRANSCRIPTS["get_all_transcripts()<br/><small>For best strategy per profile</small>"]
        TRANSCRIPTS --> KEYWORDS["Keyword matching:<br/>inability_to_pay, disputes_debt,<br/>wants_written_proof, avoidance,<br/>emotional_distress"]
        KEYWORDS --> REPORT["ObjectionReport<br/><small>category → count</small>"]
    end

    RANKING --> PLAYBOOK["generate_playbook()"]
    EXCLUDE --> PLAYBOOK
    REPORT --> PLAYBOOK

    subgraph PlaybookOutput["Playbook Assembly"]
        PLAYBOOK --> HEADER["# Collection Playbook<br/><small>timestamp, simulation count</small>"]
        HEADER --> COMPLIANCE_NOTICE["## Compliance Notice<br/><small>List exclusions</small>"]
        COMPLIANCE_NOTICE --> PER_PROFILE

        subgraph PER_PROFILE["Per Profile Section"]
            REC["### Recommended Strategy"]
            REC --> TABLE["Strategy ranking table<br/><small>payment prob, compliance, escalation</small>"]
            TABLE --> OBJ_SECTION["### Objection Playbook<br/><small>category counts</small>"]
            OBJ_SECTION --> EXAMPLE["### Example Transcript<br/><small>Best-performing run</small>"]
        end
    end

    PLAYBOOK --> OUTPUT["output/playbook.md"]
```

### Data Flow Summary

| Stage | Input | Output | Storage |
|---|---|---|---|
| **Simulation** | Profile + Strategy + Models | SimulationResult | `runs` table |
| **Tournament** | SimulationResults + Elo state | TournamentResult + Elo updates | `tournaments`, `elo_ratings`, `elo_history` |
| **Evolution** | Tournament Elo rankings | New Strategy variants | `evolved_strategies` |
| **Hardening** | Easy profiles + transcripts | Harder Profile variants | `evolved_profiles` |
| **Statistics** | Completed runs | StrategyRanking per profile | In-memory |
| **Compliance** | Completed runs + thresholds | ComplianceExclusion list | In-memory |
| **Objections** | Transcript text | ObjectionReport | In-memory |
| **Playbook** | Rankings + Exclusions + Objections | Markdown document | `output/playbook.md` |

---

## Web Dashboard Data Flow

The web dashboard mirrors all CLI workflows via REST APIs with real-time progress tracking.

```mermaid
sequenceDiagram
    participant Browser as Browser (SPA)
    participant API as FastAPI
    participant Jobs as Job Registry
    participant Task as asyncio Task
    participant Engine as SimulationEngine
    participant Store as SimulationStore

    Browser->>API: POST /api/jobs/simulations
    API->>Jobs: Create WebRunJob(status="queued")
    API->>Task: asyncio.create_task(run_job)
    API-->>Browser: { id, status: "queued" }

    loop Polling
        Browser->>API: GET /api/jobs/{job_id}
        API->>Jobs: job.snapshot()
        API-->>Browser: { status, completed, current_run, message }
    end

    Task->>Engine: run_simulation(on_progress=callback)

    loop Progress Callback
        Engine->>Task: on_progress(partial_result)
        Task->>Jobs: Update job.current_run, job.message
    end

    Engine-->>Task: SimulationResult
    Task->>Store: save_run(result)
    Task->>Jobs: job.status = "completed"

    Browser->>API: GET /api/jobs/{job_id}
    API-->>Browser: { status: "completed", result_ids: [...] }
    Browser->>API: GET /api/runs/{run_id}
    API->>Store: get_run(run_id)
    API-->>Browser: Full SimulationResult with transcript
```

### Job Types

| Job Kind | Trigger Endpoint | Behavior |
|---|---|---|
| `single` | `POST /api/jobs/simulations` | One simulation with progress streaming |
| `matrix` | `POST /api/jobs/matrix` | Parallel matrix with per-cell progress |
| `tournament` | `POST /api/jobs/tournaments` | Multi-round tournament with Elo updates |
| `model_benchmark` | `POST /api/jobs/model-benchmarks` | Cursor SDK model evaluation probes |
| `calibration` | `POST /api/jobs/calibration` | Judge calibration against human labels |

### Manual Role-Play Sessions

Manual sessions allow a human to play either the collector or debtor role:

```mermaid
sequenceDiagram
    participant Human as Human Player
    participant API as FastAPI
    participant Session as ManualSession
    participant AI as AI Agent
    participant Judge
    participant Store

    Human->>API: POST /api/manual-sessions<br/>{profile_id, strategy_id, human_role: "debtor"}
    API->>Session: Create ManualSession

    alt Human is debtor
        API->>AI: CollectorAgent.generate_turn()
        AI-->>API: Collector opening message
    end

    API-->>Human: { id, status: "waiting_for_human", transcript }

    loop Turns
        Human->>API: POST /api/manual-sessions/{id}/turn<br/>{ content: "..." }
        API->>Session: Append human message
        API->>AI: Generate AI turn (opposite role)
        AI-->>API: AI response
        API->>Session: Append AI message + check end conditions
        API-->>Human: Updated transcript
    end

    Human->>API: POST /api/manual-sessions/{id}/finish
    API->>Judge: evaluate(transcript, profile)
    Judge-->>API: Judgment
    API->>Store: save_run(result)
    API-->>Human: Final result with judgment
```

!!! tip "Concurrent Safety"
    Each manual session uses an `asyncio.Lock` to prevent race conditions from rapid turn submissions.
