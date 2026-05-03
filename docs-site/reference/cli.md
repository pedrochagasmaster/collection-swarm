# CLI reference

All commands share two top-level options:

| Option         | Default                          | Purpose                          |
| -------------- | -------------------------------- | -------------------------------- |
| `--config-dir` | `config`                         | Directory holding the five YAML files. |
| `--db`         | `output/collection_swarm.sqlite` | Path to the SQLite database.    |

Place them before the subcommand:

```bash
collection-swarm --db /tmp/local.sqlite simulate ...
```

## `simulate`

Run one Simulation, optionally persist it, print the transcript and
Judgment.

```bash
collection-swarm simulate \
  --profile <profile_id> \
  --strategy <strategy_id> \
  [--conversation-model <id>] \
  [--judge-model <id>] \
  [--no-save]
```

| Flag                    | Required | Default                       |
| ----------------------- | -------- | ----------------------------- |
| `--profile`             | yes      | —                             |
| `--strategy`            | yes      | —                             |
| `--conversation-model`  | no       | `config.default_conversation_model` |
| `--judge-model`         | no       | `config.default_judge_model`  |
| `--no-save`             | no       | `false`                       |

## `run`

Run a matrix of Simulations.

```bash
collection-swarm run \
  [--profiles a,b] \
  [--strategies a,b] \
  [--conversation-models a,b] \
  [--judge-models a,b] \
  [--reps N] \
  [--concurrency N]
```

| Flag                     | Default                                          |
| ------------------------ | ------------------------------------------------ |
| `--profiles`             | All Profiles                                     |
| `--strategies`           | All Strategies                                   |
| `--conversation-models`  | `[config.default_conversation_model]`            |
| `--judge-models`         | `[config.default_judge_model]`                   |
| `--reps`                 | `config.simulation.default_repetitions` (1)      |
| `--concurrency`          | `2`                                              |

## `tournament`

Run an Elo-rated strategy/profile tournament.

```bash
collection-swarm tournament \
  [--format swiss|round_robin] \
  [--rounds N] \
  [--profiles a,b] \
  [--strategies a,b] \
  [--conversation-model id] \
  [--judge-model id] \
  [--concurrency N]
```

Defaults are pulled from `config/simulation.yaml > arena`.

## `leaderboard`

Show current Elo rankings.

```bash
collection-swarm leaderboard [--type strategy|profile|all]
```

`--type all` (default) shows both Strategy and Profile rows
interleaved by rating.

## `reset-elo`

Wipe `elo_ratings` and `elo_history`.

```bash
collection-swarm reset-elo
```

## `evolve`

Run tournament-driven Strategy evolution.

```bash
collection-swarm evolve \
  [--generations N] \
  [--population-size N] \
  [--evolver-model id] \
  [--tournament-rounds N] \
  [--profiles a,b] \
  [--strategies a,b] \
  [--concurrency N]
```

| Flag                  | Default                                         |
| --------------------- | ----------------------------------------------- |
| `--generations`       | `5`                                             |
| `--population-size`   | `20`                                            |
| `--evolver-model`     | `config.default_conversation_model`             |
| `--tournament-rounds` | `4`                                             |
| `--profiles`          | All Profiles                                    |
| `--strategies`        | All Strategies                                  |
| `--concurrency`       | `2`                                             |

## `calibrate`

Score the Judge against human labels.

```bash
collection-swarm calibrate --labels labels.json [--optimize]
```

`--optimize` snapshots the current Judge prompts (system + transcript)
into the `judge_prompt_variants` table along with the resulting score.

## `analyze`

Generate a Markdown Playbook.

```bash
collection-swarm analyze [--output output/playbook.md]
```

Writes the file with `output_path.write_text(..., encoding="utf-8")`.
The parent directory is created if needed.

## `model-report`

Generate a Cursor model-role evaluation report.

```bash
collection-swarm model-report \
  [--output docs/cursor-model-role-report.md] \
  [--format markdown|json] \
  [--live-probes] \
  [--cursor-models gpt-5.5,gpt-5.4,claude-opus-4-7] \
  [--roles collector,debtor,judge] \
  [--profile <id>] \
  [--strategy <id>] \
  [--judge-profile <id>] \
  [--concurrency N]
```

`--live-probes` runs real Cursor SDK calls. Without it, the report uses
the checked-in `BASELINE_PROBES`.

## `test-connection`

Probe the configured default conversation model.

```bash
collection-swarm test-connection
```

For NIM and Cursor SDK backends, the command prints a hint instead of
running a probe — those backends require credentials and a real call,
which is what `simulate` is for.

## `serve`

Launch the FastAPI dashboard.

```bash
collection-swarm serve [--host 127.0.0.1] [--port 8000] [--reload]
```

`--reload` is rejected (the configured factory is incompatible with
uvicorn's import-string reloader).

## `seed`

Insert deterministic demo data into the SQLite store.

```bash
collection-swarm seed [--count 24]
```

## `list-profiles` / `list-strategies`

Print the catalog. Both produce a Rich table and a plain-text mirror so
automation can parse the IDs.

```bash
collection-swarm list-profiles
collection-swarm list-strategies
```
