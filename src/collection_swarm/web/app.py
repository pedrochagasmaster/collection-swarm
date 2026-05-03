"""FastAPI application for the Collection Swarm web dashboard."""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

import bleach
import markdown
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from collection_swarm import arena
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
from collection_swarm.credentials import CredentialStore
from collection_swarm.credentials import CredentialStore
from collection_swarm.engine import SimulationEngine, stalemate_detected, strip_end_signal
from collection_swarm.model_evaluation import (
    DEFAULT_CURSOR_PROBE_MODELS,
    DEFAULT_CURSOR_SDK_MODEL_IDS,
    ProbeScenario,
    RoleProbe,
    build_model_role_report,
    report_to_dict,
    run_live_role_probes,
    write_report,
)
from collection_swarm.models import EndedBy, MatrixCell, Message, SimulationResult, TournamentConfig, TournamentResult, model_dump_jsonable, utc_now
from collection_swarm.runner import build_matrix
from collection_swarm.store import SimulationStore

STATIC_DIR = Path(__file__).parent / "static"

# Allow-listed HTML tags & attributes for rendered Markdown output.
# The Python ``markdown`` library does not strip raw HTML by default, so any
# ``<script>`` or ``onerror`` payload that finds its way into a YAML-defined
# strategy/profile/transcript would otherwise execute when injected via
# ``innerHTML`` on the client. Sanitize before returning.
_PLAYBOOK_ALLOWED_TAGS = [
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "th", "td",
    "code", "pre", "blockquote",
    "strong", "em", "a", "br", "hr", "span", "div",
]
_PLAYBOOK_ALLOWED_ATTRS = {
    "a": ["href", "title"],
    "th": ["align"],
    "td": ["align"],
    "span": ["class"],
    "div": ["class"],
    "code": ["class"],
}


def _render_safe_markdown(md_text: str) -> str:
    """Render Markdown to HTML and strip any raw HTML the Markdown contained."""
    raw_html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    return bleach.clean(
        raw_html,
        tags=_PLAYBOOK_ALLOWED_TAGS,
        attributes=_PLAYBOOK_ALLOWED_ATTRS,
        protocols=["http", "https", "mailto"],
        strip=True,
    )


class SimulationLaunchRequest(BaseModel):
    profile_id: str
    strategy_id: str
    conversation_model: str | None = None
    judge_model: str | None = None


class MatrixLaunchRequest(BaseModel):
    profile_ids: list[str] | None = None
    strategy_ids: list[str] | None = None
    conversation_models: list[str] | None = None
    judge_models: list[str] | None = None
    reps: int = Field(default=1, ge=1, le=100)
    concurrency: int = Field(default=2, ge=1, le=10)


class TournamentLaunchRequest(BaseModel):
    format: str = "swiss"
    rounds: int = Field(default=4, ge=1, le=20)
    profile_ids: list[str] | None = None
    strategy_ids: list[str] | None = None
    conversation_model: str | None = None
    judge_model: str | None = None
    reps_per_pairing: int = Field(default=1, ge=1, le=10)
    concurrency: int = Field(default=2, ge=1, le=10)

    @field_validator("format")
    @classmethod
    def validate_format(cls, value: str) -> str:
        if value not in {"swiss", "round_robin"}:
            raise ValueError("format must be swiss or round_robin")
        return value


class BenchmarkLaunchRequest(BaseModel):
    cursor_model_names: list[str] | None = None
    roles: list[str] = Field(default_factory=lambda: ["collector", "debtor", "judge"])
    profile_ids: list[str] = Field(default_factory=lambda: ["cooperative_hardship"])
    strategy_ids: list[str] = Field(default_factory=lambda: ["empathetic_payment_plan"])
    judge_profile_ids: list[str] = Field(default_factory=lambda: ["written_proof_disputer"])
    concurrency: int = Field(default=1, ge=1, le=4)

    @field_validator("roles")
    @classmethod
    def validate_roles(cls, value: list[str]) -> list[str]:
        valid = {"collector", "debtor", "judge"}
        roles = [role.lower().strip() for role in value if role.strip()]
        invalid = [role for role in roles if role not in valid]
        if invalid:
            raise ValueError(f"unknown benchmark role(s): {', '.join(invalid)}")
        if not roles:
            raise ValueError("select at least one benchmark role")
        return roles


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


class CalibrationJobRequest(BaseModel):
    labels: list[dict[str, Any]] = Field(default_factory=list)
    optimize: bool = True


