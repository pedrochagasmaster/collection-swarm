"""SQLite persistence and analytical queries."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from collection_swarm.models import (
    EndedBy,
    Judgment,
    MatrixCell,
    Message,
    PaymentOutcome,
    SimulationResult,
    StrategyStats,
    model_dump_jsonable,
)

class SimulationStore:
    def __init__(self, path: Path | str = "output/collection_swarm.sqlite") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    profile_id TEXT NOT NULL,
                    strategy_id TEXT NOT NULL,
                    conversation_model TEXT NOT NULL,
                    judge_model TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    turn_count INTEGER,
                    ended_by TEXT,
                    transcript_json TEXT,
                    judge_reasoning TEXT,
                    payment_outcome TEXT,
                    payment_probability REAL,
                    debtor_satisfaction REAL,
                    compliance_score REAL,
                    conversation_efficiency INTEGER,
                    rapport_built REAL,
                    escalation_risk REAL,
                    end_reason TEXT,
                    constraint_violations_json TEXT,
                    total_input_tokens INTEGER,
                    total_output_tokens INTEGER,
                    estimated_cost_usd REAL
                )
                """
            )

    def save_run(self, result: SimulationResult) -> None:
        judgment = result.judgment
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO runs (
                    id, status, error_message, profile_id, strategy_id, conversation_model, judge_model,
                    started_at, ended_at, turn_count, ended_by, transcript_json, judge_reasoning,
                    payment_outcome, payment_probability, debtor_satisfaction, compliance_score,
                    conversation_efficiency, rapport_built, escalation_risk, end_reason,
                    constraint_violations_json, total_input_tokens, total_output_tokens, estimated_cost_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.id,
                    result.status,
                    result.error_message,
                    result.profile_id,
                    result.strategy_id,
                    result.conversation_model,
                    result.judge_model,
                    result.started_at.isoformat(),
                    result.ended_at.isoformat() if result.ended_at else None,
                    result.turn_count,
                    _enum_value(result.ended_by),
                    json.dumps([model_dump_jsonable(message) for message in result.transcript]),
                    judgment.reasoning if judgment else None,
                    _enum_value(judgment.payment_outcome) if judgment else None,
                    judgment.payment_probability if judgment else None,
                    judgment.debtor_satisfaction if judgment else None,
                    judgment.compliance_score if judgment else None,
                    judgment.conversation_efficiency if judgment else None,
                    judgment.rapport_built if judgment else None,
                    judgment.escalation_risk if judgment else None,
                    judgment.end_reason if judgment else None,
                    json.dumps(judgment.constraint_violations if judgment else []),
                    result.total_input_tokens,
                    result.total_output_tokens,
                    result.estimated_cost_usd,
                ),
            )

    def get_run(self, run_id: str) -> SimulationResult:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown simulation '{run_id}'")
        return _result_from_row(row)

    def list_runs(self, status: str | None = "completed") -> list[SimulationResult]:
        sql = "SELECT * FROM runs"
        params: tuple[Any, ...] = ()
        if status:
            sql += " WHERE status = ?"
            params = (status,)
        sql += " ORDER BY started_at"
        with self._connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [_result_from_row(row) for row in rows]

    def get_strategy_comparison(self, profile_id: str) -> list[StrategyStats]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT profile_id, strategy_id, COUNT(*) AS simulation_count,
                       AVG(payment_probability) AS mean_payment_probability,
                       AVG(compliance_score) AS mean_compliance_score,
                       AVG(escalation_risk) AS mean_escalation_risk
                FROM runs
                WHERE status = 'completed' AND profile_id = ? AND payment_probability IS NOT NULL
                GROUP BY profile_id, strategy_id
                ORDER BY mean_payment_probability DESC
                """,
                (profile_id,),
            ).fetchall()
        return [StrategyStats.model_validate(dict(row)) for row in rows]

    def get_payment_probability_samples(self, profile_id: str) -> dict[str, list[float]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT strategy_id, payment_probability
                FROM runs
                WHERE status = 'completed' AND profile_id = ? AND payment_probability IS NOT NULL
                ORDER BY strategy_id, started_at
                """,
                (profile_id,),
            ).fetchall()
        samples: dict[str, list[float]] = {}
        for row in rows:
            samples.setdefault(str(row["strategy_id"]), []).append(float(row["payment_probability"]))
        return samples

    def get_matrix_coverage(self) -> dict[MatrixCell, int]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT profile_id, strategy_id, conversation_model, judge_model, COUNT(*) AS completed
                FROM runs
                WHERE status = 'completed'
                GROUP BY profile_id, strategy_id, conversation_model, judge_model
                """
            ).fetchall()
        return {
            MatrixCell(
                profile_id=row["profile_id"],
                strategy_id=row["strategy_id"],
                conversation_model=row["conversation_model"],
                judge_model=row["judge_model"],
            ): int(row["completed"])
            for row in rows
        }

    def get_backfill_needed(
        self,
        target_reps: int,
        cells: list[MatrixCell],
    ) -> list[MatrixCell]:
        coverage = self.get_matrix_coverage()
        needed: list[MatrixCell] = []
        for cell in cells:
            remaining = max(0, target_reps - coverage.get(cell, 0))
            needed.extend([cell] * remaining)
        return needed

    def get_best_transcript(self, profile_id: str, strategy_id: str) -> list[Message]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT transcript_json FROM runs
                WHERE status = 'completed' AND profile_id = ? AND strategy_id = ?
                ORDER BY payment_probability DESC, compliance_score DESC
                LIMIT 1
                """,
                (profile_id, strategy_id),
            ).fetchone()
        if row is None:
            return []
        return [Message.model_validate(item) for item in json.loads(row["transcript_json"] or "[]")]

    def get_all_transcripts(self, profile_id: str, strategy_id: str) -> list[list[Message]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT transcript_json FROM runs
                WHERE status = 'completed' AND profile_id = ? AND strategy_id = ?
                """,
                (profile_id, strategy_id),
            ).fetchall()
        return [[Message.model_validate(item) for item in json.loads(row["transcript_json"] or "[]")] for row in rows]

    def get_compliance_summary(self, profile_id: str, strategy_id: str) -> dict[str, float]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT AVG(compliance_score) AS compliance_score, AVG(escalation_risk) AS escalation_risk
                FROM runs
                WHERE status = 'completed' AND profile_id = ? AND strategy_id = ?
                """,
                (profile_id, strategy_id),
            ).fetchone()
        return {
            "compliance_score": float(row["compliance_score"] or 0.0),
            "escalation_risk": float(row["escalation_risk"] or 0.0),
        }

    def get_cost_summary(self) -> dict[str, float]:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS simulations, SUM(total_input_tokens) AS input_tokens,
                       SUM(total_output_tokens) AS output_tokens, SUM(estimated_cost_usd) AS cost
                FROM runs
                """
            ).fetchone()
        return {
            "simulations": float(row["simulations"] or 0),
            "input_tokens": float(row["input_tokens"] or 0),
            "output_tokens": float(row["output_tokens"] or 0),
            "estimated_cost_usd": float(row["cost"] or 0.0),
        }

    def count_by_status(self) -> dict[str, int]:
        with self._connect() as connection:
            rows = connection.execute("SELECT status, COUNT(*) AS count FROM runs GROUP BY status").fetchall()
        return {str(row["status"]): int(row["count"]) for row in rows}


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    return getattr(value, "value", value)


def _result_from_row(row: sqlite3.Row) -> SimulationResult:
    judgment = None
    if row["payment_outcome"] is not None:
        judgment = Judgment(
            reasoning=row["judge_reasoning"] or "",
            payment_outcome=PaymentOutcome(row["payment_outcome"]),
            payment_probability=float(row["payment_probability"] or 0.0),
            debtor_satisfaction=float(row["debtor_satisfaction"] or 0.0),
            compliance_score=float(row["compliance_score"] or 0.0),
            conversation_efficiency=int(row["conversation_efficiency"] or 0),
            rapport_built=float(row["rapport_built"] or 0.0),
            escalation_risk=float(row["escalation_risk"] or 0.0),
            end_reason=row["end_reason"] or "no_resolution",
            constraint_violations=json.loads(row["constraint_violations_json"] or "[]"),
        )
    return SimulationResult(
        id=row["id"],
        status=row["status"],
        error_message=row["error_message"],
        profile_id=row["profile_id"],
        strategy_id=row["strategy_id"],
        conversation_model=row["conversation_model"],
        judge_model=row["judge_model"],
        turn_count=int(row["turn_count"] or 0),
        started_at=datetime.fromisoformat(row["started_at"]),
        ended_at=datetime.fromisoformat(row["ended_at"]) if row["ended_at"] else None,
        ended_by=EndedBy(row["ended_by"]) if row["ended_by"] else None,
        transcript=[Message.model_validate(item) for item in json.loads(row["transcript_json"] or "[]")],
        judgment=judgment,
        total_input_tokens=int(row["total_input_tokens"] or 0),
        total_output_tokens=int(row["total_output_tokens"] or 0),
        estimated_cost_usd=float(row["estimated_cost_usd"] or 0.0),
    )
