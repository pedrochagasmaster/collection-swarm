"""Tests for the analysis pipeline: compliance, statistics, objections."""

from __future__ import annotations

from collection_swarm.analysis.compliance import check_exclusions
from collection_swarm.analysis.objections import ObjectionReport, extract_objections
from collection_swarm.analysis.statistics import StrategyRanking, compare_strategies
from collection_swarm.models import (
    EndedBy,
    Judgment,
    Message,
    PaymentOutcome,
    SimulationResult,
)
from collection_swarm.store import SimulationStore


def _make_result(
    run_id: str = "sim_analysis",
    profile_id: str = "cooperative_hardship",
    strategy_id: str = "empathetic_payment_plan",
    compliance_score: float = 0.95,
    escalation_risk: float = 0.05,
    payment_probability: float = 0.8,
    transcript: list[Message] | None = None,
) -> SimulationResult:
    return SimulationResult(
        id=run_id,
        profile_id=profile_id,
        strategy_id=strategy_id,
        conversation_model="local-scripted",
        judge_model="local-judge",
        turn_count=2,
        ended_by=EndedBy.COLLECTOR,
        transcript=transcript
        or [
            Message(role="collector", content="Can we set up a plan?"),
            Message(role="debtor", content="I can pay $100 per month."),
        ],
        judgment=Judgment(
            reasoning="Acceptable.",
            payment_outcome=PaymentOutcome.PAYMENT_PLAN,
            payment_probability=payment_probability,
            debtor_satisfaction=0.7,
            compliance_score=compliance_score,
            conversation_efficiency=2,
            rapport_built=0.6,
            escalation_risk=escalation_risk,
        ),
    )


# ── Compliance exclusions ────────────────────────────────────────


def test_no_exclusions_when_all_scores_passing(tmp_path) -> None:
    store = SimulationStore(tmp_path / "test.sqlite")
    for i in range(3):
        store.save_run(_make_result(run_id=f"sim_{i}", compliance_score=0.9, escalation_risk=0.1))

    exclusions = check_exclusions(
        store,
        profile_ids=["cooperative_hardship"],
        strategy_ids=["empathetic_payment_plan"],
    )

    assert exclusions == []


def test_exclusion_when_compliance_below_threshold(tmp_path) -> None:
    store = SimulationStore(tmp_path / "test.sqlite")
    for i in range(3):
        store.save_run(_make_result(run_id=f"sim_{i}", compliance_score=0.5, escalation_risk=0.1))

    exclusions = check_exclusions(
        store,
        profile_ids=["cooperative_hardship"],
        strategy_ids=["empathetic_payment_plan"],
        min_compliance_score=0.8,
    )

    assert len(exclusions) == 1
    assert "compliance_score" in exclusions[0].reason


def test_exclusion_when_escalation_risk_above_threshold(tmp_path) -> None:
    store = SimulationStore(tmp_path / "test.sqlite")
    for i in range(3):
        store.save_run(_make_result(run_id=f"sim_{i}", compliance_score=0.9, escalation_risk=0.5))

    exclusions = check_exclusions(
        store,
        profile_ids=["cooperative_hardship"],
        strategy_ids=["empathetic_payment_plan"],
        max_escalation_risk=0.3,
    )

    assert len(exclusions) == 1
    assert "escalation_risk" in exclusions[0].reason


def test_exclusion_both_reasons(tmp_path) -> None:
    store = SimulationStore(tmp_path / "test.sqlite")
    for i in range(3):
        store.save_run(_make_result(run_id=f"sim_{i}", compliance_score=0.5, escalation_risk=0.5))

    exclusions = check_exclusions(
        store,
        profile_ids=["cooperative_hardship"],
        strategy_ids=["empathetic_payment_plan"],
        min_compliance_score=0.8,
        max_escalation_risk=0.3,
    )

    assert len(exclusions) == 1
    assert "compliance_score" in exclusions[0].reason
    assert "escalation_risk" in exclusions[0].reason