class ApiKeyUpdateRequest(BaseModel):
    api_key: str = Field(min_length=1)


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
    artifacts: dict[str, str] = field(default_factory=dict)
    benchmark_report: dict[str, Any] | None = None
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
            "artifacts": self.artifacts,
            "benchmark_report": self.benchmark_report,
            "message": self.message,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
        }


def _job_cancelled_snapshot(job: WebRunJob) -> None:
    job.status = "cancelled"
    job.message = "Job cancelled."
    job.ended_at = utc_now().isoformat()


@dataclass
class ManualSession:
    id: str
    result: SimulationResult
    human_role: str
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
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
    app.state.benchmark_reports = {}
    app.state.tasks = {}
    app.state.db_path = db_path

    def _store() -> SimulationStore:
        return SimulationStore(db_path)

    def _credential_store() -> CredentialStore:
        return CredentialStore(db_path)

    def _config():
        return load_app_config(config_dir)

    def _benchmark_output_dir() -> Path:
        return db_path.parent / "benchmarks"

    def _load_saved_benchmark_reports() -> None:
        bench_dir = _benchmark_output_dir()
        if not bench_dir.is_dir():
            return
        for path in sorted(bench_dir.glob("bench_*-*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                job_id = path.stem.split("-")[0]
                if job_id not in app.state.benchmark_reports:
                    app.state.benchmark_reports[job_id] = data
            except Exception:
                pass

    _load_saved_benchmark_reports()

    def _entity_pools(config, store: SimulationStore) -> tuple[dict[str, Any], dict[str, Any]]:
        return (
            {**config.profiles, **store.get_evolved_profile_pool()},
            {**config.strategies, **store.get_evolved_strategy_pool()},
        )

    def _model_options(config) -> dict[str, Any]:
        profiles, strategies = _entity_pools(config, _store())
        conversation = []
        judge = []
        for model in config.models.values():
            item = model_dump_jsonable(model)
            if model.backend == "scripted" or model.id.startswith(("cursor-", "nim-")):
                conversation.append(item)
            if model.backend in {"heuristic", "scripted"} or model.id.startswith("cursor-"):
                judge.append(item)
        return {
            "profiles": [model_dump_jsonable(profile) for profile in profiles.values()],
            "strategies": [model_dump_jsonable(strategy) for strategy in strategies.values()],
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
    def compliance_exclusions() -> dict[str, Any]:
        store = _store()
        config = _config()
        exclusions = check_exclusions(
            store,
            list(config.profiles),
            list(config.strategies),
            min_compliance_score=config.simulation.min_compliance_score,
            max_escalation_risk=config.simulation.max_escalation_risk,
        )
        total_runs = store.count_by_status().get("completed", 0)
        exclusion_items = []
        for exclusion in exclusions:
            combo_runs = store.get_combo_runs(exclusion.profile_id, exclusion.strategy_id)
            model_pairs = sorted({(run.conversation_model, run.judge_model) for run in combo_runs})
            exclusion_items.append(
                {
                    "profile_id": exclusion.profile_id,
                    "strategy_id": exclusion.strategy_id,
                    "compliance_score": exclusion.compliance_score,
                    "escalation_risk": exclusion.escalation_risk,
                    "reason": exclusion.reason,
                    "simulation_count": len(combo_runs),
                    "run_ids": [run.id for run in combo_runs[:3]],
                    "model_pairs": [
                        {"conversation_model": conversation_model, "judge_model": judge_model}
                        for conversation_model, judge_model in model_pairs
                    ],
                }
            )
        return {
            "thresholds": {
                "min_compliance_score": config.simulation.min_compliance_score,
                "max_escalation_risk": config.simulation.max_escalation_risk,
            },
            "total_completed_runs": total_runs,
            "minimum_runs_per_combination": 3,
            "exclusions": exclusion_items,
        }

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
    def get_playbook(format: str = Query("html", description="html or markdown")) -> dict[str, Any]:
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
        completed_runs = store.list_runs(status="completed")
        simulation_count = len(completed_runs)
        conversation_models = sorted({r.conversation_model for r in completed_runs if r.conversation_model})
        judge_models = sorted({r.judge_model for r in completed_runs if r.judge_model})
        meta = {
            "simulation_count": simulation_count,
            "conversation_models": conversation_models,
            "judge_models": judge_models,
            "thresholds": {
                "min_compliance_score": config.simulation.min_compliance_score,
                "max_escalation_risk": config.simulation.max_escalation_risk,
            },
            "generated_at": utc_now().isoformat(),
        }
        if format == "markdown":
            return {"format": "markdown", "content": md_text, "meta": meta}
        return {"format": "html", "content": _render_safe_markdown(md_text), "meta": meta}

    # ── Config info ─────────────────────────────────────────────────

    @app.get("/api/config/profiles")
    def list_profiles() -> list[dict[str, Any]]:
        config = _config()
        performance = _store().get_performance_by("profile_id")
        profiles = []
        for profile in config.profiles.values():
            item = model_dump_jsonable(profile)
            item["performance"] = performance.get(profile.id)
            profiles.append(item)
        return profiles

    @app.get("/api/config/strategies")
    def list_strategies() -> list[dict[str, Any]]:
        config = _config()
        performance = _store().get_performance_by("strategy_id")
        strategies = []
        for strategy in config.strategies.values():
            item = model_dump_jsonable(strategy)
            item["performance"] = performance.get(strategy.id)
            strategies.append(item)
        return strategies

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

    @app.get("/api/config/api-keys")
    def list_api_keys() -> dict[str, Any]:
        return {"providers": [info.__dict__ for info in _credential_store().list_api_keys()]}

    @app.put("/api/config/api-keys/{provider}")
    def set_api_key(provider: str, payload: ApiKeyUpdateRequest) -> dict[str, Any]:
        try:
            info = _credential_store().set_api_key(provider, payload.api_key)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"API key provider '{provider}' not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return info.__dict__

    @app.delete("/api/config/api-keys/{provider}")
    def clear_api_key(provider: str) -> dict[str, Any]:
        try:
            return _credential_store().clear_api_key(provider).__dict__
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"API key provider '{provider}' not found") from exc

    # ── Arena / Tournament APIs ─────────────────────────────────────

    @app.get("/api/arena/leaderboard")
    def arena_leaderboard(
        entity_type: str | None = Query(None),
        conversation_model: str | None = Query(None),
        judge_model: str | None = Query(None),
    ) -> dict[str, list[dict[str, Any]]]:
        if entity_type not in {None, "strategy", "profile"}:
            raise HTTPException(status_code=400, detail="entity_type must be strategy or profile")
        store = _store()
        config = _config()
        conversation_model = conversation_model or config.default_conversation_model
        judge_model = judge_model or config.default_judge_model
        strategies = (
            []
            if entity_type == "profile"
            else store.get_elo_ratings("strategy", conversation_model, judge_model)
        )
        profiles = [] if entity_type == "strategy" else store.get_elo_ratings("profile", conversation_model, judge_model)
        return {
            "strategies": [model_dump_jsonable(rating) for rating in strategies],
            "profiles": [model_dump_jsonable(rating) for rating in profiles],
        }

    @app.get("/api/arena/history/{entity_id}")
    def arena_history(entity_id: str) -> list[dict[str, Any]]:
        return [model_dump_jsonable(update) for update in _store().get_elo_history(entity_id)]

    @app.get("/api/arena/tournaments")
    def list_tournaments() -> list[dict[str, Any]]:
        return [model_dump_jsonable(result) for result in _store().list_tournaments()]

    @app.get("/api/arena/tournaments/{tournament_id}")
    def get_tournament(tournament_id: str) -> dict[str, Any]:
        try:
            return model_dump_jsonable(_store().get_tournament(tournament_id))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get("/api/evolution/pool")
    def evolution_pool() -> dict[str, list[dict[str, Any]]]:
        strategies = []
        for strategy, lineage in _store().list_evolved_strategies():
            item = model_dump_jsonable(strategy)
            item["lineage"] = model_dump_jsonable(lineage)
            strategies.append(item)
        profiles = []
        for profile, lineage in _store().list_evolved_profiles():
            item = model_dump_jsonable(profile)
            item["lineage"] = model_dump_jsonable(lineage)
            profiles.append(item)
        return {"strategies": strategies, "profiles": profiles}

    @app.get("/api/calibration/results")
    def calibration_results() -> dict[str, Any]:
        from collection_swarm.calibration import evaluate_judge

        return model_dump_jsonable(evaluate_judge(_store().list_calibration_labels(), _store()))

    @app.post("/api/calibration/labels")
    def upload_calibration_labels(payload: list[dict[str, Any]]) -> dict[str, Any]:
        from collection_swarm.calibration import CalibrationLabel

        labels = [CalibrationLabel.model_validate(item) for item in payload]
        _store().save_calibration_labels(labels)
        return {"saved": len(labels)}

    @app.post("/api/jobs/calibration")
    async def launch_calibration(payload: CalibrationJobRequest) -> dict[str, Any]:
        job = WebRunJob(
            id=f"calib_{uuid4().hex[:10]}",
            kind="calibration",
            status="queued",
            total=1,
            message="Queued calibration evaluation.",
        )
        app.state.jobs[job.id] = job
        app.state.tasks[job.id] = asyncio.create_task(_run_calibration_job(job, _config(), _store(), payload))
        return job.snapshot()

    @app.get("/api/calibration/variants")
    def calibration_variants() -> list[dict[str, Any]]:
        return _store().list_judge_variants()

    # ── Model benchmark APIs ────────────────────────────────────────

    @app.get("/api/model-benchmarks/options")
    def benchmark_options() -> dict[str, Any]:
        config = _config()
        return {
            "cursor_models": list(DEFAULT_CURSOR_SDK_MODEL_IDS),
            "default_cursor_models": list(DEFAULT_CURSOR_PROBE_MODELS),
            "roles": ["collector", "debtor", "judge"],
            "profiles": [model_dump_jsonable(profile) for profile in config.profiles.values()],
            "strategies": [model_dump_jsonable(strategy) for strategy in config.strategies.values()],
            "defaults": {
                "profile_ids": ["cooperative_hardship"],
                "strategy_ids": ["empathetic_payment_plan"],
                "judge_profile_ids": ["written_proof_disputer"],
                "concurrency": 1,
            },
        }

    @app.get("/api/model-benchmarks")
    def list_benchmark_reports() -> list[dict[str, Any]]:
        reports = []
        for job_id, report in reversed(list(app.state.benchmark_reports.items())):
            reports.append(
                {
                    "job_id": job_id,
                    "title": report.get("title"),
                    "generated_at": report.get("generated_at"),
                    "recommendations": report.get("recommendations", {}),
                    "probe_count": len(report.get("probes", [])),
                }
            )
        return reports

    @app.get("/api/model-benchmarks/{job_id}")
    def get_benchmark_report(job_id: str) -> dict[str, Any]:
        report = app.state.benchmark_reports.get(job_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Model benchmark '{job_id}' not found")
        return report

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
            _run_single_job(
                job,
                config,
                _store(),
                payload.profile_id,
                payload.strategy_id,
                conversation_model,
                judge_model,
                _credential_store(),
            )
        )
        return job.snapshot()

    @app.post("/api/jobs/matrix")
    async def launch_matrix(payload: MatrixLaunchRequest) -> dict[str, Any]:
        config = _config()
        profile_ids = payload.profile_ids if payload.profile_ids is not None else list(config.profiles)
        strategy_ids = payload.strategy_ids if payload.strategy_ids is not None else list(config.strategies)
        conversation_models = (
            payload.conversation_models if payload.conversation_models is not None else [config.default_conversation_model]
        )
        judge_models = payload.judge_models if payload.judge_models is not None else [config.default_judge_model]
        if not profile_ids:
            raise HTTPException(status_code=400, detail="Select at least one profile")
        if not strategy_ids:
            raise HTTPException(status_code=400, detail="Select at least one strategy")
        if not conversation_models:
            raise HTTPException(status_code=400, detail="Select at least one conversation model")
        if not judge_models:
            raise HTTPException(status_code=400, detail="Select at least one judge model")
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
        app.state.tasks[job.id] = asyncio.create_task(
            _run_matrix_job(job, config, _store(), cells, payload.concurrency, _credential_store())
        )
        return job.snapshot()

    @app.post("/api/jobs/tournaments")
    async def launch_tournament(payload: TournamentLaunchRequest) -> dict[str, Any]:
        config = _config()
        store = _store()
        profiles = {**config.profiles, **store.get_evolved_profile_pool()}
        strategies = {**config.strategies, **store.get_evolved_strategy_pool()}
        profile_ids = payload.profile_ids if payload.profile_ids is not None else list(profiles)
        strategy_ids = payload.strategy_ids if payload.strategy_ids is not None else list(strategies)
        conversation_model = payload.conversation_model or config.default_conversation_model
        judge_model = payload.judge_model or config.default_judge_model
        if not profile_ids:
            raise HTTPException(status_code=400, detail="Select at least one profile")
        if not strategy_ids:
            raise HTTPException(status_code=400, detail="Select at least one strategy")
        try:
            for profile_id in profile_ids:
                if profile_id not in profiles:
                    config.profile(profile_id)
            for strategy_id in strategy_ids:
                if strategy_id not in strategies:
                    config.strategy(strategy_id)
            config.model(conversation_model)
            config.model(judge_model)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if payload.format == "round_robin":
            pairings_per_round = len(strategy_ids) * len(profile_ids)
        else:
            pairings_per_round = min(len(strategy_ids), len(profile_ids))
        total = pairings_per_round * payload.rounds * payload.reps_per_pairing
        job = WebRunJob(
            id=f"tournjob_{uuid4().hex[:10]}",
            kind="tournament",
            status="queued",
            total=total,
            message=f"Queued {total} tournament simulations.",
        )
        app.state.jobs[job.id] = job
        app.state.tasks[job.id] = asyncio.create_task(
            _run_tournament_job(
                job,
                config,
                store,
                TournamentConfig(
                    format=payload.format,  # type: ignore[arg-type]
                    rounds=payload.rounds,
                    reps_per_pairing=payload.reps_per_pairing,
                    k_factor_initial=config.simulation.arena.k_factor_initial,
                    k_factor_stable=config.simulation.arena.k_factor_stable,
                    k_factor_threshold=config.simulation.arena.k_factor_threshold,
                    scoring=config.simulation.arena.scoring,
                ),
                profile_ids,
                strategy_ids,
                conversation_model,
                judge_model,
                payload.concurrency,
                _credential_store(),
            )
        )
        return job.snapshot()

    @app.post("/api/jobs/model-benchmarks")
    async def launch_model_benchmark(payload: BenchmarkLaunchRequest) -> dict[str, Any]:
        config = _config()
        if not payload.profile_ids:
            raise HTTPException(status_code=400, detail="Select at least one profile")
        if not payload.strategy_ids:
            raise HTTPException(status_code=400, detail="Select at least one strategy")
        if not payload.judge_profile_ids:
            raise HTTPException(status_code=400, detail="Select at least one judge profile")
        try:
            for pid in payload.profile_ids:
                config.profile(pid)
            for sid in payload.strategy_ids:
                config.strategy(sid)
            for jpid in payload.judge_profile_ids:
                config.profile(jpid)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        cursor_model_names = payload.cursor_model_names or list(DEFAULT_CURSOR_PROBE_MODELS)
        cursor_model_names = [name.strip() for name in cursor_model_names if name.strip()]
        if not cursor_model_names:
            raise HTTPException(status_code=400, detail="Select at least one Cursor model")

        non_judge_roles = [r for r in payload.roles if r != "judge"]
        has_judge = "judge" in payload.roles
        conv_scenarios = len(payload.profile_ids) * len(payload.strategy_ids)
        judge_scenarios = len(payload.judge_profile_ids)
        total_probes = len(cursor_model_names) * (
            len(non_judge_roles) * conv_scenarios + (judge_scenarios if has_judge else 0)
        )

        job = WebRunJob(
            id=f"bench_{uuid4().hex[:10]}",
            kind="model_benchmark",
            status="queued",
            total=total_probes,
            message=f"Queued {len(cursor_model_names)} model benchmark across {conv_scenarios} conversation scenario{'s' if conv_scenarios != 1 else ''} and {judge_scenarios} judge scenario{'s' if judge_scenarios != 1 else ''}.",
        )
        app.state.jobs[job.id] = job
        app.state.tasks[job.id] = asyncio.create_task(
            _run_model_benchmark_job(
                job,
                config,
                app.state.benchmark_reports,
                _benchmark_output_dir(),
                cursor_model_names,
                payload.roles,
                payload.profile_ids,
                payload.strategy_ids,
                payload.judge_profile_ids,
                payload.concurrency,
                CredentialStore(db_path),
            )
        )
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

    @app.post("/api/jobs/{job_id}/cancel")
    async def cancel_job(job_id: str) -> dict[str, Any]:
        job = app.state.jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found")
        if job.status not in {"queued", "running"}:
            return job.snapshot()
        job.status = "cancelled"
        job.message = "Job cancelled by user."
        job.ended_at = utc_now().isoformat()
        task = app.state.tasks.get(job_id)
        if task and not task.done():
            task.cancel()
        return job.snapshot()

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
            await _append_ai_turn(session, config, role="collector", api_keys=_credential_store())
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
        async with session.lock:
            if session.status == "completed":
                raise HTTPException(status_code=400, detail="Manual session is already completed")
            if session.status != "waiting_for_human":
                raise HTTPException(status_code=409, detail=f"Manual session is {session.status}")

            config = _config()
            settings = config.simulation.conversation
            content, ended = strip_end_signal(payload.content, settings.end_signal)
            session.result.transcript.append(Message(role=session.human_role, content=content))
            session.result.turn_count = len(session.result.transcript)
            if ended:
                session.result.ended_by = EndedBy(session.human_role)
                await _finish_manual_session(session, config, _store(), _credential_store())
                return session.snapshot()
            if len(session.result.transcript) >= settings.max_turns:
                session.result.ended_by = EndedBy.TURN_LIMIT
                await _finish_manual_session(session, config, _store(), _credential_store())
                return session.snapshot()

            ai_role = "debtor" if session.human_role == "collector" else "collector"
            await _append_ai_turn(session, config, ai_role, api_keys=_credential_store())
            if session.result.ended_by or len(session.result.transcript) >= settings.max_turns:
                session.result.ended_by = session.result.ended_by or EndedBy.TURN_LIMIT
                await _finish_manual_session(session, config, _store(), _credential_store())
            elif stalemate_detected(
                session.result.transcript,
                settings.stalemate_window,
                settings.stalemate_similarity_threshold,
            ):
                session.result.ended_by = EndedBy.STALEMATE
                await _finish_manual_session(session, config, _store(), _credential_store())
            else:
                session.status = "waiting_for_human"
                session.message = f"Waiting for human {session.human_role} turn."
            return session.snapshot()

    @app.post("/api/manual-sessions/{session_id}/finish")
    async def finish_manual_session(session_id: str) -> dict[str, Any]:
        session = app.state.manual_sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail=f"Manual session '{session_id}' not found")
        async with session.lock:
            if session.status == "completed":
                return session.snapshot()
            if session.status != "waiting_for_human":
                raise HTTPException(status_code=409, detail=f"Manual session is {session.status}")
            if not session.result.transcript:
                raise HTTPException(status_code=400, detail="Manual session has no turns to judge")
            session.result.ended_by = session.result.ended_by or EndedBy.TURN_LIMIT
            await _finish_manual_session(session, _config(), _store(), _credential_store())
            return session.snapshot()

    # ── SPA entry point ─────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    def index():
        index_path = STATIC_DIR / "index.html"
        return index_path.read_text(encoding="utf-8")

    return app


def create_app_from_env() -> FastAPI:
    """Factory used by uvicorn reload, which requires an import string."""
    return create_app(
        config_dir=Path(os.environ.get("COLLECTION_SWARM_CONFIG_DIR", "config")),
        db_path=Path(os.environ.get("COLLECTION_SWARM_DB_PATH", "output/collection_swarm.sqlite")),
    )


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
    api_keys: CredentialStore,
) -> None:
    try:
        job.status = "running"
        job.message = "Simulation running."
        engine = _make_engine(config, conversation_model, judge_model, api_keys=api_keys)

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
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        _fail_job(job, exc)


