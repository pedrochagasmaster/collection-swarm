"""End-to-end tests for the dashboard credential API and CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner
from fastapi.testclient import TestClient

from collection_swarm.cli import cli
from collection_swarm.credentials import CredentialStore
from collection_swarm.web.app import create_app


@pytest.fixture()
def web_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "creds.sqlite"
    return TestClient(create_app(config_dir=Path("config"), db_path=db_path))


def test_list_credentials_returns_provider_metadata(web_client: TestClient, monkeypatch) -> None:
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)

    response = web_client.get("/api/credentials")

    assert response.status_code == 200
    data = response.json()
    ids = {p["id"] for p in data["providers"]}
    assert ids == {"cursor", "nvidia_nim"}
    cursor = next(p for p in data["providers"] if p["id"] == "cursor")
    assert cursor["env_var"] == "CURSOR_API_KEY"
    assert cursor["configured"] is False
    assert cursor["preview"] is None
    assert "storage_path" in data


def test_upsert_credential_persists_value(web_client: TestClient, tmp_path: Path) -> None:
    response = web_client.put("/api/credentials/cursor", json={"value": "key_topsecret_1234"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is True
    assert payload["source"] == "store"
    assert payload["preview"] == "key_...1234"

    # Status endpoint reflects the change.
    refreshed = web_client.get("/api/credentials").json()
    cursor = next(p for p in refreshed["providers"] if p["id"] == "cursor")
    assert cursor["configured"] is True


def test_delete_credential_removes_value(web_client: TestClient) -> None:
    web_client.put("/api/credentials/cursor", json={"value": "abc12345"})

    deleted = web_client.delete("/api/credentials/cursor")

    assert deleted.status_code == 200
    assert deleted.json()["source"] is None


def test_upsert_unknown_provider_returns_404(web_client: TestClient) -> None:
    response = web_client.put("/api/credentials/unknown", json={"value": "x"})
    assert response.status_code == 404


def test_upsert_rejects_empty_value(web_client: TestClient) -> None:
    response = web_client.put("/api/credentials/cursor", json={"value": "   "})
    assert response.status_code == 422


def test_cli_creds_list_reports_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    db = tmp_path / "creds.sqlite"

    result = CliRunner().invoke(cli, ["--db", str(db), "creds", "list"])

    assert result.exit_code == 0
    assert "Cursor SDK" in result.output
    assert "NVIDIA NIM" in result.output
    assert "missing" in result.output


def test_cli_creds_set_then_list(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    db = tmp_path / "creds.sqlite"
    runner = CliRunner()

    set_result = runner.invoke(
        cli,
        ["--db", str(db), "creds", "set", "cursor", "--value", "my_secret_key"],
    )
    list_result = runner.invoke(cli, ["--db", str(db), "creds", "list"])

    assert set_result.exit_code == 0, set_result.output
    assert "Saved Cursor SDK credential" in set_result.output
    assert list_result.exit_code == 0
    assert "dashboard" in list_result.output
    assert CredentialStore(db).get("cursor").value == "my_secret_key"  # type: ignore[union-attr]


def test_cli_creds_clear_removes_credential(tmp_path: Path) -> None:
    db = tmp_path / "creds.sqlite"
    runner = CliRunner()
    runner.invoke(cli, ["--db", str(db), "creds", "set", "cursor", "--value", "hello"])

    result = runner.invoke(cli, ["--db", str(db), "creds", "clear", "cursor"])

    assert result.exit_code == 0
    assert "Cleared Cursor SDK credential" in result.output
    assert CredentialStore(db).get("cursor") is None


def test_cli_creds_set_unknown_provider_errors(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        cli,
        ["--db", str(tmp_path / "x.sqlite"), "creds", "set", "bogus", "--value", "y"],
    )
    assert result.exit_code != 0
    assert "unknown credential provider" in result.output


def test_cli_creds_providers_lists_metadata() -> None:
    result = CliRunner().invoke(cli, ["creds", "providers"])
    assert result.exit_code == 0
    assert "cursor" in result.output
    assert "CURSOR_API_KEY" in result.output


def test_cli_creds_set_strips_whitespace(tmp_path: Path) -> None:
    db = tmp_path / "creds.sqlite"
    result = CliRunner().invoke(
        cli,
        ["--db", str(db), "creds", "set", "cursor", "--value", "  spaced  "],
    )

    assert result.exit_code == 0
    assert CredentialStore(db).get("cursor").value == "spaced"  # type: ignore[union-attr]


def test_cli_creds_set_rejects_empty(tmp_path: Path) -> None:
    db = tmp_path / "creds.sqlite"
    result = CliRunner().invoke(
        cli,
        ["--db", str(db), "creds", "set", "cursor", "--value", "  "],
    )
    assert result.exit_code != 0
    assert "must not be empty" in result.output
