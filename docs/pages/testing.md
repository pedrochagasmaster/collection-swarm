---
title: Testing
layout: default
nav_order: 19
---

# Testing
{: .no_toc }

Test suite structure and coverage.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Source:** `tests/`

## Overview

Collection Swarm has a comprehensive test suite built with **pytest** and **pytest-asyncio**. Tests cover configuration loading, domain models, the conversation engine, judge parsing, SQLite persistence, matrix generation, playbook output, CLI commands, web API routes, and all major subsystems.

## Running Tests

```bash
# Run all tests
pytest -q

# Run with verbose output
pytest -v

# Run a specific test file
pytest tests/test_engine.py
```

### Configuration

From `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

The `asyncio_mode = "auto"` setting means async test functions are automatically detected and run with pytest-asyncio.

## Test Files

| File | Module Tested | Coverage Focus |
|:-----|:-------------|:---------------|
| `test_config.py` | `config.py` | YAML loading, validation, defaults |
| `test_models.py` | `models.py` | Pydantic model validation, serialization |
| `test_engine.py` | `engine.py` | Conversation loop, stalemate detection, end signals |
| `test_judge.py` | `agents/judge.py` | JSON parsing, constraint verification, fallbacks |
| `test_store.py` | `store.py` | SQLite CRUD, queries, schema migration |
| `test_runner.py` | `runner.py` | Matrix building, concurrent execution |
| `test_playbook.py` | `analysis/playbook.py` | Markdown generation, formatting |
| `test_cli.py` | `cli.py` | Click command wiring, output format |
| `test_web.py` | `web/app.py` | FastAPI routes, request/response validation |
| `test_cursor_sdk_backend.py` | `backends/cursor_sdk.py` | Bridge subprocess, error handling |
| `test_model_evaluation.py` | `model_evaluation.py` | Probe scoring, report generation |
| `test_arena.py` | `arena.py` | Elo math, Swiss pairing, round-robin |
| `test_evolution.py` | `evolution.py` | Strategy evolution, YAML parsing, culling |
| `test_adversarial.py` | `adversarial.py` | Profile hardening, fallbacks |
| `test_calibration.py` | `calibration.py` | Pearson correlation, MAE, label loading |
| `test_env.py` | `env.py` | .env file parsing, no-override behavior |

## Key Testing Patterns

### Scripted Backend for Testing

All tests use the `ScriptedBackend` (or mocked backends) to avoid external API calls. This ensures tests are:
- **Fast** — no network latency
- **Deterministic** — same inputs always produce same outputs
- **Offline** — no API keys needed

### Async Test Functions

Engine, runner, and web tests use async functions:

```python
async def test_simulation_completes():
    engine = SimulationEngine(collector, debtor, judge)
    result = await engine.run_simulation(profile, strategy)
    assert result.status == "completed"
```

### Web API Testing

Web tests use `httpx.AsyncClient` with FastAPI's test client:

```python
from httpx import AsyncClient, ASGITransport

async def test_list_profiles():
    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app)) as client:
        response = await client.get("/api/profiles")
        assert response.status_code == 200
```

### SQLite Test Isolation

Store tests use temporary file paths or in-memory databases to avoid polluting the production database.

## Dependencies

| Package | Version | Purpose |
|:--------|:--------|:--------|
| `pytest` | >= 8.0 | Test runner |
| `pytest-asyncio` | >= 0.23 | Async test support |
| `httpx` | >= 0.27 | Async HTTP client for API testing |

These are installed via the `[dev]` optional dependency group:

```bash
pip install -e ".[dev]"
```