async def _run_matrix_job(
    job: WebRunJob,
    config,
    store: SimulationStore,
    cells: list[MatrixCell],
    concurrency: int,
    api_keys: CredentialStore,
) -> None:
    try:
        job.status = "running"
        job.message = "Matrix run in progress."
        semaphore = asyncio.Semaphore(concurrency)
        lock = asyncio.Lock()

        async def run_cell(cell: MatrixCell) -> None:
            async with semaphore:
                try:
                    engine = _make_engine(config, cell.conversation_model, cell.judge_model, api_keys=api_keys)

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
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    async with lock:
                        job.failed += 1
                        job.errors.append(f"{cell.profile_id} x {cell.strategy_id}: {exc}")
                        job.message = f"{job.completed + job.failed}/{job.total} simulations finished."

        await asyncio.gather(*(run_cell(cell) for cell in cells))
        job.status = "completed" if job.failed == 0 else "failed"
        job.message = f"Matrix finished: {job.completed} completed, {job.failed} failed."
        job.ended_at = utc_now().isoformat()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        _fail_job(job, exc)


async def _run_tournament_job(
    job: WebRunJob,
    config,
    store: SimulationStore,
    tournament_config: TournamentConfig,
    profile_ids: list[str],
    strategy_ids: list[str],
    conversation_model: str,
    judge_model: str,
    concurrency: int,
    api_keys: CredentialStore,
) -> None:
    try:
        job.status = "running"
        job.message = "Tournament in progress."
        history: set[tuple[str, str]] = set()
        semaphore = asyncio.Semaphore(concurrency)
        lock = asyncio.Lock()
        result = TournamentResult(config=tournament_config)
        total_cost = 0.0
        profiles = {**config.profiles, **store.get_evolved_profile_pool()}
        strategies = {**config.strategies, **store.get_evolved_strategy_pool()}

        async def run_cell(cell: MatrixCell) -> SimulationResult:
            async with semaphore:
                engine = _make_engine(config, cell.conversation_model, cell.judge_model, api_keys=api_keys)

                async def on_progress(partial: SimulationResult) -> None:
                    partial.turn_count = len(partial.transcript)
                    async with lock:
                        job.current_run = partial.model_copy(
                            update={"status": "running" if partial.ended_at is None else partial.status}
                        )
                        job.message = f"Running round {result.rounds_completed + 1}: {cell.strategy_id} x {cell.profile_id}."

                return await engine.run_simulation(
                    profiles[cell.profile_id],
                    strategies[cell.strategy_id],
                    on_progress=on_progress,
                )

        for round_number in range(1, tournament_config.rounds + 1):
            strategy_ratings = [
                store.get_elo_rating("strategy", strategy_id, conversation_model, judge_model)
                for strategy_id in strategy_ids
            ]
            profile_ratings = [
                store.get_elo_rating("profile", profile_id, conversation_model, judge_model)
                for profile_id in profile_ids
            ]
            pairings = (
                arena.round_robin_pairings(strategy_ids, profile_ids)
                if tournament_config.format == "round_robin"
                else arena.swiss_pairings(strategy_ratings, profile_ratings, history)
            )
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
            simulations = await asyncio.gather(*(run_cell(cell) for cell in cells), return_exceptions=True)
            for item in simulations:
                async with lock:
                    if isinstance(item, Exception):
                        job.failed += 1
                        job.errors.append(str(item))
                        continue
                    simulation = item
                    store.save_run(simulation)
                    job.result_ids.append(simulation.id)
                    job.current_run = simulation
                    total_cost += simulation.estimated_cost_usd
                    history.add((simulation.strategy_id, simulation.profile_id))
                    if simulation.status == "completed":
                        job.completed += 1
                    else:
                        job.failed += 1
                        job.errors.append(simulation.error_message or f"{simulation.id} failed")
                    if simulation.judgment is not None:
                        updates = arena.update_ratings(
                            store.get_elo_rating(
                                "strategy",
                                simulation.strategy_id,
                                simulation.conversation_model,
                                simulation.judge_model,
                            ),
                            store.get_elo_rating(
                                "profile",
                                simulation.profile_id,
                                simulation.conversation_model,
                                simulation.judge_model,
                            ),
                            simulation.judgment,
                            simulation.id,
                            scoring=tournament_config.scoring,
                            k_factor_initial=tournament_config.k_factor_initial,
                            k_factor_stable=tournament_config.k_factor_stable,
                            k_factor_threshold=tournament_config.k_factor_threshold,
                        )
                        for update in updates:
                            store.save_elo_update(update, tournament_id=result.id)
                    job.message = f"{job.completed + job.failed}/{job.total} tournament simulations finished."
            result.rounds_completed = round_number
            result.total_games = job.completed + job.failed
            result.total_cost_usd = total_cost

        result.completed_at = utc_now()
        store.save_tournament(result)
        job.status = "completed" if job.failed == 0 else "failed"
        job.message = f"Tournament finished: {job.completed} completed, {job.failed} failed."
        job.ended_at = utc_now().isoformat()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        _fail_job(job, exc)


