"""Judge calibration utilities."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from collection_swarm.store import SimulationStore


class CalibrationLabel(BaseModel):
    transcript_id: str
    human_scores: dict[str, float]
    labeler_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("human_scores")
    @classmethod
    def validate_scores(cls, value: dict[str, float]) -> dict[str, float]:
        for metric, score in value.items():
            if score < 0 or score > 1:
                raise ValueError(f"{metric} must be between 0 and 1")
        return value


class CalibrationResult(BaseModel):
    correlations: dict[str, float]
    mae: dict[str, float]
    overall_score: float
    label_count: int


def load_calibration_labels(path: Path | str) -> list[CalibrationLabel]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    return [CalibrationLabel.model_validate(item) for item in data]


def pearson_correlation(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or not xs:
        return 0.0
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denom_x == 0 or denom_y == 0:
        return 0.0
    return numerator / (denom_x * denom_y)


def evaluate_judge(labels: list[CalibrationLabel], store: SimulationStore) -> CalibrationResult:
    by_metric: dict[str, tuple[list[float], list[float]]] = {}
    used_labels = 0
    for label in labels:
        try:
            run = store.get_run(label.transcript_id)
        except KeyError:
            continue
        if run.judgment is None:
            continue
        used_labels += 1
        judgment_data = run.judgment.model_dump()
        for metric, human_score in label.human_scores.items():
            if metric not in judgment_data or not isinstance(judgment_data[metric], (int, float)):
                continue
            human, judge = by_metric.setdefault(metric, ([], []))
            human.append(float(human_score))
            judge.append(float(judgment_data[metric]))

    correlations: dict[str, float] = {}
    mae: dict[str, float] = {}
    for metric, (human, judge) in by_metric.items():
        correlations[metric] = pearson_correlation(human, judge)
        mae[metric] = sum(abs(h - j) for h, j in zip(human, judge, strict=True)) / len(human)
    overall = sum(correlations.values()) / len(correlations) if correlations else 0.0
    return CalibrationResult(correlations=correlations, mae=mae, overall_score=overall, label_count=used_labels)
