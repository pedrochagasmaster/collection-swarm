from __future__ import annotations

from collection_swarm.models import EndedBy, EloUpdate, Judgment, Message, PaymentOutcome, SimulationResult, TournamentConfig, TournamentResult
from collection_swarm.store import SimulationStore


def _result() -> SimulationResult:
    return SimulationResult(
        id="sim_test",
        profile_id="cooperative_hardship",
        strategy_id="empathetic_payment_plan",
        conversation_model="local-scripted",
        judge_model="local-scripted",
        turn_count=2,
        ended_by=EndedBy.DEBTOR,
        transcript=[
            Message(role="collector", content="Can we set up a plan?"),
            Message(role="debtor", content="I can pay $100 per month."),
        ],
        judgment=Judgment(
            reasoning="Good plan.",
            payment_outcome=PaymentOutcome.PAYMENT_PLAN,
            payment_probability=0.8,
            debtor_satisfaction=0.7,
            compliance_score=0.95,
            conversation_efficiency=2,
            rapport_built=0.6,
            escalation_risk=0.05,
        ),
    )


def test_store_saves_and_reads_simulation(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")
    store.save_run(_result())

    loaded = store.get_run("sim_test")

    assert loaded.profile_id == "cooperative_hardship"
    assert loaded.judgment is not None
    assert loaded.judgment.payment_probability == 0.8
    assert store.count_by_status() == {"completed": 1}


def test_store_saves_runs_in_batch(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")
    first = _result()
    second = _result().model_copy(update={"id": "sim_test_2", "strategy_id": "neutral_reminder"})

    store.save_runs([first, second])

    assert store.count_by_status() == {"completed": 2}
    assert store.get_run("sim_test_2").strategy_id == "neutral_reminder"


def test_strategy_comparison_and_best_transcript(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")
    store.save_run(_result())

    stats = store.get_strategy_comparison("cooperative_hardship")

    assert stats[0].strategy_id == "empathetic_payment_plan"
    assert store.get_best_transcript("cooperative_hardship", "empathetic_payment_plan")[1].role == "debtor"


def test_elo_rating_defaults_to_1500(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")

    rating = store.get_elo_rating("strategy", "new_strategy")

    assert rating.rating == 1500.0
    assert rating.games_played == 0


def test_save_and_read_elo_update(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")
    update = EloUpdate(
        entity_type="strategy",
        entity_id="empathetic_payment_plan",
        opponent_id="cooperative_hardship",
        simulation_id="sim_test",
        rating_before=1500,
        rating_after=1510,
        effective_score=0.8,
        expected_score=0.5,
    )

    store.save_elo_update(update, tournament_id="tourn_test")
    rating = store.get_elo_rating("strategy", "empathetic_payment_plan")
    history = store.get_elo_history("empathetic_payment_plan")

    assert rating.rating == 1510
    assert rating.games_played == 1
    assert rating.wins == 1
    assert len(history) == 1
    assert history[0].simulation_id == "sim_test"


def test_elo_ratings_are_scoped_by_model_pair(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")
    base = {
        "entity_type": "strategy",
        "entity_id": "empathetic_payment_plan",
        "opponent_id": "cooperative_hardship",
        "simulation_id": "sim_test",
        "rating_before": 1500,
        "rating_after": 1510,
        "effective_score": 0.8,
        "expected_score": 0.5,
    }

    store.save_elo_update(EloUpdate(**base, conversation_model="model_a", judge_model="judge_a"))
    store.save_elo_update(EloUpdate(**base, conversation_model="model_b", judge_model="judge_a"))

    assert store.get_elo_rating("strategy", "empathetic_payment_plan", "model_a", "judge_a").games_played == 1
    assert store.get_elo_rating("strategy", "empathetic_payment_plan", "model_b", "judge_a").games_played == 1
    assert store.get_elo_rating("strategy", "empathetic_payment_plan", "model_c", "judge_a").games_played == 0


def test_elo_history_returns_chronological_updates(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")
    for idx in range(2):
        store.save_elo_update(
            EloUpdate(
                entity_type="profile",
                entity_id="cooperative_hardship",
                opponent_id=f"strategy_{idx}",
                simulation_id=f"sim_{idx}",
                rating_before=1500 + idx,
                rating_after=1501 + idx,
                effective_score=0.4,
                expected_score=0.5,
            ),
            tournament_id="tourn_test",
        )

    assert [update.simulation_id for update in store.get_elo_history("cooperative_hardship")] == ["sim_0", "sim_1"]


def test_reset_elo_ratings_clears_all(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")
    store.save_elo_update(
        EloUpdate(
            entity_type="strategy",
            entity_id="empathetic_payment_plan",
            opponent_id="cooperative_hardship",
            simulation_id="sim_test",
            rating_before=1500,
            rating_after=1510,
            effective_score=0.8,
            expected_score=0.5,
        )
    )

    store.reset_elo_ratings()

    assert store.get_elo_ratings() == []
    assert store.get_elo_history("empathetic_payment_plan") == []


def test_save_and_read_tournament(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")
    result = TournamentResult(
        id="tourn_test",
        config=TournamentConfig(format="round_robin", rounds=1),
        rounds_completed=1,
        total_games=2,
        total_cost_usd=0.12,
    )

    store.save_tournament(result)

    assert store.get_tournament("tourn_test").total_games == 2
    assert store.list_tournaments()[0].id == "tourn_test"