async def _run_calibration_job(
    job: WebRunJob,
    config,
    store: SimulationStore,
    payload: CalibrationJobRequest,
) -> None:
    try:
        from collection_swarm.calibration import CalibrationLabel, evaluate_judge

        job.status = "running"
        labels = [CalibrationLabel.model_validate(item) for item in payload.labels]
        if labels:
            store.save_calibration_labels(labels)
        result = evaluate_judge(store.list_calibration_labels(), store)
        if payload.optimize:
            store.save_judge_variant(
                config.prompts.judge.system,
                config.prompts.judge.transcript,
                calibration_score=result.overall_score,
            )
        job.completed = 1
        job.status = "completed"
        job.message = f"Calibration completed with {result.label_count} labels."
        job.ended_at = utc_now().isoformat()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        _fail_job(job, exc)


async def _run_model_benchmark_job(
    job: WebRunJob,
    config,
    report_registry: dict[str, dict[str, Any]],
    output_dir: Path,
    cursor_model_names: list[str],
    roles: list[str],
    profile_ids: list[str],
    strategy_ids: list[str],
    judge_profile_ids: list[str],
    concurrency: int,
    api_keys: CredentialStore,
) -> None:
    try:
        job.status = "running"
        job.message = "Benchmark probes running."
        all_probes: list[RoleProbe] = []
        non_judge_roles = tuple(r for r in roles if r != "judge")
        has_judge = "judge" in roles
        primary_scenario = ProbeScenario(
            profile_id=profile_ids[0],
            strategy_id=strategy_ids[0],
            judge_profile_id=judge_profile_ids[0],
        )

        if has_judge:
            for jpid in judge_profile_ids:
                judge_scenario = ProbeScenario(
                    profile_id=profile_ids[0],
                    strategy_id=strategy_ids[0],
                    judge_profile_id=jpid,
                )
                judge_probes = await run_live_role_probes(
                    config,
                    cursor_model_names=tuple(cursor_model_names),
                    roles=("judge",),
                    scenario=judge_scenario,
                    concurrency=concurrency,
                    api_keys=api_keys,
                )
                all_probes.extend(judge_probes)
                ok = sum(1 for p in judge_probes if p.status == "ok")
                job.completed += ok
                job.failed += len(judge_probes) - ok
            job.message = f"Judge probes done; running scenario probes ({len(profile_ids)} profiles x {len(strategy_ids)} strategies)."

        if non_judge_roles:
            for pid in profile_ids:
                for sid in strategy_ids:
                    scenario = ProbeScenario(
                        profile_id=pid,
                        strategy_id=sid,
                        judge_profile_id=judge_profile_ids[0],
                    )
                    probes = await run_live_role_probes(
                        config,
                        cursor_model_names=tuple(cursor_model_names),
                        roles=non_judge_roles,
                        scenario=scenario,
                        concurrency=concurrency,
                        api_keys=api_keys,
                    )
                    all_probes.extend(probes)
                    ok = sum(1 for p in probes if p.status == "ok")
                    job.completed += ok
                    job.failed += len(probes) - ok
                    job.message = f"{job.completed + job.failed}/{job.total} probes finished."

        ok_count = sum(1 for probe in all_probes if probe.status == "ok")
        failed_count = len(all_probes) - ok_count
        report = build_model_role_report(
            config,
            probes=tuple(all_probes),
            scenario=primary_scenario,
            title="Production Cursor Model Role Benchmark",
        )
        stamp = utc_now().strftime("%Y%m%d-%H%M%S")
        markdown_path = output_dir / f"{job.id}-{stamp}.md"
        json_path = output_dir / f"{job.id}-{stamp}.json"
        write_report(report, markdown_path, report_format="markdown")
        write_report(report, json_path, report_format="json")
        report_data = report_to_dict(report)
        report_registry[job.id] = report_data

        job.completed = ok_count
        job.failed = failed_count
        job.status = "completed" if failed_count == 0 else "failed"
        job.message = f"Benchmark finished: {ok_count} probes completed, {failed_count} failed."
        job.artifacts = {"markdown": str(markdown_path), "json": str(json_path)}
        job.benchmark_report = report_data
        job.ended_at = utc_now().isoformat()
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        _fail_job(job, exc)


