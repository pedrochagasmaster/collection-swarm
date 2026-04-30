"""FastAPI application for the Collection Swarm web dashboard."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

import markdown
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from collection_swarm.agents.collector import CollectorAgent
from collection_swarm.agents.debtor import DebtorAgent
from collection_swarm.agents.judge import Judge
from collection_swarm.analysis.compliance import check_exclusions
from collection_swarm.analysis.objections import extract_objections
from collection_swarm.analysis.playbook import generate_playbook
from collection_swarm.analysis.statistics import compare_strategies
from collection_swarm.backends.base import LLMResponse
from collection_swarm.backends.router import LLMRouter
from collection_swarm.config import load_app_config
from collection_swarm.engine import SimulationEngine, stalemate_detected, strip_end_signal
from collection_swarm.models import EndedBy, MatrixCell, Message, SimulationResult, model_dump_jsonable, utc_now
from collection_swarm.runner import build_matrix
from collection_swarm.store import SimulationStore

STATIC_DIR = Path(__file__).parent / "static"


class SimulationLaunchRequest(BaseModel):
    profile_id: str
    strategy_id: str
    conversation_model: str | None = None
    judge_model: str | None = None


class MatrixLaunchRequest(BaseModel):
    profile_ids: list[str] = Field(default_factory=list)
    strategy_ids: list[str] = Field(default_factory=list)
    conversation_models: list[str] = Field(default_factory=list)
    judge_models: list[str] = Field(default_factory=list)
    reps: int = Field(default=1, ge=1, le=100)
    concurrency: int = Field(default=2, ge=1, le=10)


class ManualSessionRequest(BaseModel):
    profile_id: str
    strategy_id: str
    human_role: str
    conversation_model: str | None = None
    judge_model: str | None = None

    @field_validator("human_role")
    @classmethod
    def validate_human_role(cls, value: str) -> str:
        if value not in {"collector", "debtor"}:
            raise ValueError("human_role must be collector or debtor")
        return value


class ManualTurnRequest(BaseModel):
    content: str = Field(min_length=1)


@dataclass
class WebRunJob:
    id: str
    kind: str
    status: str
    total: int = 1
    completed: int = 0
    failed: int = 0
    current_run: SimulationResult | None = None
    result_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    message: str = ""
    started_at: str = field(default_factory=lambda: utc_now().isoformat())
    ended_at: str | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "total": self.total,
            "completed": self.completed,
            "failed": self.failed,
            "current_run": model_dump_jsonable(self.current_run) if self.current_run else None,
            "result_ids": self.result_ids,
            "errors": self.errors[-5:],
            "message": self.message,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }


@dataclass
class ManualSession:
    id: str
    result: SimulationResult
    human_role: str
    status: str = "waiting_for_human"
    message: str = ""
    ended_at: str | None = None

    def snapshot(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "human_role": self.human_role,
            "message": self.message,
            "run": model_dump_jsonable(self.result),
            "ended_at": self.ended_at,
        }


def create_app(
    config_dir: Path = Path("config"),
    db_path: Path = Path("output/collection_swarm.sqlite"),
) -> FastAPI:
    app = FastAPI(title="Collection Swarm Dashboard", version="0.1.0")
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.state.jobs = {}
    app.state.manual_sessions = {}
    app.state.tasks = {}

    def _store() -> SimulationStore:
        return SimulationStore(db_path)

    def _config():
        return load_app_config(config_dir)

    def _model_options(config) -> dict[str, Any]:
        conversation = []
        judge = []
        for model in config.models.values():
            item = model_dump_jsonable(model)
            if model.backend == "scripted" or model.id.startswith(("cursor-", "nim-")):
                conversation.append(item)
            if model.backend in {"heuristic", "scripted"} or model.id.startswith("cursor-"):
                judge.append(item)
        return {
            "profiles": [model_dump_jsonable(profile) for profile in config.profiles.values()],
            "strategies": [model_dump_jsonable(strategy) for strategy in config.strategies.values()],
            "conversation_models": conversation,
            "judge_models": judge,
            "defaults": {
                "conversation_model": config.default_conversation_model,
                "judge_model": config.default_judge_model,
                "reps": config.simulation.default_repetitions,
            },
        }

    # ── Dashboard overview ──────────────────────────────────────────

    @app.get("/api/dashboard")
    def dashboard_overview() -> dict[str, Any]:
        store = _store()
        config = _config()
        status_counts = store.count_by_status()
        cost = store.get_cost_summary()
        runs = store.list_runs(status="completed")

        outcome_counts: dict[str, int] = {}
        score_sums: dict[str, float] = {
            "payment_probability": 0,
            "compliance_score": 0,
            "debtor_satisfaction": 0,
            "escalation_risk": 0,
            "rapport_built": 0,
        }
        judged = 0
        for r in runs:
            if r.judgment:
                judged += 1
                outcome_counts[r.judgment.payment_outcome] = (
                    outcome_counts.get(r.judgment.payment_outcome, 0) + 1
                )
                score_sums["payment_probability"] += r.judgment.payment_probability
                score_sums["compliance_score"] += r.judgment.compliance_score
                score_sums["debtor_satisfaction"] += r.judgment.debtor_satisfaction
                score_sums["escalation_risk"] += r.judgment.escalation_risk
                score_sums["rapport_built"] += r.judgment.rapport_built

        avg_scores = {k: (v / judged if judged else 0) for k, v in score_sums.items()}

        return {
            "total_runs": sum(status_counts.values()),
            "completed": status_counts.get("completed", 0),
            "failed": status_counts.get("failed", 0),
            "profiles": list(config.profiles.keys()),
            "strategies": list(config.strategies.keys()),
            "outcome_distribution": outcome_counts,
            "average_scores": avg_scores,
            "cost": cost,
        }

    # ── Runs list ───────────────────────────────────────────────────

    @app.get("/api/runs")
    def list_runs(
        status: str | None = Query(None, description="Filter by status"),
        profile_id: str | None = Query(None),
        strategy_id: str | None = Query(None),
    ) -> list[dict[str, Any]]:
        store = _store()
        runs = store.list_runs(status=status)
        if profile_id:
            runs = [r for r in runs if r.profile_id == profile_id]
        if strategy_id:
            runs = [r for r in runs if r.strategy_id == strategy_id]
        results = []
        for r in runs:
            item: dict[str, Any] = {
                "id": r.id,
                "status": r.status,
                "profile_id": r.profile_id,
                "strategy_id": r.strategy_id,
                "conversation_model": r.conversation_model,
                "judge_model": r.judge_model,
                "turn_count": r.turn_count,
                "ended_by": r.ended_by,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "ended_at": r.ended_at.isoformat() if r.ended_at else None,
                "total_input_tokens": r.total_input_tokens,
                "total_output_tokens": r.total_output_tokens,
                "estimated_cost_usd": r.estimated_cost_usd,
                "error_message": r.error_message,
            }
            if r.judgment:
                item["judgment"] = {
                    "payment_outcome": r.judgment.payment_outcome,
                    "payment_probability": r.judgment.payment_probability,
                    "compliance_score": r.judgment.compliance_score,
                    "debtor_satisfaction": r.judgment.debtor_satisfaction,
                    "escalation_risk": r.judgment.escalation_risk,
                    "rapport_built": r.judgment.rapport_built,
                    "end_reason": r.judgment.end_reason,
                }
            results.append(item)
        return results

    # ── Single run detail with transcript ───────────────────────────

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str) -> dict[str, Any]:
        store = _store()
        try:
            r = store.get_run(run_id)
        except KeyError:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        result = json.loads(r.model_dump_json())
        result["started_at"] = r.started_at.isoformat() if r.started_at else None
        result["ended_at"] = r.ended_at.isoformat() if r.ended_at else None
        return result

    # ── Strategy comparison per profile ─────────────────────────────

    @app.get("/api/profiles/{profile_id}/strategies")
    def strategy_comparison(profile_id: str) -> dict[str, Any]:
        store = _store()
        ranking = compare_strategies(profile_id, store)
        return {
            "profile_id": ranking.profile_id,
            "recommended": ranking.recommended_strategy_id,
            "strategies": [model_dump_jsonable(s) for s in ranking.strategies],
        }

    # ── Compliance exclusions ───────────────────────────────────────

    @app.get("/api/compliance/exclusions")
    def compliance_exclusions() -> list[dict[str, Any]]:
        store = _store()
        config = _config()
        exclusions = check_exclusions(
            store,
            list(config.profiles),
            list(config.strategies),
            min_compliance_score=config.simulation.min_compliance_score,
            max_escalation_risk=config.simulation.max_escalation_risk,
        )
        return [
            {
                "profile_id": e.profile_id,
                "strategy_id": e.strategy_id,
                "compliance_score": e.compliance_score,
                "escalation_risk": e.escalation_risk,
                "reason": e.reason,
            }
            for e in exclusions
        ]

    # ── Objection analysis ──────────────────────────────────────────

    @app.get("/api/profiles/{profile_id}/objections")
    def objection_analysis(
        profile_id: str,
        strategy_id: str | None = Query(None),
    ) -> dict[str, Any]:
        store = _store()
        config = _config()
        strat_id = strategy_id
        if not strat_id:
            ranking = compare_strategies(profile_id, store)
            strat_id = ranking.recommended_strategy_id
        if not strat_id:
            return {"profile_id": profile_id, "strategy_id": None, "objections": {}}
        transcripts = store.get_all_transcripts(profile_id, strat_id)
        report = extract_objections(transcripts)
        return {
            "profile_id": profile_id,
            "strategy_id": strat_id,
            "objections": report.objections,
        }

    # ── Playbook (rendered) ─────────────────────────────────────────

    @app.get("/api/playbook")
    def get_playbook(format: str = Query("html", description="html or markdown")) -> dict[str, str]:
        store = _store()
        config = _config()
        rankings = [compare_strategies(pid, store) for pid in config.profiles]
        exclusions = check_exclusions(
            store,
            list(config.profiles),
            list(config.strategies),
            min_compliance_score=config.simulation.min_compliance_score,
            max_escalation_risk=config.simulation.max_escalation_risk,
        )
        md_text = generate_playbook(rankings, exclusions, store)
        if format == "markdown":
            return {"format": "markdown", "content": md_text}
        html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
        return {"format": "html", "content": html}

    # ── Config info ─────────────────────────────────────────────────

    @app.get("/api/config/profiles")
    def list_profiles() -> list[dict[str, Any]]:
        config = _config()
        return [model_dump_jsonable(p) for p in config.profiles.values()]

    @app.get("/api/config/strategies")
    def list_strategies() -> list[dict[str, Any]]:
        config = _config()
        return [model_dump_jsonable(s) for s in config.strategies.values()]

    @app.get("/api/config/models")
    def list_models() -> dict[str, Any]:
        config = _config()
        models = [model_dump_jsonable(model) for model in config.models.values()]
        return {
            "models": models,
            "default_conversation_model": config.default_conversation_model,
            "default_judge_model": config.default_judge_model,
        }

    @app.get("/api/config/run-options")
    def run_options() -> dict[str, Any]:
        return _model_options(_config())

    # ── Run launch and progress APIs ────────────────────────────────

    @app.post("/api/jobs/simulations")
    async def launch_simulation(payload: SimulationLaunchRequest) -> dict[str, Any]:
        config = _config()
        conversation_model = payload.conversation_model or config.default_conversation_model
        judge_model = payload.judge_model or config.default_judge_model
        _validate_run_choices(config, payload.profile_id, payload.strategy_id, conversation_model, judge_model)

        job = WebRunJob(
            id=f"job_{uuid4().hex[:10]}",
            kind="single",
            status="queued",
            total=1,
            message="Queued single simulation.",
        )
        app.state.jobs[job.id] = job
        app.state.tasks[job.id] = asyncio.create_task(
            _run_single_job(job, config, _store(), payload.profile_id, payload.strategy_id, conversation_model, judge_model)
        )
        return job.snapshot()

    @app.post("/api/jobs/matrix")
    async def launch_matrix(payload: MatrixLaunchRequest) -> dict[str, Any]:
        config = _config()
        profile_ids = payload.profile_ids or list(config.profiles)
        strategy_ids = payload.strategy_ids or list(config.strategies)
        conversation_models = payload.conversation_models or [config.default_conversation_model]
        judge_models = payload.judge_models or [config.default_judge_model]
        try:
            cells = build_matrix(
                config,
                profile_ids=profile_ids,
                strategy_ids=strategy_ids,
                conversation_models=conversation_models,
                judge_models=judge_models,
                reps=payload.reps,
            )
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        job = WebRunJob(
            id=f"job_{uuid4().hex[:10]}",
            kind="matrix",
            status="queued",
            total=len(cells),
            message=f"Queued {len(cells)} matrix simulations.",
        )
        app.state.jobs[job.id] = job
        app.state.tasks[job.id] = asyncio.create_task(_run_matrix_job(job, config, _store(), cells, payload.concurrency))
        return job.snapshot()

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, Any]:
        job = app.state.jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
        return job.snapshot()

    @app.get("/api/jobs")
    def list_jobs() -> list[dict[str, Any]]:
        return [job.snapshot() for job in reversed(list(app.state.jobs.values()))]

    # ── Manual role-play sessions ───────────────────────────────────

    @app.post("/api/manual-sessions")
    async def create_manual_session(payload: ManualSessionRequest) -> dict[str, Any]:
        config = _config()
        conversation_model = payload.conversation_model or config.default_conversation_model
        judge_model = payload.judge_model or config.default_judge_model
        _validate_run_choices(config, payload.profile_id, payload.strategy_id, conversation_model, judge_model)

        result = SimulationResult(
            status="running",
            profile_id=payload.profile_id,
            strategy_id=payload.strategy_id,
            conversation_model=conversation_model,
            judge_model=judge_model,
        )
        session = ManualSession(
            id=f"manual_{uuid4().hex[:10]}",
            result=result,
            human_role=payload.human_role,
            message=f"Waiting for human {payload.human_role} turn.",
        )
        app.state.manual_sessions[session.id] = session
        if payload.human_role == "debtor":
            await _append_ai_turn(session, config, role="collector")
            if session.status != "completed":
                session.status = "waiting_for_human"
                session.message = "Waiting for human debtor turn."
        return session.snapshot()

    @app.get("/api/manual-sessions/{session_id}")
    def get_manual_session(session_id: str) -> dict[str, Any]:
        session = app.state.manual_sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Manual session '{session_id}' not found")
        return session.snapshot()

    @app.post("/api/manual-sessions/{session_id}/turn")
    async def submit_manual_turn(session_id: str, payload: ManualTurnRequest) -> dict[str, Any]:
        session = app.state.manual_sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Manual session '{session_id}' not found")
        if session.status == "completed":
            raise HTTPException(status_code=400, detail="Manual session is already completed")

        config = _config()
        settings = config.simulation.conversation
        content, ended = strip_end_signal(payload.content, settings.end_signal)
        session.result.transcript.append(Message(role=session.human_role, content=content))
        session.result.turn_count = len(session.result.transcript)
        if ended:
            session.result.ended_by = EndedBy(session.human_role)
            await _finish_manual_session(session, config, _store())
            return session.snapshot()
        if len(session.result.transcript) >= settings.max_turns:
            session.result.ended_by = EndedBy.TURN_LIMIT
            await _finish_manual_session(session, config, _store())
            return session.snapshot()

        ai_role = "debtor" if session.human_role == "collector" else "collector"
        await _append_ai_turn(session, config, ai_role)
        if session.result.ended_by or len(session.result.transcript) >= settings.max_turns:
            session.result.ended_by = session.result.ended_by or EndedBy.TURN_LIMIT
            await _finish_manual_session(session, config, _store())
        elif stalemate_detected(
            session.result.transcript,
            settings.stalemate_window,
            settings.stalemate_similarity_threshold,
        ):
            session.result.ended_by = EndedBy.STALEMATE
            await _finish_manual_session(session, config, _store())
        else:
            session.status = "waiting_for_human"
            session.message = f"Waiting for human {session.human_role} turn."
        return session.snapshot()

    @app.post("/api/manual-sessions/{session_id}/finish")
    async def finish_manual_session(session_id: str) -> dict[str, Any]:
        session = app.state.manual_sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Manual session '{session_id}' not found")
        if session.status != "completed":
            session.result.ended_by = session.result.ended_by or EndedBy.TURN_LIMIT
            await _finish_manual_session(session, _config(), _store())
        return session.snapshot()

    # ── SPA entry point ─────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    def index():
        index_path = STATIC_DIR / "index.html"
        return index_path.read_text(encoding="utf-8")

    return app


def _validate_run_choices(
    config,
    profile_id: str,
    strategy_id: str,
    conversation_model: str,
    judge_model: str,
) -> None:
    try:
        config.profile(profile_id)
        config.strategy(strategy_id)
        config.model(conversation_model)
        config.model(judge_model)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def _run_single_job(
    job: WebRunJob,
    config,
    store: SimulationStore,
    profile_id: str,
    strategy_id: str,
    conversation_model: str,
    judge_model: str,
) -> None:
    job.status = "running"
    job.message = "Simulation running."
    engine = _make_engine(config, conversation_model, judge_model)

    async def on_progress(result: SimulationResult) -> None:
        result.turn_count = len(result.transcript)
        job.current_run = result.model_copy(update={"status": "running" if result.ended_at is None else result.status})
        job.message = f"{result.turn_count} turn{'s' if result.turn_count != 1 else ''} recorded."

    result = await engine.run_simulation(config.profile(profile_id), config.strategy(strategy_id), on_progress=on_progress)
    store.save_run(result)
    job.current_run = result
    job.result_ids = [result.id]
    job.completed = 1 if result.status == "completed" else 0
    job.failed = 1 if result.status == "failed" else 0
    job.status = "completed" if result.status == "completed" else "failed"
    job.message = "Simulation completed." if result.status == "completed" else result.error_message or "Simulation failed."
    job.ended_at = utc_now().isoformat()


async def _run_matrix_job(
    job: WebRunJob,
    config,
    store: SimulationStore,
    cells: list[MatrixCell],
    concurrency: int,
) -> None:
    job.status = "running"
    job.message = "Matrix run in progress."
    semaphore = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()

    async def run_cell(cell: MatrixCell) -> None:
        async with semaphore:
            engine = _make_engine(config, cell.conversation_model, cell.judge_model)

            async def on_progress(result: SimulationResult) -> None:
                result.turn_count = len(result.transcript)
                async with lock:
                    job.current_run = result.model_copy(
                        update={"status": "running" if result.ended_at is None else result.status}
                    )
                    job.message = f"Running {cell.profile_id} x {cell.strategy_id}; {job.completed + job.failed}/{job.total} finished."

            result = await engine.run_simulation(config.profile(cell.profile_id), config.strategy(cell.strategy_id), on_progress=on_progress)
            store.save_run(result)
            async with lock:
                job.result_ids.append(result.id)
                if result.status == "completed":
                    job.completed += 1
                else:
                    job.failed += 1
                    job.errors.append(result.error_message or f"{result.id} failed")
                job.current_run = result
                job.message = f"{job.completed + job.failed}/{job.total} simulations finished."

    await asyncio.gather(*(run_cell(cell) for cell in cells))
    job.status = "completed" if job.failed == 0 else "failed"
    job.message = f"Matrix finished: {job.completed} completed, {job.failed} failed."
    job.ended_at = utc_now().isoformat()


def _make_engine(config, conversation_model: str, judge_model: str) -> SimulationEngine:
    router = LLMRouter(config.models)
    settings = config.simulation.conversation
    return SimulationEngine(
        collector=CollectorAgent(router, conversation_model),
        debtor=DebtorAgent(router, conversation_model),
        judge=Judge(router, judge_model),
        max_turns=settings.max_turns,
        end_signal=settings.end_signal,
        stalemate_window=settings.stalemate_window,
        stalemate_similarity_threshold=settings.stalemate_similarity_threshold,
    )


async def _append_ai_turn(session: ManualSession, config, role: str) -> None:
    session.status = "ai_thinking"
    session.message = f"AI {role} is responding."
    result = session.result
    router = LLMRouter(config.models)
    profile = config.profile(result.profile_id)
    settings = config.simulation.conversation
    if role == "collector":
        agent = CollectorAgent(router, result.conversation_model)
        response = await agent.generate_turn(config.strategy(result.strategy_id), profile.account_data, result.transcript)
    else:
        agent = DebtorAgent(router, result.conversation_model)
        response = await agent.generate_turn(profile, result.transcript)
    _append_response(result, role, response, settings.end_signal)
    result.turn_count = len(result.transcript)


def _append_response(result: SimulationResult, role: str, response: LLMResponse, end_signal: str) -> None:
    result.total_input_tokens += response.input_tokens
    result.total_output_tokens += response.output_tokens
    result.estimated_cost_usd += response.estimated_cost_usd
    content, ended = strip_end_signal(response.content, end_signal)
    result.transcript.append(Message(role=role, content=content))
    if ended:
        result.ended_by = EndedBy(role)


async def _finish_manual_session(session: ManualSession, config, store: SimulationStore) -> None:
    session.status = "judging"
    session.message = "Judging manual run."
    result = session.result
    result.turn_count = len(result.transcript)
    result.ended_by = result.ended_by or EndedBy.TURN_LIMIT
    judge = Judge(LLMRouter(config.models), result.judge_model)
    result.judgment = await judge.evaluate(result.transcript, config.profile(result.profile_id))
    if judge.last_response:
        result.total_input_tokens += judge.last_response.input_tokens
        result.total_output_tokens += judge.last_response.output_tokens
        result.estimated_cost_usd += judge.last_response.estimated_cost_usd
    result.status = "completed"
    result.ended_at = utc_now()
    store.save_run(result)
    session.status = "completed"
    session.message = "Manual run saved."
    session.ended_at = utc_now().isoformat()
