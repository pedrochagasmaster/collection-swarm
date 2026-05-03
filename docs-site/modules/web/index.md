# Web Dashboard

The Collection Swarm web dashboard is a single-page application backed by a **FastAPI** server that lets you browse simulation results, launch new runs, compare strategies, and generate playbooks — all without touching the CLI.

## Architecture

The dashboard is created by the factory function `create_app()` in `src/collection_swarm/web/app.py`:

```python
from collection_swarm.web.app import create_app

app = create_app(
    config_dir=Path("config"),
    db_path=Path("output/collection_swarm.sqlite"),
)
```

| Component | Location | Description |
|-----------|----------|-------------|
| FastAPI app | `src/collection_swarm/web/app.py` | API endpoints and application factory |
| Static assets | `src/collection_swarm/web/static/` | SPA front-end (`index.html`, `app.js`, `styles.css`) |
| Seed data | `src/collection_swarm/web/seed.py` | Demo data generator for quick onboarding |

Static files are mounted at `/static` and the SPA entry point is served at `GET /`.

## Quick Start

### 1. Seed demo data (optional)

Populate the database with realistic simulation results so the dashboard has data to display immediately:

```bash
collection-swarm seed --count 24
```

This calls `generate_seed_data()` which creates `SimulationResult` rows complete with transcripts, judgments, and token/cost metadata.

### 2. Start the dashboard

```bash
collection-swarm serve
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

!!! tip "Custom bind address"
    Pass `--host` and `--port` to change the listen address:

    ```bash
    collection-swarm serve --host 0.0.0.0 --port 9000
    ```

## Features

The dashboard exposes every major capability through its UI:

| Feature | API Group | Description |
|---------|-----------|-------------|
| **Dashboard overview** | `/api/dashboard` | Aggregate stats: total runs, completion rate, outcome distribution, average scores, cost summary |
| **Run browser** | `/api/runs` | Filter runs by status, profile, or strategy; inspect full transcripts and judgments |
| **Simulation launcher** | `/api/jobs/simulations` | Fire a single simulation from the browser |
| **Matrix runs** | `/api/jobs/matrix` | Sweep across profiles × strategies × models × reps in one click |
| **Tournaments** | `/api/jobs/tournaments` | Run Swiss or round-robin Elo-rated tournaments |
| **Arena leaderboard** | `/api/arena/leaderboard` | View Elo rankings for strategies and profiles, filterable by model pair |
| **Evolution pool** | `/api/evolution/pool` | Browse evolved strategies and profiles with lineage metadata |
| **Playbook generation** | `/api/playbook` | Generate and render a strategy playbook in HTML or Markdown |
| **Calibration** | `/api/calibration/*` | Upload human labels, run calibration jobs, view judge accuracy metrics |
| **Model benchmarks** | `/api/model-benchmarks/*` | Benchmark Cursor SDK models across collector/debtor/judge roles |
| **Manual sessions** | `/api/manual-sessions` | Human-in-the-loop role-play: take the collector or debtor seat |

## Job System

Long-running operations (simulations, matrix runs, tournaments, benchmarks, calibration) are executed as **background `asyncio` tasks** and tracked through the `WebRunJob` dataclass:

```python
@dataclass
class WebRunJob:
    id: str              # e.g. "job_a1b2c3d4e5"
    kind: str            # "single" | "matrix" | "tournament" | "model_benchmark" | "calibration"
    status: str          # "queued" | "running" | "completed" | "failed" | "cancelled"
    total: int           # total units of work
    completed: int       # successfully finished units
    failed: int          # failed units
    current_run: SimulationResult | None
    result_ids: list[str]
    errors: list[str]    # last 5 errors
    artifacts: dict[str, str]
    benchmark_report: dict | None
    message: str
    started_at: str
    ended_at: str | None
```

### Job lifecycle

1. **POST** to a launch endpoint (e.g. `/api/jobs/simulations`) — returns the job snapshot immediately with `status: "queued"`.
2. **Poll** `GET /api/jobs/{job_id}` to watch `completed`/`failed` counters advance.
3. **Cancel** via `POST /api/jobs/{job_id}/cancel` — the backing `asyncio.Task` is cancelled.
4. **List** all jobs with `GET /api/jobs` (newest first).

!!! info "Concurrency control"
    Matrix and tournament jobs accept a `concurrency` parameter (1–10) that controls the `asyncio.Semaphore` used to limit parallel simulations.

## Markdown Rendering & XSS Safety

The playbook endpoint can return rendered HTML. Because profile/strategy YAML and transcript text could theoretically contain malicious markup, all Markdown-to-HTML conversion passes through a sanitization pipeline:

1. **Render** with `markdown.markdown()` (extensions: `tables`, `fenced_code`).
2. **Sanitize** with `bleach.clean()` using an explicit allow-list of safe tags and attributes.

Blocked constructs include `<script>`, `onerror` attributes, `javascript:` URIs, and `<img>` tags.

```python
_PLAYBOOK_ALLOWED_TAGS = [
    "p", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "table", "thead", "tbody", "tr", "th", "td",
    "code", "pre", "blockquote",
    "strong", "em", "a", "br", "hr", "span", "div",
]
```

## Seed Data

`generate_seed_data()` populates the SQLite database with demo results across representative profile/strategy combinations. Each seed run includes:

- A multi-turn transcript (hand-authored for key combos, generic for others)
- A complete `Judgment` with realistic score jitter
- Token counts and cost estimates

```python
from collection_swarm.web.seed import generate_seed_data

generate_seed_data(
    db_path=Path("output/collection_swarm.sqlite"),
    num_runs=24,
)
```

The seed combos cover the full breadth of the catalog:

| Profile | Strategy |
|---------|----------|
| `cooperative_hardship` | `empathetic_payment_plan` |
| `written_proof_disputer` | `problem_solving_callback` |
| `hostile_avoidant` | `neutral_reminder` |
| `liquidation_confused` | `liquidation_explainer` |
| `scam_suspicious` | `whatsapp_self_service` |
| `superendividado_chronic` | `superendividamento_referral` |
| `willbank_blocked_balance_hardship` | `blocked_balance_hardship_plan` |
| `willbank_micro_merchant_cashflow` | `micro_merchant_cashflow_alignment` |
| `willbank_fgc_waiting_high_balance` | `reimbursement_milestone_callback` |
| `willbank_low_digital_access` | `low_digital_access_guidance` |

## Environment Variables

The dashboard respects the following environment variables when using the `create_app_from_env()` factory (used by uvicorn reload mode):

| Variable | Default | Description |
|----------|---------|-------------|
| `COLLECTION_SWARM_CONFIG_DIR` | `config` | Path to the YAML configuration directory |
| `COLLECTION_SWARM_DB_PATH` | `output/collection_swarm.sqlite` | Path to the SQLite database |

## CLI Options

```
Usage: collection-swarm serve [OPTIONS]

  Launch the web dashboard.

Options:
  --host TEXT     Bind host.  [default: 127.0.0.1]
  --port INTEGER  Bind port.  [default: 8000]
  --help          Show this message and exit.
```

```
Usage: collection-swarm seed [OPTIONS]

  Generate realistic demo data for the web dashboard.

Options:
  --count INTEGER  Number of seed simulations.  [default: 24]
  --help           Show this message and exit.
```
