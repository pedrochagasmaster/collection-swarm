# Contributing

This guide covers the project layout, development setup, code conventions, and how to extend Collection Swarm with new profiles, strategies, and backends.

## Prerequisites

| Dependency | Version | Required for |
|------------|---------|-------------|
| Python | 3.12+ | All modes |
| Node.js | 22+ | Cursor SDK backend |
| NVIDIA NIM API key | — | NIM backend |
| Cursor API key | — | Cursor SDK backend |

## Setup

### Install in development mode

```bash
pip install -e ".[dev]"
```

This installs the package with development dependencies (`pytest`, `pytest-asyncio`, `httpx`).

### Verify the installation

```bash
collection-swarm test-connection
collection-swarm list-profiles
collection-swarm list-strategies
```

### Set up live model backends (optional)

Collection Swarm resolves API credentials in three interchangeable ways
(first match wins): dashboard-stored values, environment variables, then a
friendly error. Pick whichever fits your workflow:

=== "Dashboard"

    Run `collection-swarm serve` and open the **Settings** page. Each
    provider has a hidden-by-default input with Save and Clear actions.
    Stored values persist in the simulation SQLite database.

=== "CLI"

    ```bash
    collection-swarm creds set cursor                    # interactive prompt
    collection-swarm creds set nvidia_nim --value "$KEY" # scripted setup
    collection-swarm creds list                          # inspect state
    ```

=== ".env file"

    Create a `.env` file in the repo root — useful for CI or transient
    shells:

    ```bash
    NVIDIA_NIM_API_KEY=your_nvidia_key
    CURSOR_API_KEY=your_cursor_key
    ```

See [`modules/credentials.md`](../modules/credentials.md) for the full
resolution contract.

For the Cursor SDK backend:

```bash
cd cursor_sdk_bridge && npm install && cd ..
```

## Project Layout

```
collection-swarm/
├── src/collection_swarm/           # Main package
│   ├── __init__.py
│   ├── agents/                     # Agent implementations
│   │   ├── collector.py            # Collector agent (prompt rendering + turn generation)
│   │   ├── debtor.py               # Debtor agent (profile-driven role-play)
│   │   └── judge.py                # Judge (structured evaluation + constraint checking)
│   ├── analysis/                   # Post-simulation analysis
│   │   ├── compliance.py           # Compliance exclusion filters
│   │   ├── objections.py           # Objection taxonomy extraction
│   │   ├── playbook.py             # Markdown playbook generation
│   │   └── statistics.py           # Strategy comparison and ranking
│   ├── backends/                   # LLM backend implementations
│   │   ├── base.py                 # LLMBackend protocol + LLMResponse dataclass
│   │   ├── router.py               # LLMRouter: dispatches to the correct backend
│   │   ├── scripted.py             # Deterministic scripted backend (offline)
│   │   ├── nim.py                  # NVIDIA NIM backend (via LiteLLM)
│   │   └── cursor_sdk.py           # Cursor SDK backend (via Node bridge)
│   ├── web/                        # Web dashboard
│   │   ├── app.py                  # FastAPI application factory + all endpoints
│   │   ├── seed.py                 # Demo data generator
│   │   └── static/                 # SPA assets (index.html, app.js, styles.css)
│   ├── cli.py                      # Click CLI entry point
│   ├── config.py                   # YAML configuration loader
│   ├── engine.py                   # Simulation engine (conversation loop)
│   ├── models.py                   # Pydantic domain models
│   ├── runner.py                   # Matrix builder + concurrent runner
│   ├── store.py                    # SQLite persistence layer
│   ├── arena.py                    # Elo rating system + tournament logic
│   ├── evolution.py                # Strategy/profile evolution
│   ├── calibration.py              # Judge calibration against human labels
│   ├── model_evaluation.py         # Cursor SDK model-role probing + reports
│   ├── adversarial.py              # Adversarial improvement pipeline
│   └── env.py                      # Environment variable loading
├── config/                         # YAML configuration files
│   ├── debtor_profiles.yaml        # Debtor profile definitions
│   ├── collector_strategies.yaml   # Collector strategy definitions
│   ├── models.yaml                 # Model backend configuration
│   ├── prompts.yaml                # Prompt templates (collector, debtor, judge)
│   └── simulation.yaml             # Simulation parameters (turns, thresholds)
├── cursor_sdk_bridge/              # Node.js bridge for Cursor SDK
├── tests/                          # Test suite (16 files)
├── docs/                           # Generated reports and research
├── assets/                         # Images and infographics
└── pyproject.toml                  # Package definition (setuptools)
```

## Running Tests

```bash
pytest -q
```

For verbose output with tracebacks:

```bash
pytest --tb=short
```

See the [Testing Guide](testing.md) for details on test categories, writing tests, and async testing patterns.

## Code Style and Conventions

### General

- **Type hints** are used throughout. All function signatures include type annotations.
- **Pydantic v2** models for all domain types (`SimulationResult`, `Judgment`, `Profile`, `Strategy`, etc.).
- **`from __future__ import annotations`** at the top of every module for PEP 604 union syntax.
- **Async-first** — simulation engine, agents, and web handlers are all `async`.

### Naming

- Module-level constants: `UPPER_SNAKE_CASE`
- Private helpers: `_leading_underscore`
- Pydantic models: `PascalCase`
- YAML config IDs: `snake_case` (e.g. `empathetic_payment_plan`)

### Imports

- Standard library first, then third-party, then project imports.
- Relative imports within the package (e.g. `from collection_swarm.models import ...`).

### Error handling

- API endpoints raise `HTTPException` with descriptive messages.
- Background jobs catch exceptions and update `WebRunJob.errors`.
- `asyncio.CancelledError` is always re-raised to support job cancellation.

## How to Add New Profiles

1. Edit `config/debtor_profiles.yaml` — add a new entry under `profiles:`.
2. Required fields: `id`, `archetype`, `financial_situation`, `debt_amount`, `debt_age_days`, `debt_type`, `prior_contact_count`, `emotional_state`, `primary_objection`, `responsiveness`, `demographics`, `backstory`.
3. Optional `constraints` list with `text` and optional `rule` (machine-readable).
4. No code changes needed — the config loader picks up the new profile automatically.
5. Verify: `collection-swarm list-profiles` should show the new profile.
6. Test: run a simulation with the new profile and review the transcript.

```yaml
- id: my_new_profile
  archetype: cooperative
  financial_situation: can_pay_partial
  debt_amount: 1200
  debt_age_days: 60
  debt_type: cartao_credito_will
  prior_contact_count: 1
  emotional_state: anxious
  primary_objection: inability_to_pay
  responsiveness: high
  demographics: sudeste_classe_c
  backstory: |
    Detailed backstory for the debtor agent to role-play.
  constraints:
    - text: "Max R$ 100/month."
      rule:
        type: max_payment
        amount: 100
        frequency: monthly
```

## How to Add New Strategies

1. Edit `config/collector_strategies.yaml` — add a new entry under `strategies:`.
2. Required fields: `id`, `tone`, `opening_approach`, `negotiation_tactic`, `escalation_style`, `concession_willingness`, `compliance_adherence`, `follow_up_strategy`.
3. Optional Will Bank fields: `payment_channel`, `primary_anchor`, `discovery_questions`, `framing`, `discount_authority`, `liquidation_disclosure`, `cultural_register`, `rationale`.
4. No code changes needed.
5. Verify: `collection-swarm list-strategies` should show the new strategy.

## How to Add New Backends

To add a new LLM backend:

1. Create a new module in `src/collection_swarm/backends/` (e.g. `my_backend.py`).
2. Implement the `LLMBackend` protocol from `backends/base.py`:

    ```python
    from collection_swarm.backends.base import LLMBackend, LLMResponse
    from collection_swarm.models import Message

    class MyBackend(LLMBackend):
        async def complete(
            self,
            model_name: str,
            messages: list[Message],
            system_prompt: str | None = None,
        ) -> LLMResponse:
            # Call your model provider
            return LLMResponse(
                content="response text",
                model_id=model_name,
                backend="my_backend",
                input_tokens=100,
                output_tokens=50,
                estimated_cost_usd=0.001,
            )
    ```

3. Register the backend in `backends/router.py` so the `LLMRouter` can dispatch to it.
4. Add model entries in `config/models.yaml` with `backend: my_backend`.
5. Write tests in `tests/test_my_backend.py`.

## How to Add New Analysis Modules

Analysis modules live in `src/collection_swarm/analysis/`. Each module:

1. Takes simulation data from the `SimulationStore`.
2. Produces structured results (Pydantic models or dicts).
3. Is surfaced through both the CLI and web API.

To add a new analysis:

1. Create a module in `analysis/` with a pure function interface.
2. Add a CLI command in `cli.py`.
3. Add an API endpoint in `web/app.py`.
4. Write tests.

## Commit Guidelines

- Commit config, code, tests, and docs.
- **Never** commit API keys, `.env` files, or generated databases (`output/`).
- Generated and local-only files are gitignored:
    - `.env`
    - `output/`
    - `cursor_sdk_bridge/node_modules/`
    - Python build artifacts (`*.egg-info`, `__pycache__`, `dist/`)