def _fail_job(job: WebRunJob, exc: Exception) -> None:
    job.status = "failed"
    job.failed = job.failed or max(1, job.total - job.completed)
    job.errors.append(str(exc))
    job.message = str(exc) or "Job failed."
    job.ended_at = utc_now().isoformat()


def _make_engine(
    config,
    conversation_model: str,
    judge_model: str,
    api_keys: CredentialStore | None = None,
) -> SimulationEngine:
    router = LLMRouter(config.models, cursor_sdk_prompts=config.prompts.cursor_sdk, api_keys=api_keys)
    settings = config.simulation.conversation
    return SimulationEngine(
        collector=CollectorAgent(router, conversation_model, config.prompts.collector),
        debtor=DebtorAgent(router, conversation_model, config.prompts.debtor),
        judge=Judge(router, judge_model, config.prompts.judge),
        max_turns=settings.max_turns,
        end_signal=settings.end_signal,
        stalemate_window=settings.stalemate_window,
        stalemate_similarity_threshold=settings.stalemate_similarity_threshold,
    )


async def _append_ai_turn(
    session: ManualSession,
    config,
    role: str,
    api_keys: CredentialStore | None = None,
) -> None:
    session.status = "ai_thinking"
    session.message = f"AI {role} is responding."
    result = session.result
    router = LLMRouter(config.models, cursor_sdk_prompts=config.prompts.cursor_sdk, api_keys=api_keys)
    profile = config.profile(result.profile_id)
    settings = config.simulation.conversation
    if role == "collector":
        agent = CollectorAgent(router, result.conversation_model, config.prompts.collector)
        response = await agent.generate_turn(config.strategy(result.strategy_id), profile.account_data, result.transcript)
    else:
        agent = DebtorAgent(router, result.conversation_model, config.prompts.debtor)
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


async def _finish_manual_session(
    session: ManualSession,
    config,
    store: SimulationStore,
    api_keys: CredentialStore | None = None,
) -> None:
    session.status = "judging"
    session.message = "Judging manual run."
    result = session.result
    result.turn_count = len(result.transcript)
    result.ended_by = result.ended_by or EndedBy.TURN_LIMIT
    judge = Judge(
        LLMRouter(config.models, cursor_sdk_prompts=config.prompts.cursor_sdk, api_keys=api_keys),
        result.judge_model,
        config.prompts.judge,
    )
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
