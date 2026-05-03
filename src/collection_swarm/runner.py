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
from collection_swarm.credentials import ApiKeyProvider
from collection_swarm.engine import SimulationEngine
from collection_swarm.adversarial import harden_profiles
from collection_swarm.evolution import cull_strategies, evolve_strategies
from collection_swarm.models import EvolutionConfig, HardeningConfig, MatrixCell, ProfileLineage, SimulationResult, StrategyLineage, TournamentConfig, TournamentResult, utc_now
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
    api_keys: ApiKeyProvider | None = None,
) -> RunSummary:
    router = LLMRouter(config.models, cursor_sdk_prompts=config.prompts.cursor_sdk, api_keys=api_keys)
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
    api_keys: ApiKeyProvider | None = None,
) -> TournamentResult:
    conversation_model = conversation_model or config.default_conversation_model
    judge_model = judge_model or config.default_judge_model
    config.model(conversation_model)
    config.model(judge_model)

    profiles = profile_ids or list(config.profiles)
    strategies = strategy_ids or list(config.strategies)
    strategy_pool = {**config.strategies, **store.get_evolved_strategy_pool()}
    profile_pool = {**config.profiles, **store.get_evolved_profile_pool()}
    for profile_id in profiles:
        if profile_id not in profile_pool:
            config.profile(profile_id)
    for strategy_id in strategies:
        if strategy_id not in strategy_pool:
            config.strategy(strategy_id)

    result = TournamentResult(config=tournament_config)
    history: set[tuple[str, str]] = set()
    total_cost = 0.0
    router = LLMRouter(config.models, cursor_sdk_prompts=config.prompts.cursor_sdk, api_keys=api_keys)
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
            return await engine.run_simulation(profile_pool[cell.profile_id], strategy_pool[cell.strategy_id])

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


async def run_evolution_cycle(
    config: AppConfig,
    store: SimulationStore,
    evolution_config: EvolutionConfig,
    tournament_config: TournamentConfig,
    generations: int = 5,
    profile_ids: list[str] | None = None,
    strategy_ids: list[str] | None = None,
    hardening_config: HardeningConfig | None = None,
    conversation_model: str | None = None,
    judge_model: str | None = None,
    concurrency: int = 2,
    on_generation_complete: Callable[[int, TournamentResult], Awaitable[None]] | None = None,
    api_keys: ApiKeyProvider | None = None,
) -> list[TournamentResult]:
    router = LLMRouter(config.models, cursor_sdk_prompts=config.prompts.cursor_sdk, api_keys=api_keys)
    results: list[TournamentResult] = []
    active_strategy_ids = list(strategy_ids or config.strategies)
    active_profile_ids = list(profile_ids or config.profiles)
    for generation in range(1, generations + 1):
        tournament = await run_tournament(
            config,
            store,
            tournament_config,
            profile_ids=active_profile_ids,
            strategy_ids=active_strategy_ids,
            conversation_model=conversation_model,
            judge_model=judge_model,
            concurrency=concurrency,
        )
        results.append(tournament)
        ratings = store.get_elo_ratings("strategy", conversation_model or config.default_conversation_model, judge_model or config.default_judge_model)
        sorted_ids = [rating.entity_id for rating in ratings if rating.entity_id in active_strategy_ids]
        if not sorted_ids:
            sorted_ids = active_strategy_ids
        all_strategies = {**config.strategies, **store.get_evolved_strategy_pool()}
        top = [all_strategies[strategy_id] for strategy_id in sorted_ids[: evolution_config.top_k] if strategy_id in all_strategies]
        bottom = [all_strategies[strategy_id] for strategy_id in sorted_ids[-evolution_config.bottom_k :] if strategy_id in all_strategies]
        failed_runs = [
            run
            for run in store.list_runs(status="completed")
            if run.strategy_id in {strategy.id for strategy in bottom} and run.transcript
        ]
        failure_transcripts = [
            "\n".join(f"{message.role}: {message.content}" for message in run.transcript)
            for run in failed_runs[:5]
        ]
        evolved = await evolve_strategies(top, bottom, failure_transcripts, evolution_config, router)
        for strategy in evolved:
            lineage = StrategyLineage(
                strategy_id=strategy.id,
                parent_ids=[s.id for s in top[:2]],
                generation=generation,
                mutation_type="llm",
                mutation_description="Generated from tournament leaderboard feedback.",
            )
            store.save_evolved_strategy(strategy, lineage)
            if strategy.id not in active_strategy_ids:
                active_strategy_ids.append(strategy.id)
        if evolution_config.cull_bottom_n:
            active_evolved = store.list_evolved_strategies()
            lineages = {lineage.strategy_id: lineage for _, lineage in active_evolved}
            rating_map = {rating.entity_id: rating.rating for rating in ratings}
            all_strategies = {**config.strategies, **store.get_evolved_strategy_pool()}
            kept = cull_strategies(
                [all_strategies[strategy_id] for strategy_id in active_strategy_ids if strategy_id in all_strategies],
                rating_map,
                keep_n=max(0, evolution_config.population_size - len(config.strategies)),
                lineages=lineages,
            )
            kept_ids = {strategy.id for strategy in kept}
            for strategy, lineage in active_evolved:
                if lineage.generation > 0 and strategy.id not in kept_ids:
                    store.cull_evolved_strategy(strategy.id)
                    if strategy.id in active_strategy_ids:
                        active_strategy_ids.remove(strategy.id)
        if hardening_config and hardening_config.enabled:
            profile_pool = {**config.profiles, **store.get_evolved_profile_pool()}
            seed_profiles = [profile_pool[profile_id] for profile_id in active_profile_ids if profile_id in profile_pool]
            hardened = await harden_profiles(seed_profiles[: evolution_config.bottom_k], [], hardening_config, router)
            for profile in hardened:
                parent_id = seed_profiles[0].id if seed_profiles else None
                lineage = ProfileLineage(
                    profile_id=profile.id,
                    parent_id=parent_id,
                    generation=generation,
                    hardening_type="llm",
                    hardening_description="Generated from successful collection transcripts.",
                )
                store.save_evolved_profile(profile, lineage)
                if profile.id not in active_profile_ids:
                    active_profile_ids.append(profile.id)
        if on_generation_complete is not None:
            await on_generation_complete(generation, tournament)
    return results
