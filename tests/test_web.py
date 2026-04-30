"""Tests for the web dashboard module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from collection_swarm.web.app import create_app
from collection_swarm.web.seed import generate_seed_data


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
        assert isinstance(data, list)


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
