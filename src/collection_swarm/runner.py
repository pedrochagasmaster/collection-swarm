"""Run orchestration for multiple Simulations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from collection_swarm.agents.collector import CollectorAgent
from collection_swarm.agents.debtor import DebtorAgent
from collection_swarm.agents.judge import Judge
from collection_swarm.backends.router import LLMRouter
from collection_swarm.config import AppConfig
from collection_swarm.engine import SimulationEngine
from collection_swarm.models import MatrixCell, SimulationResult
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
    router = LLMRouter(config.models)
    semaphore = asyncio.Semaphore(concurrency)

    async def run_cell(cell: MatrixCell) -> SimulationResult:
        async with semaphore:
            settings = config.simulation.conversation
            engine = SimulationEngine(
                collector=CollectorAgent(router, cell.conversation_model),
                debtor=DebtorAgent(router, cell.conversation_model),
                judge=Judge(router, cell.judge_model),
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
