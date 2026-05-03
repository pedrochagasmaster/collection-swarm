# CLI Reference

The `collection-swarm` CLI is the primary interface for running simulations, tournaments, analysis, and the web dashboard. It is built on [Click](https://click.palletsprojects.com/) and uses [Rich](https://rich.readthedocs.io/) for terminal output.

```bash
collection-swarm [OPTIONS] COMMAND [ARGS]
```

---

## Global Options

These options apply to every subcommand and must appear **before** the command name.

| Option | Type | Default | Description |
|---|---|---|---|
| `--config-dir` | PATH | `config` | Directory containing the YAML configuration files |
| `--db` | PATH | `output/collection_swarm.sqlite` | Path to the SQLite database for persisting results |

```bash
collection-swarm --config-dir my_configs --db results.sqlite simulate ...
```

---

## Commands

### `list-profiles`

List all configured debtor profiles in a formatted table.

```bash
collection-swarm list-profiles
```

??? example "Sample output"
    ```
    ┌──────────────────────────┬─────────────┬───────────────────────────────┬─────────────────────────┐
    │ ID                       │ Archetype   │ Debt (R$)                     │ Primary Objection       │
    ├──────────────────────────┼─────────────┼───────────────────────────────┼─────────────────────────┤
    │ cooperative_hardship     │ cooperative │ R$ 850 (credito_pessoal_will) │ inability_to_pay        │
    │ written_proof_disputer   │ disputer    │ R$ 612 (cartao_credito_will)  │ wants_written_proof     │
    │ hostile_avoidant         │ hostile     │ R$ 1,900 (cartao_credito_will)│ avoidance               │
    │ ...                      │ ...         │ ...                           │ ...                     │
    └──────────────────────────┴─────────────┴───────────────────────────────┴─────────────────────────┘
    ```

---

### `list-strategies`

List all configured collector strategies in a formatted table.

```bash
collection-swarm list-strategies
```

??? example "Sample output"
    ```
    ┌───────────────────────────┬────────────┬──────────────────────────┬──────────────────────────────────┐
    │ ID                        │ Tone       │ Tactic                   │ Follow-up                        │
    ├───────────────────────────┼────────────┼──────────────────────────┼──────────────────────────────────┤
    │ empathetic_payment_plan   │ empathetic │ payment_plan             │ written_agreement                │
    │ assertive_settlement      │ assertive  │ settlement_offer         │ immediate_payment                │
    │ neutral_reminder          │ neutral    │ payment_reminder         │ digital_link_to_self_service     │
    │ ...                       │ ...        │ ...                      │ ...                              │
    └───────────────────────────┴────────────┴──────────────────────────┴──────────────────────────────────┘
    ```

---

### `simulate`

Run a single simulation between one profile and one strategy, then print the transcript and judgment.

```bash
collection-swarm simulate [OPTIONS]
```

| Option | Type | Required | Default | Description |
|---|---|---|---|---|
| `--profile` | STRING | **Yes** | — | Debtor profile ID |
| `--strategy` | STRING | **Yes** | — | Collector strategy ID |
| `--conversation-model` | STRING | No | First `scripted` model | Model ID for Collector and Debtor roles |
| `--judge-model` | STRING | No | First `heuristic` model | Model ID for the Judge role |
| `--no-save` | FLAG | No | `false` | Print results without persisting to SQLite |

#### Examples

```bash
# Offline simulation (scripted backend)
collection-swarm simulate \
  --profile cooperative_hardship \
  --strategy empathetic_payment_plan \
  --no-save

# Live simulation with NVIDIA NIM
collection-swarm simulate \
  --profile hostile_avoidant \
  --strategy assertive_settlement \
  --conversation-model nim-llama-4-maverick \
  --judge-model nim-mistral-large-3-675b

# Live simulation with Cursor SDK
collection-swarm simulate \
  --profile scam_suspicious \
  --strategy liquidation_explainer \
  --conversation-model cursor-gpt-5.5-medium \
  --judge-model cursor-claude-4.6-opus-high-thinking
```

---

### `run`

Run a full matrix of simulations: every combination of the selected profiles × strategies × models × repetitions.

```bash
collection-swarm run [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--profiles` | STRING | All | Comma-separated profile IDs |
| `--strategies` | STRING | All | Comma-separated strategy IDs |
| `--conversation-models` | STRING | Default model | Comma-separated conversation model IDs |
| `--judge-models` | STRING | Default model | Comma-separated judge model IDs |
| `--reps` | INT | From `simulation.yaml` | Repetitions per matrix cell |
| `--concurrency` | INT | `2` | Maximum parallel simulations |

#### Examples

```bash
# Run all profiles × all strategies, 1 rep each
collection-swarm run

# Focused run with specific profiles and strategies
collection-swarm run \
  --profiles cooperative_hardship,hostile_avoidant \
  --strategies empathetic_payment_plan,assertive_settlement \
  --reps 5 \
  --concurrency 8

# Multi-model matrix
collection-swarm run \
  --conversation-models nim-llama-4-maverick,nim-mistral-large-3-675b \
  --judge-models cursor-claude-4.6-opus-high-thinking \
  --reps 3
```

!!! info "Matrix size"
    Total simulations = profiles × strategies × conversation models × judge models × reps. A full matrix with 14 profiles, 14 strategies, 2 conversation models, and 3 reps produces **1,176 simulations**.

---

### `tournament`

Run an Elo-rated tournament that pits strategies and profiles against each other in head-to-head matchups.

```bash
collection-swarm tournament [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--format` | CHOICE | From `simulation.yaml` | Tournament format: `swiss` or `round_robin` |
| `--rounds` | INT | From `simulation.yaml` | Number of tournament rounds |
| `--profiles` | STRING | All | Comma-separated profile IDs |
| `--strategies` | STRING | All | Comma-separated strategy IDs |
| `--conversation-model` | STRING | Default model | Model ID for Collector and Debtor |
| `--judge-model` | STRING | Default model | Model ID for the Judge |
| `--concurrency` | INT | `2` | Maximum parallel games |

#### Examples

```bash
# Swiss tournament with defaults
collection-swarm tournament

# Round-robin with more rounds
collection-swarm tournament --format round_robin --rounds 8

# Tournament on a subset of strategies
collection-swarm tournament \
  --strategies empathetic_payment_plan,assertive_settlement,neutral_reminder \
  --conversation-model nim-llama-4-maverick \
  --concurrency 4
```

!!! tip "Swiss vs. Round Robin"
    **Swiss** pairs opponents with similar ratings each round — fewer games, faster convergence. **Round Robin** plays every possible matchup — more games, complete coverage.

---

### `leaderboard`

Display current Elo ratings from the database.

```bash
collection-swarm leaderboard [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--type` | CHOICE | `all` | Filter by entity type: `strategy`, `profile`, or `all` |

#### Examples

```bash
# Show all rankings
collection-swarm leaderboard

# Show only strategy rankings
collection-swarm leaderboard --type strategy

# Show only profile rankings
collection-swarm leaderboard --type profile
```

---

### `reset-elo`

Reset all Elo ratings and game history in the database. This does **not** delete simulation results — only the tournament ratings.

```bash
collection-swarm reset-elo
```

!!! warning "Irreversible"
    This permanently clears all Elo data. Run a fresh tournament afterwards to rebuild ratings.

---

### `evolve`

Run tournament-driven strategy evolution. The evolver LLM mutates, recombines, and selects strategies across multiple generations based on tournament performance.

```bash
collection-swarm evolve [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--generations` | INT | `5` | Number of evolutionary generations |
| `--population-size` | INT | `20` | Number of strategies in the population per generation |
| `--evolver-model` | STRING | Default conv. model | Model ID for the strategy-evolving LLM |
| `--tournament-rounds` | INT | `4` | Rounds per intra-generation tournament |
| `--profiles` | STRING | All | Comma-separated profile IDs for fitness evaluation |
| `--strategies` | STRING | All | Comma-separated seed strategy IDs |
| `--concurrency` | INT | `2` | Maximum parallel simulations |

#### Examples

```bash
# Default evolution
collection-swarm evolve

# Larger population, more generations
collection-swarm evolve \
  --generations 10 \
  --population-size 40 \
  --evolver-model cursor-gpt-5.5-medium \
  --concurrency 8

# Evolve strategies against specific hard profiles
collection-swarm evolve \
  --profiles hostile_avoidant,scam_suspicious,feirao_serial_renegotiator \
  --generations 8
```

---

### `calibrate`

Evaluate stored judge scores against human-labeled ground truth. Optionally save the current judge prompt as a scored variant for comparison.

```bash
collection-swarm calibrate [OPTIONS]
```

| Option | Type | Required | Default | Description |
|---|---|---|---|---|
| `--labels` | PATH | **Yes** | — | Path to a JSON file with calibration labels |
| `--optimize` | FLAG | No | `false` | Store the current judge prompt as a scored variant |

#### Examples

```bash
# Evaluate judge accuracy
collection-swarm calibrate --labels data/calibration_labels.json

# Evaluate and save this prompt variant
collection-swarm calibrate --labels data/calibration_labels.json --optimize
```

!!! info "Calibration labels format"
    The JSON file should contain human-scored judgments for specific simulation IDs. See the Judge Calibration guide for the expected schema.

---

### `analyze`

Generate a Markdown playbook from all completed simulations in the database. The playbook ranks strategies per profile, flags compliance exclusions, and provides statistical breakdowns.

```bash
collection-swarm analyze [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--output` | PATH | `output/playbook.md` | Output path for the generated playbook |

#### Examples

```bash
# Generate playbook with default path
collection-swarm analyze

# Custom output path
collection-swarm analyze --output reports/q2_playbook.md
```

---

### `model-report`

Generate a parameterized evaluation report comparing how different models perform across the Collector, Debtor, and Judge roles.

```bash
collection-swarm model-report [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--output` | PATH | `docs/cursor-model-role-report.md` | Report destination |
| `--format` | CHOICE | `markdown` | Output format: `markdown` or `json` |
| `--live-probes` | FLAG | `false` | Run live Cursor SDK probes instead of using the baseline |
| `--cursor-models` | STRING | Built-in defaults | Comma-separated Cursor model IDs for live probes |
| `--roles` | STRING | `collector,debtor,judge` | Comma-separated roles to probe |
| `--profile` | STRING | `cooperative_hardship` | Profile ID for the probe scenario |
| `--strategy` | STRING | `empathetic_payment_plan` | Strategy ID for the probe scenario |
| `--judge-profile` | STRING | `written_proof_disputer` | Profile used when probing the judge role |
| `--concurrency` | INT | `1` | Maximum parallel probes |

#### Examples

```bash
# Generate report from baseline data
collection-swarm model-report

# Run live probes with specific models
collection-swarm model-report \
  --live-probes \
  --cursor-models gpt-5.5,claude-opus-4-7 \
  --roles collector,debtor \
  --concurrency 2

# JSON output for programmatic consumption
collection-swarm model-report --format json --output reports/models.json
```

---

### `test-connection`

Verify that the default model backend can produce a completion. For local backends (`scripted`, `heuristic`), this runs a test generation. For remote backends (`nim`, `cursor_sdk`), it prints a message directing you to run a simulation.

```bash
collection-swarm test-connection
```

#### Example

```bash
collection-swarm test-connection
# Backend ready: scripted (local-scripted), output_tokens=42
```

---

### `serve`

Launch the web dashboard for exploring simulation results, transcripts, and analytics in the browser.

```bash
collection-swarm serve [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--host` | STRING | `127.0.0.1` | Bind address |
| `--port` | INT | `8000` | Bind port |
| `--reload` | FLAG | `false` | Enable auto-reload (development only) |

#### Examples

```bash
# Start dashboard on default port
collection-swarm serve

# Bind to all interfaces on port 3000
collection-swarm serve --host 0.0.0.0 --port 3000
```

!!! tip "Quick demo"
    Seed the database with demo data first:
    ```bash
    collection-swarm seed --count 50
    collection-swarm serve
    ```
    Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

### `seed`

Generate realistic demo data and persist it to the database. Useful for exploring the dashboard and testing analysis pipelines without running real simulations.

```bash
collection-swarm seed [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--count` | INT | `24` | Number of seed simulations to generate |

#### Examples

```bash
# Generate 24 demo simulations
collection-swarm seed

# Generate 100 demo simulations
collection-swarm seed --count 100

# Seed into a custom database
collection-swarm --db demo.sqlite seed --count 50
```

---

### `creds`

Manage API credentials stored in the dashboard database. Stored values
override matching environment variables for every backend (CLI, web,
runner, model probes), so dashboard users no longer have to manage `.env`
files manually.

```bash
collection-swarm creds list                        # show provider statuses
collection-swarm creds providers                   # describe known providers
collection-swarm creds set <provider> [--value V]  # store a credential
collection-swarm creds clear <provider>            # delete a stored credential
```

Supported providers (run `collection-swarm creds providers` for the live
list):

| Provider ID  | Env Var                | Used by              |
|--------------|------------------------|----------------------|
| `cursor`     | `CURSOR_API_KEY`       | Cursor SDK backend   |
| `nvidia_nim` | `NVIDIA_NIM_API_KEY`   | NVIDIA NIM backend   |

#### Examples

```bash
# Interactive — prompts with hidden input
collection-swarm creds set cursor

# Non-interactive (CI / scripted setup)
collection-swarm creds set nvidia_nim --value "$NVIDIA_NIM_API_KEY"

# Show current state
collection-swarm creds list

# Remove a stored value (env vars still apply if set)
collection-swarm creds clear cursor
```

---

## Command Quick Reference

| Command | Purpose |
|---|---|
| `list-profiles` | Show all debtor profiles |
| `list-strategies` | Show all collector strategies |
| `simulate` | Run one conversation |
| `run` | Run a full matrix of conversations |
| `tournament` | Run an Elo-rated tournament |
| `leaderboard` | Show Elo rankings |
| `reset-elo` | Clear all Elo data |
| `evolve` | Evolve strategies over generations |
| `calibrate` | Evaluate judge accuracy |
| `analyze` | Generate a strategy playbook |
| `model-report` | Compare model performance per role |
| `test-connection` | Verify backend connectivity |
| `serve` | Launch the web dashboard |
| `seed` | Generate demo data |
| `creds` | Manage dashboard-stored API credentials |
