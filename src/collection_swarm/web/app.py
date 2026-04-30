"""FastAPI application for the Collection Swarm web dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import markdown
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from collection_swarm.analysis.compliance import check_exclusions
from collection_swarm.analysis.objections import extract_objections
from collection_swarm.analysis.playbook import generate_playbook
from collection_swarm.analysis.statistics import compare_strategies
from collection_swarm.config import load_app_config
from collection_swarm.models import model_dump_jsonable
from collection_swarm.store import SimulationStore

STATIC_DIR = Path(__file__).parent / "static"


def create_app(
    config_dir: Path = Path("config"),
    db_path: Path = Path("output/collection_swarm.sqlite"),
) -> FastAPI:
    app = FastAPI(title="Collection Swarm Dashboard", version="0.1.0")
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    def _store() -> SimulationStore:
        return SimulationStore(db_path)

    def _config():
        return load_app_config(config_dir)

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

    # ── SPA entry point ─────────────────────────────────────────────

    @app.get("/", response_class=HTMLResponse)
    def index():
        index_path = STATIC_DIR / "index.html"
        return index_path.read_text(encoding="utf-8")

    return app
