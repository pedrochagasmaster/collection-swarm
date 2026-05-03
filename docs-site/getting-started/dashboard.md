# The web dashboard

The dashboard is a FastAPI app that serves a single-page application from
`src/collection_swarm/web/static/`. It is the easiest way to launch runs,
watch them progress in real time, browse historical transcripts, and read
the rendered Playbook.

## Seed demo data

If you want a populated dashboard before running anything live:

```bash
collection-swarm seed --count 24
```

The seed command synthesizes 24 realistic Brazilian-Portuguese transcripts
across the 10 canonical Profile × Strategy combos defined in
[`web/seed.py`](../modules/web/seed.md), wires up plausible Judgment
scores, and inserts everything into `output/collection_swarm.sqlite`.

## Start the server

```bash
collection-swarm serve
```

By default this binds `127.0.0.1:8000`. Pass `--host 0.0.0.0` to expose it
on a LAN, or `--port 8080` to switch ports. The `--reload` flag is rejected
with a clear error because Uvicorn's reloader needs an import string and
the dashboard uses a configured factory.

Open <http://127.0.0.1:8000> and you'll land on the Dashboard view.

## Pages at a glance

| Page                | Source              | Reads / Writes                                                      |
| ------------------- | ------------------- | ------------------------------------------------------------------- |
| Dashboard           | `index.html` + `app.js` | `GET /api/dashboard`                                            |
| Simulation runs     | `index.html` + `app.js` | `GET /api/runs`, `GET /api/runs/{id}`                            |
| Launch run          | `index.html` + `app.js` | `POST /api/jobs/simulations`                                     |
| Batch comparison    | `index.html` + `app.js` | `POST /api/jobs/matrix`                                          |
| Manual run          | `index.html` + `app.js` | `POST /api/manual-sessions`, `POST /api/manual-sessions/{id}/turn` |
| Playbook            | `index.html` + `app.js` | `GET /api/playbook?format=html`                                   |
| Compliance          | `index.html` + `app.js` | `GET /api/compliance/exclusions`                                  |
| Arena leaderboard   | `index.html` + `app.js` | `GET /api/arena/leaderboard`                                     |
| Tournaments         | `index.html` + `app.js` | `POST /api/jobs/tournaments`                                     |
| Evolution pool      | `index.html` + `app.js` | `GET /api/evolution/pool`                                        |
| Calibration         | `index.html` + `app.js` | `POST /api/calibration/labels`, `POST /api/jobs/calibration`     |
| Model benchmarks    | `index.html` + `app.js` | `POST /api/jobs/model-benchmarks`                                |
| Settings            | `index.html` + `app.js` | `GET /api/credentials`, `PUT /api/credentials/{id}`, `DELETE /api/credentials/{id}` |

A full HTTP API matrix lives in [API reference](../reference/api.md).

## Settings: managing API credentials

The **Settings** page (Configuration section in the sidebar) is the
dashboard's surface for storing the API keys the live backends need. Each
provider card shows:

- Status: **Stored in dashboard**, **From environment**, or **Not
  configured**.
- A hidden-by-default input for the new value, with a Show/Hide toggle.
- A masked preview (first four + last four characters) of the stored
  value so you can confirm which key is active without revealing it.
- A **Clear stored value** action that removes the dashboard row and
  lets the backends fall back to the matching env var, if any.

Values live in the `dashboard_credentials` table of the same SQLite file
that holds simulations (`output/collection_swarm.sqlite` by default), so
switching `--db` swaps credentials along with the data.

The resolver precedence is **dashboard store → environment variable →
friendly error**. For the programmatic contract, see
[`modules/credentials.md`](../modules/credentials.md).

## Anatomy of a job

Every long-running operation in the UI — single simulations, matrix sweeps,
tournaments, calibration runs, model benchmarks — is dispatched through
`POST /api/jobs/...` endpoints. Each returns a `WebRunJob` snapshot:

```json
{
  "id": "job_a1b2c3d4e5",
  "kind": "matrix",
  "status": "queued",
  "total": 12,
  "completed": 0,
  "failed": 0,
  "current_run": null,
  "result_ids": [],
  "errors": [],
  "message": "Queued 12 matrix simulations.",
  "started_at": "2026-05-03T10:39:00+00:00",
  "ended_at": null
}
```

The frontend polls `GET /api/jobs/{id}` to render progress. `current_run`
carries the in-flight `SimulationResult` so the UI can stream the
transcript turn by turn.

Jobs are cancellable via `POST /api/jobs/{id}/cancel`. The dispatcher
flips the status, marks the asyncio task for cancellation, and the next
turn boundary cleanly aborts.

## Manual role-play sandbox

The Manual Run page creates a `ManualSession` where you (the human) take
either the Collector or Debtor role and the AI plays the other side. Each
turn streams through the same router and engine the automated runs use,
which makes it the fastest way to sanity-check a new Strategy or Profile
before throwing matrix runs at it.

When a human session ends — by `[END_CONVERSATION]`, the turn limit, or a
manual finish — the same Judge module evaluates the transcript, the result
is persisted, and it appears in the regular Runs list with an
`ended_by` of `collector` / `debtor` / `turn_limit`.

## What the dashboard cannot do

By design, the dashboard is a UI on top of the same engine the CLI uses.
Anything you can do in one you can do in the other. The only operator
actions that remain CLI-only:

- `collection-swarm test-connection` — quick router smoke test.
- `collection-swarm reset-elo` — wipe Elo ratings and history.

Both could be wired up to the dashboard if needed; PRs welcome.
