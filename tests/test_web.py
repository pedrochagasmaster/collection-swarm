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
        assert len(data["profiles"]) == 3
        assert len(data["strategies"]) == 4
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
        assert len(data) == 3

    def test_list_strategies(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/api/config/strategies")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 4

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
                "conversation_models": ["local-scripted", "local-scripted"],
                "judge_models": ["local-judge", "local-judge"],
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


class TestModelBenchmarks:
    def test_benchmark_options_include_models_and_roles(self, empty_client: TestClient) -> None:
        resp = empty_client.get("/api/model-benchmarks/options")

        assert resp.status_code == 200
        data = resp.json()
        assert "gpt-5.5" in data["cursor_models"]
        assert data["roles"] == ["collector", "debtor", "judge"]
        assert data["defaults"]["profile_id"] == "cooperative_hardship"

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
                "profile_id": "cooperative_hardship",
                "strategy_id": "empathetic_payment_plan",
                "judge_profile_id": "written_proof_disputer",
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
