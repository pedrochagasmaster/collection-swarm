"""Command-line interface for Collection Swarm."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from collection_swarm.env import set_db_path
from collection_swarm.agents.collector import CollectorAgent
from collection_swarm.agents.debtor import DebtorAgent
from collection_swarm.agents.judge import Judge
from collection_swarm.analysis.compliance import check_exclusions
from collection_swarm.analysis.playbook import generate_playbook
from collection_swarm.analysis.statistics import compare_strategies
from collection_swarm.backends.router import LLMRouter
from collection_swarm.calibration import evaluate_judge, load_calibration_labels
from collection_swarm.config import load_app_config
from collection_swarm.engine import SimulationEngine
from collection_swarm.model_evaluation import (
    DEFAULT_CURSOR_PROBE_MODELS,
    ProbeScenario,
    build_model_role_report,
    run_live_role_probes,
    write_report,
)
from collection_swarm.models import EvolutionConfig, TournamentConfig
from collection_swarm.runner import build_matrix, run_evolution_cycle, run_matrix, run_tournament
from collection_swarm.store import SimulationStore

console = Console()


def _split_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


@click.group()
@click.option("--config-dir", type=click.Path(path_type=Path), default=Path("config"), show_default=True)
@click.option("--db", "db_path", type=click.Path(path_type=Path), default=Path("output/collection_swarm.sqlite"), show_default=True)
@click.pass_context
def cli(ctx: click.Context, config_dir: Path, db_path: Path) -> None:
    """Run and analyze synthetic debt collection simulations."""
    ctx.ensure_object(dict)
    ctx.obj["config_dir"] = config_dir
    ctx.obj["db_path"] = db_path
    set_db_path(db_path)


@cli.command("list-profiles")
@click.pass_context
def list_profiles(ctx: click.Context) -> None:
    """List configured Profiles."""
    config = load_app_config(ctx.obj["config_dir"])
    table = Table(title="Profiles")
    table.add_column("ID", no_wrap=False, overflow="fold")
    table.add_column("Archetype", overflow="fold")
    table.add_column("Debt (R$)", overflow="fold")
    table.add_column("Primary Objection", overflow="fold")
    for profile in config.profiles.values():
        table.add_row(
            profile.id,
            profile.archetype,
            f"R$ {profile.debt_amount:,.0f} ({profile.debt_type})",
            profile.primary_objection,
        )
    console.print(table)
    # Plain-text mirror so IDs are always parseable from automation contexts
    # where Rich may truncate to fit narrow terminals.
    console.print("Profile IDs: " + ", ".join(config.profiles.keys()))


@cli.command("list-strategies")
@click.pass_context
def list_strategies(ctx: click.Context) -> None:
    """List configured Strategies."""
    config = load_app_config(ctx.obj["config_dir"])
    table = Table(title="Strategies")
    table.add_column("ID", no_wrap=False, overflow="fold")
    table.add_column("Tone", overflow="fold")
    table.add_column("Tactic", overflow="fold")
    table.add_column("Follow-up", overflow="fold")
    for strategy in config.strategies.values():
        table.add_row(strategy.id, strategy.tone, strategy.negotiation_tactic, strategy.follow_up_strategy)
    console.print(table)
    console.print("Strategy IDs: " + ", ".join(config.strategies.keys()))


@cli.command()
@click.option("--profile", "profile_id", required=True, help="Profile ID to simulate.")
@click.option("--strategy", "strategy_id", required=True, help="Strategy ID to simulate.")
@click.option("--conversation-model", default=None, help="Model ID for Collector and Debtor.")
@click.option("--judge-model", default=None, help="Model ID for the Judge.")
@click.option("--no-save", is_flag=True, help="Print only; do not persist the Simulation.")
@click.pass_context
def simulate(
    ctx: click.Context,
    profile_id: str,
    strategy_id: str,
    conversation_model: str | None,
    judge_model: str | None,
    no_save: bool,
) -> None:
    """Run one Simulation and print transcript plus Judgment."""
    config = load_app_config(ctx.obj["config_dir"])
    conversation_model = conversation_model or config.default_conversation_model
    judge_model = judge_model or config.default_judge_model
    router = LLMRouter(config.models, cursor_sdk_prompts=config.prompts.cursor_sdk)
    settings = config.simulation.conversation
    engine = SimulationEngine(
        CollectorAgent(router, conversation_model, config.prompts.collector),
        DebtorAgent(router, conversation_model, config.prompts.debtor),
        Judge(router, judge_model, config.prompts.judge),
        max_turns=settings.max_turns,
        end_signal=settings.end_signal,
        stalemate_window=settings.stalemate_window,
        stalemate_similarity_threshold=settings.stalemate_similarity_threshold,
    )
    result = asyncio.run(engine.run_simulation(config.profile(profile_id), config.strategy(strategy_id)))
    if not no_save:
        SimulationStore(ctx.obj["db_path"]).save_run(result)
    _print_result(result)


@cli.command("run")
@click.option("--profiles", default=None, help="Comma-separated profile IDs. Defaults to all.")
@click.option("--strategies", default=None, help="Comma-separated strategy IDs. Defaults to all.")
@click.option("--conversation-models", default=None, help="Comma-separated conversation model IDs.")
@click.option("--judge-models", default=None, help="Comma-separated judge model IDs.")
@click.option("--reps", default=None, type=int, help="Repetitions per matrix cell.")
@click.option("--concurrency", default=2, show_default=True, type=int)
@click.pass_context
def run_command(
    ctx: click.Context,
    profiles: str | None,
    strategies: str | None,
    conversation_models: str | None,
    judge_models: str | None,
    reps: int | None,
    concurrency: int,
) -> None:
    """Run a matrix of Simulations."""
    config = load_app_config(ctx.obj["config_dir"])
    cells = build_matrix(
        config,
        profile_ids=_split_csv(profiles),
        strategy_ids=_split_csv(strategies),
        conversation_models=_split_csv(conversation_models),
        judge_models=_split_csv(judge_models),
        reps=reps or config.simulation.default_repetitions,
    )
    summary = asyncio.run(run_matrix(config, SimulationStore(ctx.obj["db_path"]), cells, concurrency=concurrency))
    console.print(f"Completed {summary.completed}/{summary.total} simulations; failed {summary.failed}.")


@cli.command()
@click.option("--format", "tournament_format", type=click.Choice(["swiss", "round_robin"]), default=None)
@click.option("--rounds", default=None, type=int)
@click.option("--profiles", default=None, help="Comma-separated profile IDs. Defaults to all.")
@click.option("--strategies", default=None, help="Comma-separated strategy IDs. Defaults to all.")
@click.option("--conversation-model", default=None, help="Model ID for Collector and Debtor.")
@click.option("--judge-model", default=None, help="Model ID for the Judge.")
@click.option("--concurrency", default=2, show_default=True, type=int)
@click.pass_context
def tournament(
    ctx: click.Context,
    tournament_format: str | None,
    rounds: int | None,
    profiles: str | None,
    strategies: str | None,
    conversation_model: str | None,
    judge_model: str | None,
    concurrency: int,
) -> None:
    """Run an Elo-rated strategy/profile tournament."""
    config = load_app_config(ctx.obj["config_dir"])
    arena_settings = config.simulation.arena
    result = asyncio.run(
        run_tournament(
            config,
            SimulationStore(ctx.obj["db_path"]),
            TournamentConfig(
                format=tournament_format or arena_settings.default_format,
                rounds=rounds or arena_settings.default_rounds,
                k_factor_initial=arena_settings.k_factor_initial,
                k_factor_stable=arena_settings.k_factor_stable,
                k_factor_threshold=arena_settings.k_factor_threshold,
                scoring=arena_settings.scoring,
            ),
            profile_ids=_split_csv(profiles),
            strategy_ids=_split_csv(strategies),
            conversation_model=conversation_model,
            judge_model=judge_model,
            concurrency=concurrency,
        )
    )
    console.print(f"Tournament {result.id} completed: {result.total_games} games across {result.rounds_completed} rounds.")


@cli.command()
@click.option("--type", "entity_type", type=click.Choice(["strategy", "profile", "all"]), default="all")
@click.pass_context
def leaderboard(ctx: click.Context, entity_type: str) -> None:
    """Show current Elo rankings."""
    store = SimulationStore(ctx.obj["db_path"])
    ratings = store.get_elo_ratings(None if entity_type == "all" else entity_type)
    if not ratings:
        console.print("No Elo ratings yet.")
        return
    table = Table(title="Elo Leaderboard")
    table.add_column("Type")
    table.add_column("ID", no_wrap=False, overflow="fold")
    table.add_column("Elo", justify="right")
    table.add_column("Games", justify="right")
    table.add_column("W-L-D", justify="right")
    for rating in ratings:
        table.add_row(
            rating.entity_type,
            rating.entity_id,
            f"{rating.rating:.1f}",
            str(rating.games_played),
            f"{rating.wins}-{rating.losses}-{rating.draws}",
        )
    console.print(table)


@cli.command("reset-elo")
@click.pass_context
def reset_elo(ctx: click.Context) -> None:
    """Reset all Elo ratings and history."""
    SimulationStore(ctx.obj["db_path"]).reset_elo_ratings()
    console.print("Reset Elo ratings.")


@cli.command("evolve")
@click.option("--generations", default=5, type=int, show_default=True)
@click.option("--population-size", default=20, type=int, show_default=True)
@click.option("--evolver-model", default=None, help="Model ID for the strategy evolver LLM.")
@click.option("--tournament-rounds", default=4, type=int, show_default=True)
@click.option("--profiles", default=None, help="Comma-separated profile IDs. Defaults to all.")
@click.option("--strategies", default=None, help="Comma-separated strategy IDs. Defaults to all.")
@click.option("--concurrency", default=2, type=int, show_default=True)
@click.pass_context
def evolve(
    ctx: click.Context,
    generations: int,
    population_size: int,
    evolver_model: str | None,
    tournament_rounds: int,
    profiles: str | None,
    strategies: str | None,
    concurrency: int,
) -> None:
    """Run tournament-driven strategy evolution."""
    config = load_app_config(ctx.obj["config_dir"])
    model_id = evolver_model or config.default_conversation_model
    results = asyncio.run(
        run_evolution_cycle(
            config,
            SimulationStore(ctx.obj["db_path"]),
            EvolutionConfig(population_size=population_size, evolver_model_id=model_id),
            TournamentConfig(format=config.simulation.arena.default_format, rounds=tournament_rounds),
            generations=generations,
            profile_ids=_split_csv(profiles),
            strategy_ids=_split_csv(strategies),
            concurrency=concurrency,
        )
    )
    console.print(f"Evolution completed: {len(results)} generation{'s' if len(results) != 1 else ''}.")


@cli.command("calibrate")
@click.option("--labels", type=click.Path(path_type=Path), required=True, help="Path to calibration labels JSON.")
@click.option("--optimize", is_flag=True, help="Store the current judge prompt as a scored variant.")
@click.pass_context
def calibrate(ctx: click.Context, labels: Path, optimize: bool) -> None:
    """Evaluate stored judge scores against human calibration labels."""
    config = load_app_config(ctx.obj["config_dir"])
    store = SimulationStore(ctx.obj["db_path"])
    loaded = load_calibration_labels(labels)
    store.save_calibration_labels(loaded)
    result = evaluate_judge(loaded, store)
    if optimize:
        store.save_judge_variant(
            config.prompts.judge.system,
            config.prompts.judge.transcript,
            calibration_score=result.overall_score,
        )
    console.print(f"Calibration labels: {result.label_count}; score: {result.overall_score:.2f}.")


@cli.command()
@click.option("--output", "output_path", type=click.Path(path_type=Path), default=Path("output/playbook.md"), show_default=True)
@click.pass_context
def analyze(ctx: click.Context, output_path: Path) -> None:
    """Generate a Markdown Playbook from completed Simulations."""
    config = load_app_config(ctx.obj["config_dir"])
    store = SimulationStore(ctx.obj["db_path"])
    rankings = [compare_strategies(profile_id, store) for profile_id in config.profiles]
    exclusions = check_exclusions(
        store,
        list(config.profiles),
        list(config.strategies),
        min_compliance_score=config.simulation.min_compliance_score,
        max_escalation_risk=config.simulation.max_escalation_risk,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generate_playbook(rankings, exclusions, store), encoding="utf-8")
    console.print(f"Wrote playbook to {output_path}")


@cli.command("model-report")
@click.option(
    "--output",
    "output_path",
    type=click.Path(path_type=Path),
    default=Path("docs/cursor-model-role-report.md"),
    show_default=True,
    help="Report destination.",
)
@click.option("--format", "report_format", type=click.Choice(["markdown", "json"]), default="markdown", show_default=True)
@click.option("--live-probes", is_flag=True, help="Run live Cursor SDK probes instead of using the checked-in baseline.")
@click.option(
    "--cursor-models",
    default=None,
    help="Comma-separated provider-facing Cursor SDK model IDs for live probes, e.g. gpt-5.5,claude-opus-4-7.",
)
@click.option("--roles", default=None, help="Comma-separated roles to probe: collector,debtor,judge.")
@click.option("--profile", "profile_id", default="cooperative_hardship", show_default=True)
@click.option("--strategy", "strategy_id", default="empathetic_payment_plan", show_default=True)
@click.option("--judge-profile", "judge_profile_id", default="written_proof_disputer", show_default=True)
@click.option("--concurrency", default=1, show_default=True, type=int)
@click.pass_context
def model_report(
    ctx: click.Context,
    output_path: Path,
    report_format: str,
    live_probes: bool,
    cursor_models: str | None,
    roles: str | None,
    profile_id: str,
    strategy_id: str,
    judge_profile_id: str,
    concurrency: int,
) -> None:
    """Generate a parameterized Cursor model-role evaluation report."""
    config = load_app_config(ctx.obj["config_dir"])
    scenario = ProbeScenario(profile_id=profile_id, strategy_id=strategy_id, judge_profile_id=judge_profile_id)
    probes = None
    if live_probes:
        selected_roles = tuple(_split_csv(roles) or ("collector", "debtor", "judge"))
        invalid_roles = [role for role in selected_roles if role not in {"collector", "debtor", "judge"}]
        if invalid_roles:
            raise click.ClickException(f"unknown model-report role(s): {', '.join(invalid_roles)}")
        probes = asyncio.run(
            run_live_role_probes(
                config,
                cursor_model_names=tuple(_split_csv(cursor_models) or DEFAULT_CURSOR_PROBE_MODELS),
                roles=selected_roles,  # type: ignore[arg-type]
                scenario=scenario,
                concurrency=concurrency,
            )
        )
    report = build_model_role_report(config, probes=probes, scenario=scenario)
    write_report(report, output_path, report_format=report_format)  # type: ignore[arg-type]
    console.print(f"Wrote model-role report to {output_path}")


@cli.command("test-connection")
@click.pass_context
def test_connection(ctx: click.Context) -> None:
    """Verify the default model path can produce a local completion."""
    config = load_app_config(ctx.obj["config_dir"])
    model = config.model(config.default_conversation_model)
    if model.backend in {"nim", "cursor_sdk", "acp"}:
        console.print(f"Configured default backend is '{model.backend}'. Run a simulation to test live credentials.")
        return
    result = asyncio.run(
        LLMRouter(config.models, cursor_sdk_prompts=config.prompts.cursor_sdk).complete(
            config.default_conversation_model,
            [],
        )
    )
    console.print(f"Backend ready: {result.backend} ({result.model_id}), output_tokens={result.output_tokens}")


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host.")
@click.option("--port", default=8000, show_default=True, type=int, help="Bind port.")
@click.option("--reload", "auto_reload", is_flag=True, help="Enable auto-reload for development.")
@click.pass_context
def serve(ctx: click.Context, host: str, port: int, auto_reload: bool) -> None:
    """Launch the web dashboard."""
    if auto_reload:
        raise click.ClickException("--reload is not supported when serving a configured dashboard app")
    import uvicorn

    from collection_swarm.web.app import create_app

    app = create_app(config_dir=ctx.obj["config_dir"], db_path=ctx.obj["db_path"])
    console.print(f"Starting dashboard at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


@cli.command("seed")
@click.option("--count", default=24, show_default=True, type=int, help="Number of seed simulations.")
@click.pass_context
def seed_data(ctx: click.Context, count: int) -> None:
    """Generate realistic demo data for the web dashboard."""
    from collection_swarm.web.seed import generate_seed_data

    n = generate_seed_data(db_path=ctx.obj["db_path"], num_runs=count)
    console.print(f"Seeded {n} simulations into {ctx.obj['db_path']}")


@cli.command("set-key")
@click.argument("key_name")
@click.option("--value", prompt=True, hide_input=True, confirmation_prompt=True, help="The API key value.")
@click.pass_context
def set_key(ctx: click.Context, key_name: str, value: str) -> None:
    """Store an API key in the encrypted local database.

    KEY_NAME must be one of NVIDIA_NIM_API_KEY or CURSOR_API_KEY.
    """
    from collection_swarm.secrets import KNOWN_KEY_NAMES, SecretsStore

    if key_name not in KNOWN_KEY_NAMES:
        raise click.ClickException(f"Unknown key '{key_name}'. Known keys: {', '.join(sorted(KNOWN_KEY_NAMES))}")
    SecretsStore(ctx.obj["db_path"]).set_key(key_name, value)
    console.print(f"Stored {key_name} in {ctx.obj['db_path']}")


@cli.command("list-keys")
@click.pass_context
def list_keys(ctx: click.Context) -> None:
    """Show which API keys are configured (database or environment)."""
    import os

    from collection_swarm.secrets import KNOWN_KEY_NAMES, SecretsStore

    store = SecretsStore(ctx.obj["db_path"])
    stored = {item["name"]: item["updated_at"] for item in store.list_keys()}
    table = Table(title="API Keys")
    table.add_column("Key")
    table.add_column("Source")
    table.add_column("Updated")
    for name in sorted(KNOWN_KEY_NAMES):
        if name in stored:
            source = "[green]database[/green]"
            updated = stored[name]
        elif os.getenv(name):
            source = "[yellow]environment[/yellow]"
            updated = "—"
        else:
            source = "[red]not set[/red]"
            updated = "—"
        table.add_row(name, source, updated)
    console.print(table)


@cli.command("remove-key")
@click.argument("key_name")
@click.pass_context
def remove_key(ctx: click.Context, key_name: str) -> None:
    """Remove a stored API key from the database."""
    from collection_swarm.secrets import KNOWN_KEY_NAMES, SecretsStore

    if key_name not in KNOWN_KEY_NAMES:
        raise click.ClickException(f"Unknown key '{key_name}'. Known keys: {', '.join(sorted(KNOWN_KEY_NAMES))}")
    deleted = SecretsStore(ctx.obj["db_path"]).delete_key(key_name)
    if deleted:
        console.print(f"Removed {key_name} from {ctx.obj['db_path']}")
    else:
        console.print(f"{key_name} was not stored in the database.")


def _print_result(result) -> None:
    console.rule(f"Simulation {result.id} [{result.status}]")
    for turn in result.transcript:
        console.print(f"[bold]{turn.role.title()}:[/bold] {turn.content}")
    console.print(f"\nEnded by: {result.ended_by}; turns: {result.turn_count}")
    if result.judgment:
        table = Table(title="Judgment")
        table.add_column("Metric")
        table.add_column("Value")
        table.add_row("Payment outcome", result.judgment.payment_outcome)
        table.add_row("Payment probability", f"{result.judgment.payment_probability:.0%}")
        table.add_row("Debtor satisfaction", f"{result.judgment.debtor_satisfaction:.0%}")
        table.add_row("Compliance score", f"{result.judgment.compliance_score:.0%}")
        table.add_row("Rapport built", f"{result.judgment.rapport_built:.0%}")
        table.add_row("Escalation risk", f"{result.judgment.escalation_risk:.0%}")
        table.add_row("End reason", result.judgment.end_reason)
        if result.judgment.constraint_violations:
            table.add_row("Constraint violations", "; ".join(result.judgment.constraint_violations))
        console.print(table)
        console.print(result.judgment.reasoning)
    if result.error_message:
        console.print(f"[red]Error:[/red] {result.error_message}")
