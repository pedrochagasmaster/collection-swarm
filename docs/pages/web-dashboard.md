---
title: Web Dashboard
layout: default
nav_order: 17
---

# Web Dashboard
{: .no_toc }

The FastAPI-powered web interface for browsing results, launching simulations, and generating reports.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Source:** `src/collection_swarm/web/`

## Overview

The web dashboard provides a browser-based interface for all Collection Swarm operations. It is built with **FastAPI** and serves a static HTML/JS/CSS frontend alongside REST API endpoints.

## Starting the Dashboard

```bash
# Optional: seed demo data
collection-swarm seed --count 24

# Start the server
collection-swarm serve --host 127.0.0.1 --port 8000
```

## Application Factory

```python
def create_app(
    config_dir: Path = Path("config"),
    db_path: Path = Path("output/collection_swarm.sqlite"),
) -> FastAPI
```

The factory:
1. Loads configuration from the specified directory.
2. Creates a `SimulationStore` connection.
3. Creates an `LLMRouter` with all configured backends.
4. Registers all API routes.
5. Mounts the static file directory for the frontend.

## API Endpoints

### Configuration

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/api/profiles` | GET | List all configured profiles |
| `/api/strategies` | GET | List all configured strategies |
| `/api/models` | GET | List all configured models |

### Simulations

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/api/simulations` | GET | List simulations with pagination and filters |
| `/api/simulations/{id}` | GET | Get a specific simulation |
| `/api/simulations` | POST | Launch a single simulation (async job) |
| `/api/simulations/{id}/transcript` | GET | Get just the transcript |

### Matrix Runs

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/api/matrix` | POST | Launch a matrix run (async job) |

### Tournaments

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/api/tournaments` | POST | Start a tournament (async job) |
| `/api/tournaments` | GET | List tournament history |
| `/api/leaderboard` | GET | Current Elo rankings |

### Playbook & Analysis

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/api/playbook` | GET | Generate and return playbook as rendered HTML |
| `/api/stats` | GET | Overview statistics |
| `/api/performance/{dimension}` | GET | Performance aggregated by dimension |

### Model Evaluation

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/api/model-report` | GET | Generate offline model-role report |
| `/api/model-report/live` | POST | Run live model probes (async job) |
| `/api/benchmarks` | GET | List completed benchmark reports |

### Manual Sessions

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/api/manual-session` | POST | Start a manual collector-debtor session |
| `/api/manual-session/{id}/turn` | POST | Submit a turn in a manual session |
| `/api/manual-session/{id}/judge` | POST | Request judge evaluation |

### Jobs

| Endpoint | Method | Description |
|:---------|:-------|:------------|
| `/api/jobs/{id}` | GET | Check job status |

## Async Job System

Long-running operations (simulations, matrix runs, tournaments, benchmarks) run as background tasks with status tracking:

```python
@dataclass
class Job:
    id: str
    type: str
    status: str           # "pending", "running", "completed", "failed"
    progress: dict        # Job-specific progress data
    result: Any = None
    error: str | None = None
```

The job system:
1. Creates a job entry with status "pending".
2. Launches an `asyncio.Task` that updates progress in real-time.
3. Returns the job ID immediately.
4. The frontend polls `/api/jobs/{id}` for status updates.

### Job Types

| Type | Description |
|:-----|:------------|
| `simulation` | Single simulation run |
| `matrix` | Matrix sweep |
| `tournament` | Elo tournament |
| `benchmark` | Live model evaluation |

## Security: HTML Sanitization

Playbook output goes through `_render_safe_markdown()`:

```python
def _render_safe_markdown(md_text: str) -> str:
    raw_html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
    return bleach.clean(raw_html, tags=_PLAYBOOK_ALLOWED_TAGS, ...)
```

This prevents XSS attacks from YAML-injected content by:
- Rendering Markdown to HTML using the `markdown` library.
- Stripping all raw HTML except whitelisted tags (`p`, `h1`–`h6`, `table`, `code`, etc.).
- Only allowing safe attributes (`href`, `title`, `align`, `class`).
- Only allowing safe protocols (`http`, `https`, `mailto`).

## Static Frontend

The frontend is a single-page application using vanilla HTML, CSS, and JavaScript:

| File | Description |
|:-----|:------------|
| `web/static/index.html` | Dashboard HTML shell |
| `web/static/app.js` | Client-side logic for all views |
| `web/static/styles.css` | Dashboard styles |

## Demo Data Seeding

**Source:** `src/collection_swarm/web/seed.py`

```python
def generate_seed_data(db_path: Path, num_runs: int = 24) -> int
```

Generates realistic synthetic simulation results for demo purposes. Creates plausible transcripts, judgments, and metadata using randomized combinations of profiles and strategies with the scripted backend's patterns.
