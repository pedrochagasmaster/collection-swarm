"""SQLite persistence and analytical queries."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from collection_swarm.models import (
    DRAW_THRESHOLD,
    EndedBy,
    EloRating,
    EloUpdate,
    Judgment,
    MatrixCell,
    Message,
    PaymentOutcome,
    SimulationResult,
    StrategyStats,
    TournamentConfig,
    TournamentResult,
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
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS elo_ratings (
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    conversation_model TEXT NOT NULL DEFAULT '',
                    judge_model TEXT NOT NULL DEFAULT '',
                    rating REAL NOT NULL,
                    games_played INTEGER NOT NULL,
                    wins INTEGER NOT NULL,
                    losses INTEGER NOT NULL,
                    draws INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (entity_type, entity_id, conversation_model, judge_model)
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS elo_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id TEXT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    opponent_id TEXT NOT NULL,
                    conversation_model TEXT NOT NULL DEFAULT '',
                    judge_model TEXT NOT NULL DEFAULT '',
                    simulation_id TEXT NOT NULL,
                    rating_before REAL NOT NULL,
                    rating_after REAL NOT NULL,
                    effective_score REAL NOT NULL,
                    expected_score REAL NOT NULL,
                    timestamp TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS tournaments (
                    id TEXT PRIMARY KEY,
                    config_json TEXT NOT NULL,
                    rounds_completed INTEGER NOT NULL,
                    total_games INTEGER NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    total_cost_usd REAL NOT NULL
                )
                """
            )
            self._ensure_column(connection, "elo_ratings", "conversation_model", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "elo_ratings", "judge_model", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "elo_history", "conversation_model", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "elo_history", "judge_model", "TEXT NOT NULL DEFAULT ''")

    def _ensure_column(self, connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def save_run(self, result: SimulationResult) -> None:
        self.save_runs([result])

    def save_runs(self, results: list[SimulationResult]) -> None:
        if not results:
            return
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT OR REPLACE INTO runs (
                    id, status, error_message, profile_id, strategy_id, conversation_model, judge_model,
                    started_at, ended_at, turn_count, ended_by, transcript_json, judge_reasoning,
                    payment_outcome, payment_probability, debtor_satisfaction, compliance_score,
                    conversation_efficiency, rapport_built, escalation_risk, end_reason,
                    constraint_violations_json, total_input_tokens, total_output_tokens, estimated_cost_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [_run_row(result) for result in results],
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

    def get_combo_runs(
        self,
        profile_id: str,
        strategy_id: str,
        conversation_model: str | None = None,
        judge_model: str | None = None,
    ) -> list[SimulationResult]:
        sql = """
                SELECT * FROM runs
                WHERE status = 'completed' AND profile_id = ? AND strategy_id = ?
                """
        params: list[Any] = [profile_id, strategy_id]
        if conversation_model:
            sql += " AND conversation_model = ?"
            params.append(conversation_model)
        if judge_model:
            sql += " AND judge_model = ?"
            params.append(judge_model)
        sql += " ORDER BY compliance_score ASC, escalation_risk DESC, started_at DESC"
        with self._connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return [_result_from_row(row) for row in rows]

    def get_performance_by(self, dimension: str) -> dict[str, dict[str, float]]:
        if dimension not in {"profile_id", "strategy_id", "conversation_model", "judge_model"}:
            raise ValueError("unsupported performance dimension")
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT {dimension} AS id,
                       COUNT(*) AS run_count,
                       AVG(payment_probability) AS payment_probability,
                       AVG(compliance_score) AS compliance_score
                FROM runs
                WHERE status = 'completed' AND payment_probability IS NOT NULL
                GROUP BY {dimension}
                """
            ).fetchall()
        return {
            str(row["id"]): {
                "run_count": float(row["run_count"] or 0),
                "payment_probability": float(row["payment_probability"] or 0.0),
                "compliance_score": float(row["compliance_score"] or 0.0),
            }
            for row in rows
        }

    def get_elo_ratings(
        self,
        entity_type: str | None = None,
        conversation_model: str | None = None,
        judge_model: str | None = None,
    ) -> list[EloRating]:
        sql = "SELECT * FROM elo_ratings"
        filters: list[str] = []
        params: list[Any] = []
        if entity_type is not None:
            filters.append("entity_type = ?")
            params.append(entity_type)
        if conversation_model is not None:
            filters.append("conversation_model = ?")
            params.append(conversation_model)
        if judge_model is not None:
            filters.append("judge_model = ?")
            params.append(judge_model)
        if filters:
            sql += " WHERE " + " AND ".join(filters)
        sql += " ORDER BY rating DESC, entity_id"
        with self._connect() as connection:
            rows = connection.execute(sql, tuple(params)).fetchall()
        return [EloRating.model_validate(dict(row)) for row in rows]

    def get_elo_rating(
        self,
        entity_type: str,
        entity_id: str,
        conversation_model: str = "",
        judge_model: str = "",
    ) -> EloRating:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM elo_ratings
                WHERE entity_type = ? AND entity_id = ? AND conversation_model = ? AND judge_model = ?
                """,
                (entity_type, entity_id, conversation_model, judge_model),
            ).fetchone()
        if row is None:
            return EloRating(
                entity_type=entity_type,  # type: ignore[arg-type]
                entity_id=entity_id,
                conversation_model=conversation_model,
                judge_model=judge_model,
            )
        return EloRating.model_validate(dict(row))

    def save_elo_update(self, update: EloUpdate, tournament_id: str | None = None) -> None:
        current = self.get_elo_rating(
            update.entity_type,
            update.entity_id,
            update.conversation_model,
            update.judge_model,
        )
        wins = current.wins
        losses = current.losses
        draws = current.draws
        if update.effective_score > 0.5 + DRAW_THRESHOLD:
            wins += 1
        elif update.effective_score < 0.5 - DRAW_THRESHOLD:
            losses += 1
        else:
            draws += 1
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO elo_ratings (
                    entity_type, entity_id, conversation_model, judge_model,
                    rating, games_played, wins, losses, draws, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    update.entity_type,
                    update.entity_id,
                    update.conversation_model,
                    update.judge_model,
                    update.rating_after,
                    current.games_played + 1,
                    wins,
                    losses,
                    draws,
                    update.timestamp.isoformat(),
                ),
            )
            connection.execute(
                """
                INSERT INTO elo_history (
                    tournament_id, entity_type, entity_id, opponent_id, conversation_model, judge_model, simulation_id,
                    rating_before, rating_after, effective_score, expected_score, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    tournament_id,
                    update.entity_type,
                    update.entity_id,
                    update.opponent_id,
                    update.conversation_model,
                    update.judge_model,
                    update.simulation_id,
                    update.rating_before,
                    update.rating_after,
                    update.effective_score,
                    update.expected_score,
                    update.timestamp.isoformat(),
                ),
            )

    def get_elo_history(self, entity_id: str) -> list[EloUpdate]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM elo_history
                WHERE entity_id = ?
                ORDER BY timestamp, id
                """,
                (entity_id,),
            ).fetchall()
        return [_elo_update_from_row(row) for row in rows]

    def reset_elo_ratings(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM elo_ratings")
            connection.execute("DELETE FROM elo_history")

    def save_tournament(self, result: TournamentResult) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO tournaments (
                    id, config_json, rounds_completed, total_games, started_at, completed_at, total_cost_usd
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.id,
                    json.dumps(model_dump_jsonable(result.config)),
                    result.rounds_completed,
                    result.total_games,
                    result.started_at.isoformat(),
                    result.completed_at.isoformat() if result.completed_at else None,
                    result.total_cost_usd,
                ),
            )

    def get_tournament(self, tournament_id: str) -> TournamentResult:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM tournaments WHERE id = ?", (tournament_id,)).fetchone()
        if row is None:
            raise KeyError(f"unknown tournament '{tournament_id}'")
        return _tournament_from_row(row)

    def list_tournaments(self) -> list[TournamentResult]:
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM tournaments ORDER BY started_at DESC").fetchall()
        return [_tournament_from_row(row) for row in rows]


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    return getattr(value, "value", value)


def _run_row(result: SimulationResult) -> tuple[Any, ...]:
    judgment = result.judgment
    return (
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
    )


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


def _elo_update_from_row(row: sqlite3.Row) -> EloUpdate:
    return EloUpdate(
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        opponent_id=row["opponent_id"],
        conversation_model=row["conversation_model"],
        judge_model=row["judge_model"],
        simulation_id=row["simulation_id"],
        rating_before=float(row["rating_before"]),
        rating_after=float(row["rating_after"]),
        effective_score=float(row["effective_score"]),
        expected_score=float(row["expected_score"]),
        timestamp=datetime.fromisoformat(row["timestamp"]),
    )


def _tournament_from_row(row: sqlite3.Row) -> TournamentResult:
    return TournamentResult(
        id=row["id"],
        config=TournamentConfig.model_validate(json.loads(row["config_json"])),
        rounds_completed=int(row["rounds_completed"] or 0),
        total_games=int(row["total_games"] or 0),
        started_at=datetime.fromisoformat(row["started_at"]),
        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        total_cost_usd=float(row["total_cost_usd"] or 0.0),
    )
