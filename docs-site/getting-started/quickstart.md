# Quick Start

This guide walks you through running simulations, viewing results, and generating a playbook — all in about ten minutes.

---

## 1. Run Your First Offline Simulation

The fastest way to see Collection Swarm in action is the **scripted backend**, which requires no API keys:

```bash
collection-swarm simulate \
  --profile cooperative_hardship \
  --strategy empathetic_payment_plan \
  --no-save
```

This runs a single multi-turn conversation between a Collector and Debtor, then prints the transcript and judgment:

```
──────────────── Simulation abc123 [completed] ────────────────
Collector: Bom dia! Aqui é da equipe de cobrança ...
Debtor: Oi, bom dia. Eu sei que estou devendo ...
Collector: Entendo sua situação ...
...

┌─────────────────────┬───────────┐
│ Metric              │ Value     │
├─────────────────────┼───────────┤
│ Payment outcome     │ partial   │
│ Payment probability │ 65%       │
│ Compliance score    │ 95%       │
│ Rapport built       │ 80%       │
│ Escalation risk     │ 10%       │
└─────────────────────┴───────────┘
```

!!! tip "Understanding `--no-save`"
    The `--no-save` flag prints results to the terminal without persisting to SQLite. Drop it when you want results stored for later analysis.

---

## 2. Run With Live Models

To use real LLM backends, pass model IDs explicitly:

=== "NVIDIA NIM"

    ```bash
    collection-swarm simulate \
      --profile hostile_avoidant \
      --strategy assertive_settlement \
      --conversation-model nim-llama-4-maverick \
      --judge-model nim-mistral-large-3-675b
    ```

=== "Cursor SDK"

    ```bash
    collection-swarm simulate \
      --profile scam_suspicious \
      --strategy liquidation_explainer \
      --conversation-model cursor-gpt-5.5-medium \
      --judge-model cursor-claude-4.6-opus-high-thinking
    ```

!!! warning "API keys required"
    Live models need the corresponding environment variable set — `NVIDIA_NIM_API_KEY` for NIM or `CURSOR_API_KEY` for Cursor SDK. See [Installation](installation.md#4-environment-variables).

---

## 3. Run a Matrix of Simulations

The `run` command executes every combination of profiles × strategies × models and saves all results:

```bash
collection-swarm run \
  --profiles cooperative_hardship,hostile_avoidant,scam_suspicious \
  --strategies empathetic_payment_plan,assertive_settlement,neutral_reminder \
  --reps 3 \
  --concurrency 4
```

This produces 3 profiles × 3 strategies × 3 repetitions = **27 simulations**, running up to 4 in parallel.

!!! info "Defaults"
    Omit `--profiles` or `--strategies` to use **all** configured profiles or strategies. The default repetition count comes from `config/simulation.yaml` (`matrix.default_repetitions`).

---

## 4. Run an Elo Tournament

Tournaments rank strategies (and profiles) using an Elo rating system:

```bash
collection-swarm tournament \
  --format swiss \
  --rounds 6 \
  --concurrency 4
```

After the tournament completes, view the leaderboard:

```bash
collection-swarm leaderboard --type strategy
```

```
┌──────────┬──────────────────────────┬───────┬───────┬───────┐
│ Type     │ ID                       │   Elo │ Games │ W-L-D │
├──────────┼──────────────────────────┼───────┼───────┼───────┤
│ strategy │ empathetic_payment_plan  │ 1584  │    12 │ 8-2-2 │
│ strategy │ liquidation_explainer    │ 1542  │    12 │ 7-3-2 │
│ strategy │ assertive_settlement     │ 1498  │    12 │ 5-5-2 │
│ strategy │ neutral_reminder         │ 1456  │    12 │ 4-6-2 │
└──────────┴──────────────────────────┴───────┴───────┴───────┘
```

---

## 5. View Results in the Dashboard

Launch the web dashboard to explore transcripts, scores, and analytics:

```bash
collection-swarm serve --port 8000
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

!!! tip "Seed demo data"
    If you want to explore the dashboard before running real simulations, generate demo data:
    ```bash
    collection-swarm seed --count 50
    collection-swarm serve
    ```

---

## 6. Generate a Playbook

After running enough simulations, distill the results into a Markdown playbook:

```bash
collection-swarm analyze --output output/playbook.md
```

The playbook contains:

- **Best strategy per debtor archetype** — ranked by composite score
- **Compliance exclusions** — strategies that breach the compliance threshold
- **Statistical breakdowns** — payment rates, satisfaction, and risk per profile–strategy pair

---

## Full Example: End-to-End Workflow

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Run a matrix across all profiles and strategies (offline)
collection-swarm run --reps 2

# 3. Run an Elo tournament
collection-swarm tournament --format swiss --rounds 4

# 4. Check the leaderboard
collection-swarm leaderboard

# 5. Generate the playbook
collection-swarm analyze

# 6. Launch the dashboard
collection-swarm serve
```

---

## What's Next?

- **[Configuration](configuration.md)** — Customize debtor profiles, collector strategies, model backends, and prompts.
- **[CLI Reference](../cli.md)** — Full documentation for every command and flag.
- **[Architecture Overview](../architecture/overview.md)** — Understand how the engine, agents, and backends fit together.