def test_no_exclusion_with_no_data(tmp_path) -> None:
    store = SimulationStore(tmp_path / "test.sqlite")

    exclusions = check_exclusions(
        store,
        profile_ids=["cooperative_hardship"],
        strategy_ids=["empathetic_payment_plan"],
    )

    assert exclusions == []


# ── Strategy ranking / statistics ────────────────────────────────


def test_compare_strategies_ranks_by_payment_probability(tmp_path) -> None:
    store = SimulationStore(tmp_path / "test.sqlite")
    store.save_run(_make_result(run_id="sim_1", strategy_id="low_performer", payment_probability=0.3))
    store.save_run(_make_result(run_id="sim_2", strategy_id="high_performer", payment_probability=0.9))

    ranking = compare_strategies("cooperative_hardship", store)

    assert isinstance(ranking, StrategyRanking)
    assert ranking.recommended_strategy_id == "high_performer"
    assert len(ranking.strategies) == 2
    assert ranking.strategies[0].mean_payment_probability > ranking.strategies[1].mean_payment_probability


def test_compare_strategies_empty_store(tmp_path) -> None:
    store = SimulationStore(tmp_path / "test.sqlite")

    ranking = compare_strategies("cooperative_hardship", store)

    assert ranking.strategies == []
    assert ranking.recommended_strategy_id is None


# ── Objection extraction ────────────────────────────────────────


def test_extract_objections_detects_inability_to_pay() -> None:
    transcripts = [
        [
            Message(role="collector", content="Can we discuss payment?"),
            Message(role="debtor", content="I can't afford to pay right now, I'm in a tough spot."),
        ]
    ]

    report = extract_objections(transcripts)

    assert isinstance(report, ObjectionReport)
    assert "inability_to_pay" in report.objections
    assert report.objections["inability_to_pay"] >= 1


def test_extract_objections_detects_dispute() -> None:
    transcripts = [
        [
            Message(role="collector", content="We show a balance of $500."),
            Message(role="debtor", content="That's not mine, I dispute this debt."),
        ]
    ]

    report = extract_objections(transcripts)

    assert "disputes_debt" in report.objections


def test_extract_objections_detects_avoidance() -> None:
    transcripts = [
        [
            Message(role="collector", content="Can we discuss?"),
            Message(role="debtor", content="Not now, call back later."),
        ]
    ]

    report = extract_objections(transcripts)

    assert "avoidance" in report.objections


def test_extract_objections_no_matches() -> None:
    transcripts = [
        [
            Message(role="collector", content="Hello."),
            Message(role="debtor", content="I agree to pay everything."),
        ]
    ]

    report = extract_objections(transcripts)

    assert report.objections == {}


def test_extract_objections_multiple_transcripts() -> None:
    transcripts = [
        [
            Message(role="collector", content="Can we discuss payment?"),
            Message(role="debtor", content="I can't afford to pay, hardship situation."),
        ],
        [
            Message(role="collector", content="About your account..."),
            Message(role="debtor", content="This is causing me stress, I'm tired of calls."),
        ],
    ]

    report = extract_objections(transcripts)

    assert "inability_to_pay" in report.objections
    assert "emotional_distress" in report.objections


def test_extract_objections_respects_taxonomy_filter() -> None:
    transcripts = [
        [
            Message(role="collector", content="Can we discuss?"),
            Message(role="debtor", content="I can't afford this and it's not mine — I dispute it."),
        ]
    ]

    report = extract_objections(transcripts, taxonomy=["inability_to_pay"])

    assert "inability_to_pay" in report.objections
    assert "disputes_debt" not in report.objections


def test_extract_objections_ignores_collector_text() -> None:
    transcripts = [
        [
            Message(role="collector", content="I know this is a hardship, but can't afford to lose you."),
            Message(role="debtor", content="Fine, let me think about it."),
        ]
    ]

    report = extract_objections(transcripts)

    assert report.objections == {}
