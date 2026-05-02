"""Tests for the web dashboard module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from collection_swarm.model_evaluation import RoleProbe
from collection_swarm.web.app import create_app
from collection_swarm.web.seed import generate_seed_data


def _wait_for_job(client: TestClient, job_id: str) -> dict:
    for _ in range(20):
        data = client.get(f"/api/jobs/{job_id}").json()
        if data["status"] in {"completed", "failed"}:
            return data
    raise AssertionError(f"job {job_id} did not finish")


@pytest.fixture()
def seeded_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "test.sqlite"
    generate_seed_data(db_path=db_path, num_runs=12)
    app = create_app(config_dir=Path("config"), db_path=db_path)
    return TestClient(app)


@pytest.fixture()
def empty_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "empty.sqlite"
    app = create_app(config_dir=Path("config"), db_path=db_path)
    return TestClient(app)


class TestDashboard:
    def test_dashboard_returns_summary(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_runs"] == 12
        assert data["completed"] == 12
        assert data["failed"] == 0
        # Seed data covers representative Will Bank scenarios while respecting
        # the requested run count.
        assert {"cooperative_hardship", "liquidation_confused", "willbank_blocked_balance_hardship"}.issubset(
            set(data["profiles"])
        )
        assert {
            "empathetic_payment_plan",
            "liquidation_explainer",
            "blocked_balance_hardship_plan",
            "micro_merchant_cashflow_alignment",
        }.issubset(set(data["strategies"]))
        assert "outcome_distribution" in data
        assert "average_scores" in data

    def test_dashboard_empty_db(self, empty_client: TestClient) -> None:
        resp = empty_client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_runs"] == 0


class TestRuns:
    def test_list_all_runs(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/api/runs?status=")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 12

    def test_filter_by_profile(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/api/runs?status=completed&profile_id=cooperative_hardship")
        assert resp.status_code == 200
        data = resp.json()
        assert all(r["profile_id"] == "cooperative_hardship" for r in data)
        assert len(data) > 0

    def test_get_single_run(self, seeded_client: TestClient) -> None:
        runs = seeded_client.get("/api/runs?status=").json()
        run_id = runs[0]["id"]
        resp = seeded_client.get(f"/api/runs/{run_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == run_id
        assert "transcript" in data
        assert len(data["transcript"]) > 0

    def test_get_missing_run_404(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/api/runs/nonexistent")
        assert resp.status_code == 404


class TestTranscript:
    def test_transcript_has_roles_and_content(self, seeded_client: TestClient) -> None:
        runs = seeded_client.get("/api/runs?status=").json()
        run_id = runs[0]["id"]
        data = seeded_client.get(f"/api/runs/{run_id}").json()
        for msg in data["transcript"]:
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ("collector", "debtor", "system", "judge")


class TestStrategies:
    def test_strategy_comparison(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/api/profiles/cooperative_hardship/strategies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["profile_id"] == "cooperative_hardship"
        assert len(data["strategies"]) > 0
        assert data["recommended"] is not None


class TestCompliance:
    def test_exclusions_endpoint(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/api/compliance/exclusions")
        assert resp.status_code == 200
        data = resp.json()
        assert "thresholds" in data
        assert "exclusions" in data
        assert "total_completed_runs" in data
        assert isinstance(data["exclusions"], list)
        if data["exclusions"]:
            exclusion = data["exclusions"][0]
            assert "simulation_count" in exclusion
            assert "run_ids" in exclusion
            assert "model_pairs" in exclusion
            assert all("conversation_model" in item for item in exclusion["model_pairs"])


class TestPlaybook:
    def test_playbook_html(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/api/playbook?format=html")
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "html"
        assert "<h1>" in data["content"]

    def test_playbook_markdown(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/api/playbook?format=markdown")
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "markdown"
        assert "# Collection Playbook" in data["content"]


class TestConfig:
    def test_list_profiles(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/api/config/profiles")
        assert resp.status_code == 200
        data = resp.json()
        # Catalog grew with Will Bank persona research; ensure original and
        # complementary liquidation profiles are exposed.
        ids = {profile["id"] for profile in data}
        assert {"cooperative_hardship", "written_proof_disputer", "hostile_avoidant"}.issubset(ids)
        assert {"liquidation_confused", "willbank_low_digital_access"} <= ids
        assert len(data) >= 14

    def test_list_strategies(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/api/config/strategies")
        assert resp.status_code == 200
        data = resp.json()
        ids = {strategy["id"] for strategy in data}
        assert {
            "empathetic_payment_plan",
            "liquidation_explainer",
            "blocked_balance_hardship_plan",
            "low_digital_access_guidance",
        }.issubset(ids)
        assert len(data) >= 13

    def test_list_models(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/api/config/models")
        assert resp.status_code == 200
        data = resp.json()
        assert data["default_conversation_model"] == "local-scripted"
        assert data["default_judge_model"] == "local-judge"
        assert any(model["id"] == "local-scripted" for model in data["models"])


class TestRunJobs:
    def test_launch_single_simulation_job(self, empty_client: TestClient) -> None:
        resp = empty_client.post(
            "/api/jobs/simulations",
            json={
                "profile_id": "cooperative_hardship",
                "strategy_id": "empathetic_payment_plan",
                "conversation_model": "local-scripted",
                "judge_model": "local-judge",
            },
        )
        assert resp.status_code == 200
        job_id = resp.json()["id"]
        job = _wait_for_job(empty_client, job_id)
        assert job["status"] == "completed"
        assert job["completed"] == 1
        run_id = job["result_ids"][0]
        run = empty_client.get(f"/api/runs/{run_id}").json()
        assert run["status"] == "completed"
        assert len(run["transcript"]) > 0

    def test_launch_matrix_job_tracks_progress(self, empty_client: TestClient) -> None:
        resp = empty_client.post(
            "/api/jobs/matrix",
            json={
                "profile_ids": ["cooperative_hardship"],
                "strategy_ids": ["empathetic_payment_plan", "neutral_reminder"],
                "conversation_models": ["local-scripted"],
                "judge_models": ["local-judge"],
                "reps": 1,
                "concurrency": 2,
            },
        )
        assert resp.status_code == 200
        job_id = resp.json()["id"]
        job = _wait_for_job(empty_client, job_id)
        assert job["status"] == "completed"
        assert job["total"] == 2
        assert job["completed"] == 2
        assert len(job["result_ids"]) == 2

    def test_launch_matrix_job_multiplies_model_dimensions(self, empty_client: TestClient) -> None:
        resp = empty_client.post(
            "/api/jobs/matrix",
            json={
                "profile_ids": ["cooperative_hardship"],
                "strategy_ids": ["empathetic_payment_plan"],
                "conversation_models": ["local-scripted", "cursor-composer-2"],
                "judge_models": ["local-judge", "cursor-claude-opus-4-7-thinking-high"],
                "reps": 1,
                "concurrency": 2,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 4

    def test_matrix_requires_explicit_profile_and_strategy_selection(self, empty_client: TestClient) -> None:
        resp = empty_client.post(
            "/api/jobs/matrix",
            json={
                "profile_ids": [],
                "strategy_ids": ["empathetic_payment_plan"],
                "conversation_models": ["local-scripted"],
                "judge_models": ["local-judge"],
            },
        )
        assert resp.status_code == 400
        assert "profile" in resp.json()["detail"]

        resp = empty_client.post(
            "/api/jobs/matrix",
            json={
                "profile_ids": ["cooperative_hardship"],
                "strategy_ids": [],
                "conversation_models": ["local-scripted"],
                "judge_models": ["local-judge"],
            },
        )
        assert resp.status_code == 400
        assert "strategy" in resp.json()["detail"]


class TestArena:
    def test_leaderboard_empty(self, empty_client: TestClient) -> None:
        resp = empty_client.get("/api/arena/leaderboard")

        assert resp.status_code == 200
        assert resp.json() == {"strategies": [], "profiles": []}

    def test_launch_tournament_job(self, empty_client: TestClient) -> None:
        resp = empty_client.post(
            "/api/jobs/tournaments",
            json={
                "format": "swiss",
                "rounds": 1,
                "profile_ids": ["cooperative_hardship", "hostile_avoidant"],
                "strategy_ids": ["empathetic_payment_plan", "neutral_reminder"],
                "conversation_model": "local-scripted",
                "judge_model": "local-judge",
                "concurrency": 2,
            },
        )

        assert resp.status_code == 200
        job = _wait_for_job(empty_client, resp.json()["id"])
        assert job["status"] == "completed"
        assert job["kind"] == "tournament"
        assert job["total"] == 2
        assert job["completed"] == 2

    def test_leaderboard_after_tournament_and_history(self, empty_client: TestClient) -> None:
        resp = empty_client.post(
            "/api/jobs/tournaments",
            json={
                "format": "round_robin",
                "rounds": 1,
                "profile_ids": ["cooperative_hardship"],
                "strategy_ids": ["empathetic_payment_plan"],
                "conversation_model": "local-scripted",
                "judge_model": "local-judge",
            },
        )
        job = _wait_for_job(empty_client, resp.json()["id"])
        assert job["status"] == "completed"

        leaderboard = empty_client.get("/api/arena/leaderboard").json()
        history = empty_client.get("/api/arena/history/empathetic_payment_plan").json()

        assert leaderboard["strategies"][0]["entity_id"] == "empathetic_payment_plan"
        assert leaderboard["profiles"][0]["entity_id"] == "cooperative_hardship"
        assert history[0]["entity_id"] == "empathetic_payment_plan"

    def test_list_tournaments(self, empty_client: TestClient) -> None:
        resp = empty_client.post(
            "/api/jobs/tournaments",
            json={
                "format": "swiss",
                "rounds": 1,
                "profile_ids": ["cooperative_hardship"],
                "strategy_ids": ["empathetic_payment_plan"],
                "conversation_model": "local-scripted",
                "judge_model": "local-judge",
            },
        )
        job = _wait_for_job(empty_client, resp.json()["id"])

        tournaments = empty_client.get("/api/arena/tournaments").json()
        tournament = empty_client.get(f"/api/arena/tournaments/{tournaments[0]['id']}").json()

        assert job["status"] == "completed"
        assert len(tournaments) == 1
        assert tournament["total_games"] == 1


class TestEvolutionAndCalibration:
    def test_evolution_pool_empty(self, empty_client: TestClient) -> None:
        resp = empty_client.get("/api/evolution/pool")

        assert resp.status_code == 200
        assert resp.json()["strategies"] == []

    def test_calibration_results_empty(self, empty_client: TestClient) -> None:
        resp = empty_client.get("/api/calibration/results")

        assert resp.status_code == 200
        assert resp.json()["label_count"] == 0

    def test_upload_calibration_labels(self, empty_client: TestClient) -> None:
        resp = empty_client.post(
            "/api/calibration/labels",
            json=[
                {
                    "transcript_id": "sim_missing",
                    "human_scores": {"payment_probability": 0.7},
                    "labeler_id": "analyst",
                }
            ],
        )

        assert resp.status_code == 200
        assert resp.json()["saved"] == 1

    def test_arena_leaderboard_can_filter_model_pair(self, empty_client: TestClient) -> None:
        from collection_swarm.models import EloUpdate
        from collection_swarm.store import SimulationStore

        store = SimulationStore(empty_client.app.state.db_path)
        store.save_elo_update(
            EloUpdate(
                entity_type="strategy",
                entity_id="model_specific",
                opponent_id="profile",
                conversation_model="cursor-composer-2",
                judge_model="local-judge",
                simulation_id="sim_model",
                rating_before=1500,
                rating_after=1510,
                effective_score=0.8,
                expected_score=0.5,
            )
        )

        default_data = empty_client.get("/api/arena/leaderboard").json()
        filtered = empty_client.get(
            "/api/arena/leaderboard?conversation_model=cursor-composer-2&judge_model=local-judge"
        ).json()

        assert "model_specific" not in {item["entity_id"] for item in default_data["strategies"]}
        assert "model_specific" in {item["entity_id"] for item in filtered["strategies"]}

    def test_run_options_include_evolved_entities(self, empty_client: TestClient) -> None:
        from collection_swarm.models import ProfileLineage, Strategy, StrategyLineage
        from collection_swarm.store import SimulationStore

        store = SimulationStore(empty_client.app.state.db_path)
        store.save_evolved_strategy(
            Strategy(
                id="evo_ui",
                tone="neutral",
                opening_approach="reminder",
                negotiation_tactic="payment_reminder",
                escalation_style="none",
                concession_willingness="low",
                compliance_adherence="strict",
                follow_up_strategy="written_agreement",
            ),
            StrategyLineage(strategy_id="evo_ui", generation=1),
        )
        profile = store.get_run if False else None
        config_profile = empty_client.get("/api/config/profiles").json()[0]
        from collection_swarm.models import Profile
        store.save_evolved_profile(
            Profile.model_validate({**config_profile, "id": "hard_ui"}),
            ProfileLineage(profile_id="hard_ui", parent_id=config_profile["id"], generation=1),
        )

        data = empty_client.get("/api/config/run-options").json()

        assert "evo_ui" in {item["id"] for item in data["strategies"]}
        assert "hard_ui" in {item["id"] for item in data["profiles"]}

    def test_calibration_job_stores_variant(self, empty_client: TestClient) -> None:
        resp = empty_client.post("/api/jobs/calibration", json={"labels": []})

        assert resp.status_code == 200
        job = _wait_for_job(empty_client, resp.json()["id"])
        assert job["status"] == "completed"
        assert empty_client.get("/api/calibration/variants").json()


class TestModelBenchmarks:
    def test_benchmark_options_include_models_and_roles(self, empty_client: TestClient) -> None:
        resp = empty_client.get("/api/model-benchmarks/options")

        assert resp.status_code == 200
        data = resp.json()
        assert "gpt-5.5" in data["cursor_models"]
        assert data["roles"] == ["collector", "debtor", "judge"]
        assert data["defaults"]["profile_ids"] == ["cooperative_hardship"]
        assert data["defaults"]["strategy_ids"] == ["empathetic_payment_plan"]
        assert data["defaults"]["judge_profile_ids"] == ["written_proof_disputer"]

    def test_launch_model_benchmark_job_saves_report(
        self,
        empty_client: TestClient,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async def fake_run_live_role_probes(*args, **kwargs):
            return (
                RoleProbe("gpt-5.5", "collector", "ok", 0.01, "This is an attempt to collect a debt for a $1,250 medical balance."),
                RoleProbe("gpt-5.5", "debtor", "ok", 0.01, "My hours were cut and I can realistically pay $100 a month."),
            )

        monkeypatch.setattr("collection_swarm.web.app.run_live_role_probes", fake_run_live_role_probes)

        resp = empty_client.post(
            "/api/jobs/model-benchmarks",
            json={
                "cursor_model_names": ["gpt-5.5"],
                "roles": ["collector", "debtor"],
                "profile_ids": ["cooperative_hardship"],
                "strategy_ids": ["empathetic_payment_plan"],
                "judge_profile_ids": ["written_proof_disputer"],
                "concurrency": 1,
            },
        )

        assert resp.status_code == 200
        job_id = resp.json()["id"]
        job = _wait_for_job(empty_client, job_id)
        assert job["status"] == "completed"
        assert job["benchmark_report"]["recommendations"]["collector"] == "gpt-5.5"
        assert job["artifacts"]["json"].endswith(".json")

        report = empty_client.get(f"/api/model-benchmarks/{job_id}")
        assert report.status_code == 200
        assert report.json()["title"] == "Production Cursor Model Role Benchmark"


class TestManualSessions:
    def test_manual_debtor_session_completes_and_saves(self, empty_client: TestClient) -> None:
        resp = empty_client.post(
            "/api/manual-sessions",
            json={
                "profile_id": "cooperative_hardship",
                "strategy_id": "empathetic_payment_plan",
                "human_role": "debtor",
                "conversation_model": "local-scripted",
                "judge_model": "local-judge",
            },
        )
        assert resp.status_code == 200
        session = resp.json()
        assert session["status"] == "waiting_for_human"
        assert session["run"]["transcript"][0]["role"] == "collector"

        resp = empty_client.post(
            f"/api/manual-sessions/{session['id']}/turn",
            json={"content": "I can do $100 per month. [END_CONVERSATION]"},
        )
        assert resp.status_code == 200
        session = resp.json()
        assert session["status"] == "completed"
        run = session["run"]
        assert run["status"] == "completed"
        assert run["judgment"] is not None
        saved = empty_client.get(f"/api/runs/{run['id']}").json()
        assert saved["id"] == run["id"]

    def test_manual_finish_rejects_empty_session(self, empty_client: TestClient) -> None:
        resp = empty_client.post(
            "/api/manual-sessions",
            json={
                "profile_id": "cooperative_hardship",
                "strategy_id": "empathetic_payment_plan",
                "human_role": "collector",
                "conversation_model": "local-scripted",
                "judge_model": "local-judge",
            },
        )
        assert resp.status_code == 200
        session = resp.json()
        assert session["run"]["transcript"] == []

        resp = empty_client.post(f"/api/manual-sessions/{session['id']}/finish", json={})
        assert resp.status_code == 400
        assert "no turns" in resp.json()["detail"]

    def test_manual_turn_rejects_non_waiting_state(self, empty_client: TestClient) -> None:
        resp = empty_client.post(
            "/api/manual-sessions",
            json={
                "profile_id": "cooperative_hardship",
                "strategy_id": "empathetic_payment_plan",
                "human_role": "debtor",
                "conversation_model": "local-scripted",
                "judge_model": "local-judge",
            },
        )
        session_id = resp.json()["id"]
        empty_client.app.state.manual_sessions[session_id].status = "ai_thinking"

        resp = empty_client.post(
            f"/api/manual-sessions/{session_id}/turn",
            json={"content": "Duplicate turn"},
        )
        assert resp.status_code == 409
        assert "ai_thinking" in resp.json()["detail"]


class TestSPA:
    def test_index_returns_html(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/")
        assert resp.status_code == 200
        assert "Collection Swarm" in resp.text

    def test_static_css(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/static/styles.css")
        assert resp.status_code == 200

    def test_static_js(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/static/app.js")
        assert resp.status_code == 200


class TestSeedData:
    def test_seed_creates_expected_count(self, tmp_path: Path) -> None:
        db_path = tmp_path / "seed_test.sqlite"
        n = generate_seed_data(db_path=db_path, num_runs=12)
        assert n == 12

    def test_seed_data_has_judgments(self, tmp_path: Path) -> None:
        from collection_swarm.store import SimulationStore
        db_path = tmp_path / "seed_test.sqlite"
        generate_seed_data(db_path=db_path, num_runs=12)
        store = SimulationStore(db_path)
        runs = store.list_runs(status="completed")
        assert all(r.judgment is not None for r in runs)
