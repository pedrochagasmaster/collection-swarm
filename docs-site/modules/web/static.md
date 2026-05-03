# `web/static/` — the single-page app

<span class="cs-kicker">collection_swarm/web/static/</span>

The dashboard's frontend. Vanilla HTML, vanilla CSS, vanilla JavaScript.
No build step, no transpiler, no framework. The whole app loads in a
single GET of `/`.

<dl class="cs-summary">
  <dt>Files</dt>
  <dd>
    <code>index.html</code> (125 lines) · <code>app.js</code> (3,000 lines) ·
    <code>styles.css</code> (3,200 lines) · <code>fonts/</code> (Inter + JetBrains Mono)
  </dd>
  <dt>Bundle size</dt><dd>~ 200 KB before fonts</dd>
  <dt>Build step</dt><dd>None</dd>
</dl>

## File map

| File                         | Purpose                                                                    |
| ---------------------------- | --------------------------------------------------------------------------- |
| `index.html`                 | App shell with the persistent sidebar, the mobile menu button, page slots, and the script tag for `app.js`. |
| `app.js`                     | Page renderers, fetch helpers, state, polling loops, transcript renderer, manual-session controller, charts. |
| `styles.css`                 | Design system: tokens, spacing, color, typography, sidebar, cards, tables, badges, dark/light schemes, responsive breakpoints. |
| `fonts/inter-latin.woff2`, `fonts/inter-latin-ext.woff2` | Self-hosted Inter for body / UI text. |
| `fonts/jetbrains-mono-latin.woff2`, `fonts/jetbrains-mono-latin-ext.woff2` | Self-hosted JetBrains Mono for code / monospace. |

## Navigation model

The sidebar in `index.html` lists every page; `app.js` exposes a global
`navigateTo(pageName)` that toggles the active page section in the main
content area. There's no router; pages are just named container `div`s.

```html
<button class="nav-link" data-page="dashboard" onclick="navigateTo('dashboard')">
  Dashboard
</button>
```

Each page has a sibling `loadPage_<name>()` function in `app.js` that
fetches the relevant data and renders it.

## API consumption

Every fetch call goes through a small helper in `app.js`:

- Read endpoints (GET) — directly fetch and render.
- Write endpoints (POST) — fire the request, then start polling
  `GET /api/jobs/{id}` (or `/api/manual-sessions/{id}`) until the job
  reaches a terminal status.

The polling cadence is ~1s. The frontend never opens a WebSocket — the
job snapshot includes the in-flight `current_run`, which is enough to
stream the transcript in near real-time.

## Theming

Two color schemes (dark and light) are declared at the top of
`styles.css` as CSS custom properties on `[data-theme="dark"]` and
`[data-theme="light"]`. The HTML root opens with `data-theme="dark"`
and the SPA persists the user's choice in `localStorage`. The OS-level
`prefers-color-scheme` is honored on first load.

The colour palette uses tinted neutrals and a deep purple primary
(`oklch(65% 0.2 275)`) so dark mode stays warm rather than monitor
blue.

## Charts and visualizations

`app.js` includes a tiny SVG chart helper used for outcome
distribution, average scores, Elo history, and the leaderboard sparklines.
No external chart library is loaded; the helper draws simple bars,
lines, and donut segments inline. Performance is fine because every
chart renders < 50 data points.

## Manual-session controller

The Manual Run page wires the human side of `ManualSession`. The
controller:

1. Posts the session create call.
2. If the AI is the Collector (human chose Debtor), waits for the AI
   reply before letting the human type.
3. Renders the transcript live as turns arrive.
4. Submits human turns through `POST /api/manual-sessions/{id}/turn`.
5. Switches the input box label between "as Collector" and "as Debtor"
   based on the configured `human_role`.
6. Emits the explicit `[END_CONVERSATION]` marker on a Finish button or
   detects it inline and routes the session into the Judge.

## Why no framework

The app is small enough that a framework would add more lines than it
saves. The trade-off is conscious: the dashboard is meant to be a
reference UI someone can fork into a Vue, React, or Svelte version
without re-thinking the architecture. The vanilla layout makes that
fork mechanical, not interpretive.

## Forking it

If you want to keep the Python backend but rewrite the frontend, the
contract is:

- Every endpoint under `/api/...` returns JSON.
- Long-running operations return a `WebRunJob` snapshot from POST and
  again from GET.
- Manual sessions return a `ManualSession` snapshot from every POST and
  GET.
- The static directory is mounted at `/static`. Everything outside it
  flows through FastAPI.

A new frontend can hit the same API surface and ignore `web/static/`
entirely. The `serve` CLI command will still expose the API; just don't
visit `/`.
