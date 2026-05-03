# Testing Guide

Collection Swarm uses **pytest** with the **pytest-asyncio** plugin for async test support. The test suite runs entirely offline using the scripted backend — no API keys or external services required.

## Running Tests

### Full suite

```bash
pytest -q
```

### With tracebacks

```bash
pytest --tb=short
```

### Single file

```bash
pytest tests/test_engine.py -v
```

### Single test

```bash
pytest tests/test_engine.py::test_engine_runs_scripted_simulation -v
```

## Test Suite Overview

The test suite spans 16 test files covering every major subsystem:

| File | Category | What it tests |
|------|----------|---------------|
| `test_config.py` | Configuration | YAML config loading, profile/strategy/model availability, prompt content, simulation parameters |
| `test_models.py` | Domain models | Pydantic model serialization, validation, constraint rules, enum behavior |
| `test_engine.py` | Simulation engine | End-signal stripping, stalemate detection, full scripted simulation lifecycle |
| `test_judge.py` | Judge agent | Judgment parsing, constraint violation detection, heuristic scoring |
| `test_runner.py` | Matrix runner | Matrix cell generation, concurrent execution, repetition handling |
| `test_store.py` | SQLite store | CRUD operations, status counts, cost summaries, run retrieval, Elo persistence |
| `test_playbook.py` | Playbook generation | Markdown output structure, strategy ranking, exclusion reporting |
| `test_cursor_sdk_backend.py` | Cursor SDK backend | Node bridge communication, response parsing, error handling |
| `test_model_evaluation.py` | Model evaluation | Probe generation, report building, role-specific scoring |
| `test_cli.py` | CLI commands | Command invocation, argument parsing, output formatting |
| `test_web.py` | Web dashboard | All API endpoints, job lifecycle, manual sessions, seed data, SPA assets |
| `test_arena.py` | Arena / Elo | Rating updates, Swiss/round-robin pairings, tournament persistence |
| `test_evolution.py` | Evolution | Strategy mutation, lineage tracking, pool management |
| `test_adversarial.py` | Adversarial | Adversarial improvement pipeline, prompt perturbation |
| `test_calibration.py` | Calibration | Label storage, judge accuracy scoring, variant management |
| `test_env.py` | Environment | Env variable loading, `.env` file handling |

## Test Categories

### Configuration tests (`test_config.py`)

Verify that the YAML configuration files load correctly and contain expected values:

```python
def test_load_default_config() -> None:
    config = load_app_config(Path("config"))
    assert "cooperative_hardship" in config.profiles
    assert "empathetic_payment_plan" in config.strategies
    assert config.default_conversation_model == "local-scripted"
```

### Engine tests (`test_engine.py`)

Test the simulation conversation loop, including end-signal parsing and stalemate detection:

```python
def test_strip_end_signal_removes_marker() -> None:
    content, ended = strip_end_signal("Thanks [END_CONVERSATION]")
    assert content == "Thanks"
    assert ended is True

async def test_engine_runs_scripted_simulation() -> None:
    config = load_app_config("config")
    router = LLMRouter(config.models, cursor_sdk_prompts=config.prompts.cursor_sdk)
    engine = SimulationEngine(
        CollectorAgent(router, "local-scripted", config.prompts.collector),
        DebtorAgent(router, "local-scripted", config.prompts.debtor),
        Judge(router, "local-judge", config.prompts.judge),
        max_turns=settings.max_turns,
    )
    result = await engine.run_simulation(
        config.profile("cooperative_hardship"),
        config.strategy("empathetic_payment_plan"),
    )
    assert result.status == "completed"
    assert result.judgment is not None
```

### Store tests (`test_store.py`)

Test SQLite persistence including save/retrieve cycles, status counting, and Elo operations:

```python
def test_save_and_retrieve_run(tmp_path: Path) -> None:
    store = SimulationStore(tmp_path / "test.sqlite")
    result = _make_result()
    store.save_run(result)
    retrieved = store.get_run(result.id)
    assert retrieved.id == result.id
    assert retrieved.judgment is not None
```

### Web dashboard tests (`test_web.py`)

Integration tests using FastAPI's `TestClient`. Tests cover all API endpoints, job creation and polling, manual session lifecycle, and SPA asset serving:

