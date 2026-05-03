# `cli.py` — Click entry point

<span class="cs-kicker">collection_swarm/cli.py</span>

The `collection-swarm` script. Click group with twelve subcommands. Pure
glue — every command resolves the config, builds the right helpers,
calls a domain function, and prints the result with Rich.

<dl class="cs-summary">
  <dt>Imports</dt><dd>Click, Rich, every domain module the CLI dispatches to</dd>
  <dt>Side effects</dt><dd>Reads config files, opens the SQLite store, runs the engine, writes Playbook artifacts</dd>
  <dt>Console</dt><dd>One <code>rich.console.Console</code> shared by all commands</dd>
</dl>

## The Click group

```python
@click.group()
@click.option("--config-dir", type=click.Path(path_type=Path), default=Path("config"))
@click.option("--db", "db_path", type=click.Path(path_type=Path), default=Path("output/collection_swarm.sqlite"))
@click.pass_context
def cli(ctx, config_dir, db_path):
    """Run and analyze synthetic debt collection simulations."""
    ctx.ensure_object(dict)
    ctx.obj["config_dir"] = config_dir
    ctx.obj["db_path"] = db_path
```

Every subcommand reads `ctx.obj["config_dir"]` and `ctx.obj["db_path"]`
through `@click.pass_context`. Override the defaults globally:

```bash
collection-swarm --config-dir ./alt_config --db /tmp/alt.sqlite simulate ...
```

## Subcommand catalogue

| Command            | Function                          | Calls                                                                 |
| ------------------ | --------------------------------- | --------------------------------------------------------------------- |
| `simulate`         | `simulate(...)`                   | `SimulationEngine.run_simulation`, `_print_result`                    |
| `run`              | `run_command(...)`                | `runner.build_matrix`, `runner.run_matrix`                            |
| `tournament`       | `tournament(...)`                 | `runner.run_tournament`                                               |
| `leaderboard`      | `leaderboard(...)`                | `store.get_elo_ratings`                                               |
| `reset-elo`        | `reset_elo(...)`                  | `store.reset_elo_ratings`                                             |
| `evolve`           | `evolve(...)`                     | `runner.run_evolution_cycle`                                          |
| `calibrate`        | `calibrate(...)`                  | `calibration.load_calibration_labels`, `calibration.evaluate_judge`   |
| `analyze`          | `analyze(...)`                    | `compare_strategies`, `check_exclusions`, `generate_playbook`         |
| `model-report`     | `model_report(...)`               | `model_evaluation.run_live_role_probes`, `build_model_role_report`, `write_report` |
| `test-connection`  | `test_connection(...)`            | `LLMRouter.complete` against the default model                        |
| `list-profiles` / `list-strategies` | `list_profiles` / `list_strategies` | `load_app_config`, formatted with Rich tables           |
| `serve`            | `serve(...)`                      | `web.app.create_app` + `uvicorn.run`                                  |
| `seed`             | `seed_data(...)`                  | `web.seed.generate_seed_data`                                         |

The full reference (with every flag) is in
[CLI reference](../reference/cli.md).

## Helper: `_split_csv`

```python
def _split_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]
```

Used by `run`, `tournament`, `evolve`, and `model-report` to parse
comma-separated `--profiles`, `--strategies`, etc. Returns `None` for
empty input so the downstream functions can apply their own defaults.

## Helper: `_print_result`

```python
def _print_result(result) -> None:
    console.rule(f"Simulation {result.id} [{result.status}]")
    for turn in result.transcript:
        console.print(f"[bold]{turn.role.title()}:[/bold] {turn.content}")
    console.print(f"\nEnded by: {result.ended_by}; turns: {result.turn_count}")
    if result.judgment:
        table = Table(title="Judgment")
        ...
        console.print(table)
        console.print(result.judgment.reasoning)
    if result.error_message:
        console.print(f"[red]Error:[/red] {result.error_message}")
```

The default formatter for a single Simulation: a Rich rule, the
transcript turn by turn, an `Ended by` summary, the Judgment in a Rich
table, the Judgment reasoning paragraph, and any error message.

## Why Rich

Rich tables wrap, pretty-print, and respect terminal width. The CLI
intentionally also prints a plain-text mirror of every ID list:

```python
console.print("Profile IDs: " + ", ".join(config.profiles.keys()))
```

so automation can grep the IDs even if the table is truncated to fit a
narrow terminal.

## When to bypass the CLI

The CLI's only job is to wire arguments into domain functions. If
you're building automation that needs the same orchestration plus
custom logic, import the domain functions directly instead of shelling
out to `collection-swarm`. The whole runtime is async and fully
re-entrant.
