"""Command-line interface for Collection Swarm."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from collection_swarm.agents.collector import CollectorAgent
from collection_swarm.agents.debtor import DebtorAgent
from collection_swarm.agents.judge import Judge
from collection_swarm.analysis.compliance import check_exclusions
from collection_swarm.analysis.playbook import generate_playbook
from collection_swarm.analysis.statistics import compare_strategies
from collection_swarm.backends.router import LLMRouter
from collection_swarm.config import load_app_config
from collection_swarm.engine import SimulationEngine
from collection_swarm.runner import build_matrix, run_matrix
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


@cli.command("list-profiles")
@click.pass_context
def list_profiles(ctx: click.Context) -> None:
    """List configured Profiles."""
    config = load_app_config(ctx.obj["config_dir"])
    table = Table(title="Profiles")
    table.add_column("ID")
    table.add_column("Archetype")
    table.add_column("Debt")
    table.add_column("Primary Objection")
    for profile in config.profiles.values():
        table.add_row(
            profile.id,
            profile.archetype,
            f"${profile.debt_amount:,.0f} {profile.debt_type}",
            profile.primary_objection,
        )
    console.print(table)


@cli.command("list-strategies")
@click.pass_context
def list_strategies(ctx: click.Context) -> None:
    """List configured Strategies."""
    config = load_app_config(ctx.obj["config_dir"])
    table = Table(title="Strategies")
    table.add_column("ID")
    table.add_column("Tone")
    table.add_column("Tactic")
    table.add_column("Follow-up")
    for strategy in config.strategies.values():
        table.add_row(strategy.id, strategy.tone, strategy.negotiation_tactic, strategy.follow_up_strategy)
    console.print(table)


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
    router = LLMRouter(config.models)
    settings = config.simulation.conversation
    engine = SimulationEngine(
        CollectorAgent(router, conversation_model),
        DebtorAgent(router, conversation_model),
        Judge(router, judge_model),
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
        LLMRouter(config.models).complete(
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
    import uvicorn

    from collection_swarm.web.app import create_app

    app = create_app(config_dir=ctx.obj["config_dir"], db_path=ctx.obj["db_path"])
    console.print(f"Starting dashboard at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=auto_reload)


@cli.command("seed")
@click.option("--count", default=24, show_default=True, type=int, help="Number of seed simulations.")
@click.pass_context
def seed_data(ctx: click.Context, count: int) -> None:
    """Generate realistic demo data for the web dashboard."""
    from collection_swarm.web.seed import generate_seed_data

    n = generate_seed_data(db_path=ctx.obj["db_path"], num_runs=count)
    console.print(f"Seeded {n} simulations into {ctx.obj['db_path']}")


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