```python
class TestDashboard:
    def test_dashboard_returns_summary(self, seeded_client: TestClient) -> None:
        resp = seeded_client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_runs"] == 12

class TestManualSessions:
    def test_manual_debtor_session_completes_and_saves(self, empty_client: TestClient) -> None:
        resp = empty_client.post("/api/manual-sessions", json={
            "profile_id": "cooperative_hardship",
            "strategy_id": "empathetic_payment_plan",
            "human_role": "debtor",
            "conversation_model": "local-scripted",
            "judge_model": "local-judge",
        })
        assert resp.json()["status"] == "waiting_for_human"
```

## Writing New Tests

### File placement

Place tests in the `tests/` directory with the naming convention `test_<module>.py`.

### Fixtures

Common fixtures used across test files:

| Fixture | Scope | Description |
|---------|-------|-------------|
| `tmp_path` | function | pytest built-in — temporary directory for each test |
| `seeded_client` | function | FastAPI `TestClient` with 12 pre-seeded simulation runs |
| `empty_client` | function | FastAPI `TestClient` with an empty database |

### Creating test fixtures

```python
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from collection_swarm.web.app import create_app
from collection_swarm.web.seed import generate_seed_data

@pytest.fixture()
def seeded_client(tmp_path: Path) -> TestClient:
    db_path = tmp_path / "test.sqlite"
    generate_seed_data(db_path=db_path, num_runs=12)
    app = create_app(config_dir=Path("config"), db_path=db_path)
    return TestClient(app)
```

### Testing async code

The project uses `pytest-asyncio` with `asyncio_mode = "auto"` (configured in `pyproject.toml`). Async test functions are detected and executed automatically — no decorator needed:

```python
async def test_engine_runs_simulation() -> None:
    # async test functions run automatically
    result = await engine.run_simulation(profile, strategy)
    assert result.status == "completed"
```

!!! info "asyncio_mode = auto"
    With `asyncio_mode = "auto"` in `pyproject.toml`, any `async def test_*` function is automatically recognized as an async test. You do **not** need `@pytest.mark.asyncio`.

### Testing web endpoints

Use FastAPI's synchronous `TestClient` for API tests. Background jobs are async but `TestClient` handles the event loop internally:

```python
def test_launch_simulation(empty_client: TestClient) -> None:
    resp = empty_client.post("/api/jobs/simulations", json={
        "profile_id": "cooperative_hardship",
        "strategy_id": "empathetic_payment_plan",
        "conversation_model": "local-scripted",
        "judge_model": "local-judge",
    })
    assert resp.status_code == 200
    job_id = resp.json()["id"]

    # Poll for completion
    for _ in range(20):
        data = empty_client.get(f"/api/jobs/{job_id}").json()
        if data["status"] in {"completed", "failed"}:
            break
    assert data["status"] == "completed"
```

### Testing with monkeypatch

Use `monkeypatch` to replace expensive external calls (e.g. live model probes) with deterministic fakes:

```python
def test_benchmark_job(empty_client, monkeypatch):
    async def fake_probes(*args, **kwargs):
        return (
            RoleProbe("gpt-5.5", "collector", "ok", 0.01, "Response text"),
        )
    monkeypatch.setattr("collection_swarm.web.app.run_live_role_probes", fake_probes)

    resp = empty_client.post("/api/jobs/model-benchmarks", json={...})
    assert resp.status_code == 200
```

### Testing database operations

Always use `tmp_path` for SQLite databases so tests are isolated:

```python
def test_store_operations(tmp_path: Path) -> None:
    store = SimulationStore(tmp_path / "test.sqlite")
    # Database is created automatically
    result = _make_simulation_result()
    store.save_run(result)
    retrieved = store.get_run(result.id)
    assert retrieved.id == result.id
```

## Test Configuration

The test configuration lives in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

| Setting | Value | Description |
|---------|-------|-------------|
| `asyncio_mode` | `"auto"` | Automatically detect and run async test functions |
| `testpaths` | `["tests"]` | Directory to search for test files |

## Dependencies

Test dependencies are declared as optional in `pyproject.toml`:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "httpx>=0.27",
]
```

| Package | Purpose |
|---------|---------|
| `pytest` | Test framework |
| `pytest-asyncio` | Async test support |
| `httpx` | Required by FastAPI's `TestClient` |

## Offline Testing

All tests run with the **scripted backend** and **heuristic judge** — deterministic backends that require no API keys. This means:

- The full test suite runs in seconds.
- CI/CD pipelines need no secret management.
- Tests produce repeatable results across environments.

To test live backends, use the CLI or dashboard with actual API keys configured.
