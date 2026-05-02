from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from collection_swarm.calibration import (
    CalibrationLabel,
    evaluate_judge,
    load_calibration_labels,
    pearson_correlation,
)
from collection_swarm.models import EndedBy, Judgment, PaymentOutcome, SimulationResult
from collection_swarm.store import SimulationStore


def _run(run_id: str, payment: float, compliance: float) -> SimulationResult:
    return SimulationResult(
        id=run_id,
        profile_id="cooperative_hardship",
        strategy_id="empathetic_payment_plan",
        conversation_model="local-scripted",
        judge_model="local-judge",
        ended_by=EndedBy.COLLECTOR,
        judgment=Judgment(
            reasoning="stored",
            payment_outcome=PaymentOutcome.PAYMENT_PLAN,
            payment_probability=payment,
            debtor_satisfaction=0.5,
            compliance_score=compliance,
            conversation_efficiency=2,
            rapport_built=0.5,
            escalation_risk=0.1,
        ),
    )


def test_load_calibration_labels_validates_json(tmp_path) -> None:
    path = tmp_path / "labels.json"
    path.write_text(
        json.dumps(
            [
                {
                    "transcript_id": "sim_1",
                    "human_scores": {"payment_probability": 0.7, "compliance_score": 0.9},
                    "labeler_id": "analyst",
                }
            ]
        ),
        encoding="utf-8",
    )

    labels = load_calibration_labels(path)

    assert labels[0].transcript_id == "sim_1"
    assert labels[0].human_scores["payment_probability"] == 0.7


def test_calibration_label_rejects_out_of_range_score() -> None:
    with pytest.raises(ValidationError):
        CalibrationLabel(
            transcript_id="sim_1",
            human_scores={"payment_probability": 1.2},
            labeler_id="analyst",
        )


def test_pearson_correlation_handles_perfect_relationship() -> None:
    assert pearson_correlation([0.1, 0.5, 0.9], [0.2, 0.6, 1.0]) == pytest.approx(1.0)


def test_evaluate_judge_computes_correlation_and_mae(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")
    store.save_runs([_run("sim_1", 0.2, 0.9), _run("sim_2", 0.8, 0.7)])
    labels = [
        CalibrationLabel(
            transcript_id="sim_1",
            human_scores={"payment_probability": 0.3, "compliance_score": 0.8},
            labeler_id="analyst",
        ),
        CalibrationLabel(
            transcript_id="sim_2",
            human_scores={"payment_probability": 0.9, "compliance_score": 0.6},
            labeler_id="analyst",
        ),
    ]

    result = evaluate_judge(labels, store)

    assert result.correlations["payment_probability"] == pytest.approx(1.0)
    assert result.mae["payment_probability"] == pytest.approx(0.1)
    assert result.label_count == 2


def test_store_saves_calibration_labels_and_variants(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")
    label = CalibrationLabel(
        transcript_id="sim_1",
        human_scores={"payment_probability": 0.7},
        labeler_id="analyst",
    )

    store.save_calibration_labels([label])
    variant_id = store.save_judge_variant(
        system_prompt="system",
        transcript_prompt="transcript",
        calibration_score=0.8,
    )

    assert store.list_calibration_labels()[0].transcript_id == "sim_1"
    assert store.list_judge_variants()[0]["id"] == variant_id
