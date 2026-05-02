"""Run orchestration for multiple Simulations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from collections.abc import Awaitable, Callable

from collection_swarm import arena
from collection_swarm.agents.collector import CollectorAgent
from collection_swarm.agents.debtor import DebtorAgent
from collection_swarm.agents.judge import Judge
from collection_swarm.backends.router import LLMRouter
from collection_swarm.config import AppConfig
from collection_swarm.engine import SimulationEngine
from collection_swarm.models import MatrixCell, SimulationResult, TournamentConfig, TournamentResult, utc_now
from collection_swarm.store import SimulationStore


@dataclass(frozen=True)
class RunSummary:
    completed: int
    failed: int
    total: int
    results: list[SimulationResult]


def build_matrix(
    config: AppConfig,
    profile_ids: list[str] | None = None,
    strategy_ids: list[str] | None = None,
    conversation_models: list[str] | None = None,
    judge_models: list[str] | None = None,
    reps: int = 1,
) -> list[MatrixCell]:
    profiles = profile_ids or list(config.profiles)
    strategies = strategy_ids or list(config.strategies)
    conversation_models = conversation_models or [config.default_conversation_model]
    judge_models = judge_models or [config.default_judge_model]

    cells: list[MatrixCell] = []
    for profile_id in profiles:
        config.profile(profile_id)
        for strategy_id in strategies:
            config.strategy(strategy_id)
            for conversation_model in conversation_models:
                config.model(conversation_model)
                for judge_model in judge_models:
                    config.model(judge_model)
                    for _ in range(reps):
                        cells.append(
                            MatrixCell(
                                profile_id=profile_id,
                                strategy_id=strategy_id,
                                conversation_model=conversation_model,
                                judge_model=judge_model,
                            )
                        )
    return cells


async def run_matrix(
    config: AppConfig,
    store: SimulationStore,
    cells: list[MatrixCell],
    concurrency: int = 2,
) -> RunSummary:
    router = LLMRouter(config.models, cursor_sdk_prompts=config.prompts.cursor_sdk)
    semaphore = asyncio.Semaphore(concurrency)

    async def run_cell(cell: MatrixCell) -> SimulationResult:
        async with semaphore:
            settings = config.simulation.conversation
            engine = SimulationEngine(
                collector=CollectorAgent(router, cell.conversation_model, config.prompts.collector),
                debtor=DebtorAgent(router, cell.conversation_model, config.prompts.debtor),
                judge=Judge(router, cell.judge_model, config.prompts.judge),
                max_turns=settings.max_turns,
                end_signal=settings.end_signal,
                stalemate_window=settings.stalemate_window,
                stalemate_similarity_threshold=settings.stalemate_similarity_threshold,
            )
            return await engine.run_simulation(config.profile(cell.profile_id), config.strategy(cell.strategy_id))

    results = await asyncio.gather(*(run_cell(cell) for cell in cells))
    store.save_runs(list(results))
    completed = sum(1 for result in results if result.status == "completed")
    failed = len(results) - completed
    return RunSummary(completed=completed, failed=failed, total=len(results), results=list(results))


async def run_tournament(
    config: AppConfig,
    store: SimulationStore,
    tournament_config: TournamentConfig,
    profile_ids: list[str] | None = None,
    strategy_ids: list[str] | None = None,
    conversation_model: str | None = None,
    judge_model: str | None = None,
    concurrency: int = 2,
    on_round_complete: Callable[[TournamentResult], Awaitable[None]] | None = None,
) -> TournamentResult:
    conversation_model = conversation_model or config.default_conversation_model
    judge_model = judge_model or config.default_judge_model
    config.model(conversation_model)
    config.model(judge_model)

    profiles = profile_ids or list(config.profiles)
    strategies = strategy_ids or list(config.strategies)
    for profile_id in profiles:
        config.profile(profile_id)
    for strategy_id in strategies:
        config.strategy(strategy_id)

    result = TournamentResult(config=tournament_config)
    history: set[tuple[str, str]] = set()
    total_cost = 0.0
    router = LLMRouter(config.models, cursor_sdk_prompts=config.prompts.cursor_sdk)
    semaphore = asyncio.Semaphore(concurrency)

    async def run_cell(cell: MatrixCell) -> SimulationResult:
        async with semaphore:
            settings = config.simulation.conversation
            engine = SimulationEngine(
                collector=CollectorAgent(router, cell.conversation_model, config.prompts.collector),
                debtor=DebtorAgent(router, cell.conversation_model, config.prompts.debtor),
                judge=Judge(router, cell.judge_model, config.prompts.judge),
                max_turns=settings.max_turns,
                end_signal=settings.end_signal,
                stalemate_window=settings.stalemate_window,
                stalemate_similarity_threshold=settings.stalemate_similarity_threshold,
            )
            return await engine.run_simulation(config.profile(cell.profile_id), config.strategy(cell.strategy_id))

    for round_number in range(1, tournament_config.rounds + 1):
        strategy_ratings = [
            store.get_elo_rating("strategy", strategy_id, conversation_model, judge_model) for strategy_id in strategies
        ]
        profile_ratings = [
            store.get_elo_rating("profile", profile_id, conversation_model, judge_model) for profile_id in profiles
        ]
        if tournament_config.format == "round_robin":
            pairings = arena.round_robin_pairings(strategies, profiles)
        else:
            pairings = arena.swiss_pairings(strategy_ratings, profile_ratings, history)
        cells = [
            MatrixCell(
                profile_id=profile_id,
                strategy_id=strategy_id,
                conversation_model=conversation_model,
                judge_model=judge_model,
            )
            for strategy_id, profile_id in pairings
            for _ in range(tournament_config.reps_per_pairing)
        ]
        results = await asyncio.gather(*(run_cell(cell) for cell in cells))
        store.save_runs(list(results))
        for simulation in results:
            total_cost += simulation.estimated_cost_usd
            history.add((simulation.strategy_id, simulation.profile_id))
            if simulation.judgment is None:
                continue
            strategy_rating = store.get_elo_rating(
                "strategy",
                simulation.strategy_id,
                simulation.conversation_model,
                simulation.judge_model,
            )
            profile_rating = store.get_elo_rating(
                "profile",
                simulation.profile_id,
                simulation.conversation_model,
                simulation.judge_model,
            )
            updates = arena.update_ratings(
                strategy_rating,
                profile_rating,
                simulation.judgment,
                simulation.id,
                scoring=tournament_config.scoring,
                k_factor_initial=tournament_config.k_factor_initial,
                k_factor_stable=tournament_config.k_factor_stable,
                k_factor_threshold=tournament_config.k_factor_threshold,
            )
            for update in updates:
                store.save_elo_update(update, tournament_id=result.id)
        result.rounds_completed = round_number
        result.total_games += len(results)
        result.total_cost_usd = total_cost
        if on_round_complete is not None:
            await on_round_complete(result)

    result.completed_at = utc_now()
    store.save_tournament(result)
    return result
