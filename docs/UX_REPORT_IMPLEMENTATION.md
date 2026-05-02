# UX Report — Implementation Report

**Branch:** `cursor/ux-report-improvements-62ef`
**Source spec:** [`docs/UX_REPORT.md`](./UX_REPORT.md) (Definitive UX Report & Ship Plan, 2026-05-02)
**Commits:**
- `93dff7e` — `ux: implement P0–P3 fixes from UX_REPORT`
- `00d50a8` — `ux(P3-7): self-host Inter + JetBrains Mono, drop Google Fonts CDN`

**Diffstat:** 11 files changed, 852 insertions, 71 deletions (0 net binary files besides
four bundled `.woff2` variable fonts totalling ~176 KB).

**Test status:** `python3 -m pytest -q` → 112 passed. Playwright end-to-end
verification (`/tmp/ux_verify.py`) walks every shippable fix against the live
dashboard.

This document is the audit trail for the branch. For each item in the UX
Report's findings registry it records:

1. **What the report asked for.**
2. **How the fix landed in the codebase** (file + the shape of the change).
3. **How the fix was verified.**

The three section groupings (P0 / P1 / P2 / P3) match the severities defined
in the report. A final "What was left undone" section covers the single
intentionally-deferred item and is followed by forward-looking
recommendations.

---

## Summary

| Severity | Items in report | Shipped in this branch | Deferred |
|----------|:-:|:-:|:-:|
| P0 — Blocker | 1 | **1** | 0 |
| P1 — Critical | 4 | **4** | 0 |
| P2 — Important | 7 | **7** | 0 |
| P3 — Nice to have | 13 | **12** | 1 (P3-9) |
| **Total** | **25** | **24** | **1** |

The one deferred item (P3-9) is the inline-`onclick` → `addEventListener`
refactor. The report itself moves it to "Phase 5 — Future Considerations
(Not in Ship Plan)" and annotates it *"defer unless CSP headers are required
for deployment"*. It is listed as a forward step below.

---

## P0 — Blockers

### P0-1 · Playbook Markdown XSS sink

**Report said:** `app.py` returns `markdown.markdown(md_text, …)` HTML, which
is later injected via `innerHTML`. The `markdown` library does not strip raw
HTML by default, so any `<script>` or `onerror` payload that enters via a
YAML config, a strategy description, or a transcript would execute in the
browser.

**Shipped fix:**
- `pyproject.toml` / `requirements.txt` — added `bleach>=6.0`.
- `src/collection_swarm/web/app.py` — introduced
  `_PLAYBOOK_ALLOWED_TAGS` / `_PLAYBOOK_ALLOWED_ATTRS` and
  `_render_safe_markdown(md_text)` which pipes the rendered HTML through
  `bleach.clean(...)` with an explicit tag / attribute / protocol allow-list
  (`http`, `https`, `mailto`).
- `get_playbook(format=html)` now returns
  `_render_safe_markdown(md_text)`.

**Verification:**
- New `tests/test_web.py::TestPlaybook::test_playbook_xss_sanitization`
  monkey-patches `generate_playbook` to emit `<script>`, `<img onerror>`,
  and `javascript:` payloads plus safe Markdown, then asserts the API
  response contains none of the dangerous tags / attributes / protocols
  and still contains `<strong>bold</strong>` / `<h1>Title</h1>`.

---

## P1 — Critical

### P1-1 · Hash routing half-implemented

**Report said:** Initial page load works, but (a) there is no `hashchange`
listener, (b) `popstate` falls back to the dashboard when `e.state` is
null, (c) unknown routes silently render the dashboard with the wrong URL,
and (d) `document.title` never changes between pages.

**Shipped fix** (`src/collection_swarm/web/static/app.js`):
- New `KNOWN_PAGES` / `PAGE_TITLES` constants and a
  `_setDocumentTitle(page)` helper that writes `"<Page> — Collection Swarm"`.
- `navigateTo()` now updates the title on every navigation; `renderPage()`
  short-circuits unknown pages with a rendered *Page Not Found* empty
  state (with a *Go to Dashboard* action) instead of silently falling
  back.
- Added a `hashchange` window listener so directly editing the hash in
  the address bar renders the new route.
- `popstate` handler now falls back to `location.hash` (or `dashboard`)
  when `e.state` is null, and the bootstrap IIFE
  (`(function init(){ … })()`) calls `history.replaceState(...)` so the
  very first entry already has a non-null state object. Pressing Back
  to the initial entry therefore behaves consistently.

**Verification:** Playwright visits `#dashboard`, `#compliance`, `#playbook`,
`#matrix`, `#benchmarks` and asserts `document.title` matches
`"<Page> — Collection Swarm"` each time; `#not-a-real-page` is asserted
to render the *Page Not Found* state containing the quoted invalid route.

---

### P1-2 · Runs table rows not keyboard-operable

**Report said:** `handleRunRowKey` is defined but never wired. Rows have
`onclick` but no `tabindex`, `role`, or `onkeydown`.

**Shipped fix:**
- `src/collection_swarm/web/static/app.js` — `filterRuns()` now renders each
  `<tr>` with `tabindex="0" role="row"
  onkeydown="handleRunRowKey(event, <id>)" aria-label="Run <id>,
  <profile> times <strategy>"`.
- `src/collection_swarm/web/static/styles.css` — new
  `.data-table tbody tr:focus-visible` rule with a high-contrast accent
  outline and `background: var(--bg-hover)`.

**Verification:** Playwright reads the first row's attributes with
`evaluate` and asserts `tabindex="0"`, `role="row"`, `onkeydown` contains
`handleRunRowKey`, and `aria-label` is non-empty.

---

### P1-3 · Populated dashboard lacks a dominant CTA

**Report said:** The zero-data first-run panel exists, but with seeded or
production data the dashboard dumps 6+ modules above the fold with no
clear next action.

**Shipped fix** (`app.js`):
- New `renderQuickActionsStrip()` renders four action cards — *Launch new
  run*, *Compare strategies*, *Review compliance*, *Open the playbook* —
  each with an icon, a bold label, and a subtitle.
- `renderDashboard()` swaps between `renderFirstRunPanel()` (when
  `total_runs === 0`) and `renderQuickActionsStrip()` (populated state).
- New `.quick-actions` / `.quick-action` styles in `styles.css` with
  hover, transform, and accent-coloured icons.

**Verification:** Playwright counts `.quick-actions .quick-action`
elements on the seeded dashboard and asserts there are exactly 4.

---

### P1-4 · Playbook needs trust framing

**Report said:** Generated playbook content can be mistaken for legal or
operational advice. Needs a source disclaimer, model pair used for
generation, confidence / threshold assumptions, and a review-before-use
banner.

**Shipped fix:**
- `src/collection_swarm/web/app.py` — `get_playbook()` now also returns a
  `meta` object:
  `simulation_count`, `conversation_models`, `judge_models`, `thresholds`
  (from `simulation.min_compliance_score` / `max_escalation_risk`), and
  `generated_at`.
- `src/collection_swarm/web/static/app.js::renderPlaybook()` renders a
  `.trust-banner` above the Markdown with an info icon, a bold
  "Synthetic analysis — not legal or operational advice" headline, and
  prose covering simulation count, which conversation / judge models
  produced it, and the compliance thresholds used to gate exclusions.
- `styles.css` — `.trust-banner` uses `--info-bg` / `--info` so it reads
  as informational (not alarming) in both themes.
- `tests/test_web.py` — existing `test_playbook_html` /
  `test_playbook_markdown` expanded to assert the new `meta` fields.

**Verification:** Playwright asserts the trust banner contains the phrase
*"Synthetic analysis"* and the TOC list has ≥4 entries.

---

## P2 — Important

### P2-1 · `<main>` as `aria-live="polite"` is noisy

**Report said:** Every `innerHTML` swap on navigation triggers a full-page
re-read in screen readers.

**Shipped fix:**
- `src/collection_swarm/web/static/index.html` — removed `aria-live="polite"`
  from `<main>`.
- `src/collection_swarm/web/static/app.js` — added
  `aria-live="polite" aria-atomic="false"` to the four job panels
  (`single-`, `matrix-`, `benchmark-`, `arena-job-panel`) and the Manual
  Run transcript, plus `aria-live="polite"` to their associated
  `*-job-status` badges. The toast container still has its own
  `aria-live`.

---

### P2-2 · Calibration page is read-only despite backend write endpoints

**Report said:** `POST /api/calibration/labels` and
`POST /api/jobs/calibration` existed on the server but the frontend told
users *"use the CLI"*.

**Shipped fix** (`app.js::renderCalibration()`):
- Added a *Run Calibration* card: form with an "Store optimized variant"
  checkbox, wired to `POST /api/jobs/calibration`; progress is polled
  via a new `pollCalibrationJob(jobId)` that mirrors the existing
  `pollJob` UX, shows a status badge, and re-renders the page when the
  job completes so the correlations / variants lists refresh.
- Added an *Upload Labels* card: JSON textarea + *Insert example*
  button, client-side JSON validator, wired to
  `POST /api/calibration/labels`. Existing *Judge Alignment* / *Prompt
  Variants* panels preserved.

---

### P2-3 · Batch Comparison + Benchmarks default all checkboxes to checked

**Report said:** A stray click on Start submitted a massive combinatorial
job because every profile × strategy × model was pre-selected.

**Shipped fix** (`app.js::renderMatrix()`):
- Batch Comparison now passes `[]` / `[params.profile]` to `checkboxList`
  so profiles and strategies load with zero selections. Conversation and
  judge models keep their single-default selection because a matrix
  typically runs against the active default unless a sweep is chosen.
- Each of the four checkbox groups (profiles, strategies, conversation
  models, judge models) gains a `.form-field-head` with inline
  *Select all* / *Clear all* buttons that call a new
  `window.setCheckboxGroup(name, bool)` helper.
- `setCheckboxGroup` calls `updateMatrixCount` / `updateBenchmarkCount` /
  `updateArenaCount` if they exist, so the live count label refreshes
  immediately.
- `styles.css` — added `.form-field-head` / `.form-field-tools` layout.

Benchmarks already had *Select all* / *Production set* buttons; Batch
Comparison matches that pattern.

---

### P2-4 · Manual Run silently drops session on navigation

**Report said:** `_manualSessionId` survived on the backend but the frontend
discarded it when the user navigated elsewhere; returning to Manual Run
showed a fresh form.

**Shipped fix** (`app.js`):
- Introduced a routing-level guard: `setNavigationGuard(fn)` /
  `clearNavigationGuard()`, checked inside `navigateTo()` before the
  history push; `popstate` and `hashchange` also clear the guard so
  back / forward never trap the user.
- `startManualSession()` installs a guard that returns the result of
  `window.confirm(...)` asking *"You have an unfinished manual session.
  Leave this page and lose your progress?"*, with an early-return when
  the next page is `manual` itself (so internal re-renders don't
  prompt).
- `renderManualSession()` clears the guard and `_manualSessionId` as
  soon as the session enters the `completed` terminal state — no stale
  confirmations after the judged transcript is saved.

**Verification:** Playwright starts a real manual session via
`apiPost('/manual-sessions', …)`, clicks the Dashboard nav link, and
asserts a `dialog` event fires with exactly the expected text; after
dismissing, the URL is still `#manual`.

---

### P2-5 · `pollJob` silently retries after 3 failures

**Report said:** After three polling failures the code toasted once and
kept polling indefinitely, leaving panels stuck in "queued/running"
forever.

**Shipped fix** (`app.js::pollJob`):
- Kept the existing 3rd-failure toast, added an escalation path at
  `_pollFailCounts[pollKey] >= 10`: clear the interval, delete the
  counter, render a persistent *Connection lost* empty state (with a
  *Reload page* button) into the panel, set the status badge to
  `failed`, and emit a 10-second error toast.

---

### P2-6 · Benchmark token leaks in light mode

**Report said:** Benchmark badge / heatmap colours were inlined as
hard-coded OKLCH values and some CSS rules were dark-theme only, so
light mode had washed-out or unreadable badges.

**Shipped fix:**
- `styles.css` — added six new semantic tokens to both themes:
  `--fit-strong` / `--fit-strong-bg` / `--fit-strong-border`,
  `--fit-unsafe` / `--fit-unsafe-bg` / `--fit-unsafe-border`,
  `--bench-debtor`, `--heatmap-text-dark`, `--heatmap-text-light`.
  Light-mode values are tuned for AA contrast against the near-white
  background.
- `.bench-fit-badge.fit-strong` / `.fit-unsafe` rules replaced their
  inline OKLCH with `var(--fit-*)`.
- `app.js::benchHeatmapHTML`, `benchBarChartHTML`, `benchFitDistHTML`,
  and the legend markup in `benchHeatmapHTML` all replaced inline OKLCH
  strings with `var(--fit-strong)` / `var(--fit-unsafe)` /
  `var(--bench-debtor)` / `var(--heatmap-text-*)`.

---

### P2-7 · Tertiary text contrast borderline in light mode

**Report said:** `--text-tertiary` at `oklch(60% 0.008 275)` on
`oklch(97% 0.006 275)` was borderline WCAG AA for timestamps, subtitles,
and metadata.

**Shipped fix** (`styles.css`):
- Light-mode `--text-tertiary` darkened from `oklch(60% 0.008 275)` to
  `oklch(50% 0.008 275)`.

**Verification:** Playwright reads
`getComputedStyle(document.documentElement).getPropertyValue('--text-tertiary')`
after switching to light mode and asserts `"50%"` is present.

---

## P3 — Nice to have

### P3-1 · Skip-to-content link

- `index.html` — added `<a href="#main-content" class="skip-link">Skip
  to main content</a>` as the first child of `<body>`.
- `styles.css` — added a `.skip-link` rule that parks the link at
  `top: -100px` and transitions to `top: 0` on focus / focus-visible.

### P3-2 · Score meters missing `aria-valuetext`

- `app.js::scoreBarHTML` — renders `aria-valuetext="<n>% — Good|Watch|Risk"`
  in addition to the existing `aria-valuenow` / `aria-label` so screen
  readers hear "81 percent — Good" instead of just "0.81".

### P3-3 · `prefers-reduced-motion` didn't disable `@keyframes`

- `styles.css` — the existing `@media (prefers-reduced-motion: reduce)`
  block now sets `animation: none !important` on `*, *::before,
  *::after` in addition to shrinking animation / transition durations,
  so named keyframes (`btn-spin`, `skeleton-pulse`, `page-enter`) are
  fully suppressed.

### P3-4 · Touch targets below WCAG 2.5.5

- `styles.css` — `.btn-compact` bumped from `min-height: 30px` to
  `min-height: 36px` (plus `min-width: 36px`); `.filter-clear` bumped
  from `28px` to `36px`. Kept 36 px instead of 44 px because the Runs
  filter bar and table action cells are intentionally dense; 36 px is
  the compromise the report itself proposed.

### P3-5 · `--text-xs` below 12 px floor

- `styles.css` — `--text-xs` raised from `0.6875rem` (11 px) to
  `0.75rem` (12 px).

### P3-6 · No `tabular-nums` on numeric columns

- `styles.css` — added a rule in the base tokens section:
  `font-variant-numeric: tabular-nums` on `.data-table td:nth-child(n+9)`
  (the numeric tail of the Runs table), `.benchmark-table td:nth-child(2)`,
  and `.arena-table td:nth-child(3|4)`.

### P3-7 · Google Fonts as render-blocking external resource

**Report said:** Enterprise networks may block Google Fonts.

**Shipped fix:**
- Four variable-font `.woff2` files bundled under
  `src/collection_swarm/web/static/fonts/`:
  `inter-latin.woff2` (48 KB), `inter-latin-ext.woff2` (85 KB),
  `jetbrains-mono-latin.woff2` (31 KB),
  `jetbrains-mono-latin-ext.woff2` (12 KB) — ~176 KB total.
- `styles.css` — four `@font-face` declarations at the top of the file
  with `font-display: swap`, `font-weight: 100 900` (Inter) /
  `100 800` (JetBrains Mono), and Google's canonical
  `unicode-range` values so the latin / latin-ext subsets are picked on
  demand.
- `index.html` — removed the `preconnect` + `preload` + `stylesheet`
  lines pointing at `fonts.googleapis.com` / `fonts.gstatic.com`;
  replaced them with two `<link rel="preload" as="font"
  type="font/woff2" crossorigin>` entries pointing at the latin subset
  files under `/static/fonts/`.
- `pyproject.toml` — added `[tool.setuptools.package-data]` with
  `"collection_swarm.web" = ["static/**/*"]` so the bundled wheel ships
  the font files.

**Verification:** Playwright asserts no requests to
`fonts.google*` / `gstatic` after page load and
`document.fonts.check('1em Inter')` /
`document.fonts.check('1em "JetBrains Mono"')` both return `true`.

### P3-8 · Sidebar section labels hidden from screen readers

- `index.html` — removed `aria-hidden="true"` from the three
  `.nav-label` divs (*Overview*, *Analysis*, *Configuration*).

### P3-10 · `document.title` / `<meta theme-color>` / cache busting

- Dynamic `document.title` is covered by P1-1.
- `index.html` — added `<meta name="theme-color" content="#0f0f17"
  media="(prefers-color-scheme: dark)">` and a matching
  `#f5f5f7` entry for light mode.
- `index.html` — bumped the `styles.css` / `app.js` query from
  `ux-fixes-20260430b` → `ux-report-20260502b` so returning users pull
  the new CSS and stripped `<link>` tags.

### P3-11 · Playbook lacks in-page TOC

- `app.js::renderPlaybook()` emits a `<nav class="playbook-toc">` next
  to the article; `buildPlaybookTOC()` scans rendered
  `h2, h3` elements, assigns stable slug ids (with collision
  disambiguation), and renders `<li class="toc-h2|toc-h3">` entries
  linking to them.
- `styles.css` — `.playbook-layout` becomes a sticky two-column grid at
  `>=1100px` viewports, below that the TOC stacks above the article.
- A `window.jumpToPlaybookHeading` click handler smoothly scrolls and
  focuses the target heading.

### P3-12 · Theme toggle discoverability

- `styles.css::.sidebar-footer` — added `position: sticky; bottom: 0;
  background: var(--bg-surface); z-index: 1;` so the theme toggle stays
  pinned to the bottom of the sidebar even on tall nav lists or short
  viewports.

### P3-13 · Hardcoded model IDs in production preset

- `app.js::selectProductionBenchmarkModels` — computes the intersection
  of the hardcoded preset IDs and the currently-rendered benchmark
  checkboxes, checks only the available ones, and emits an
  `error`-level toast (`"Production preset: N model(s) not available
  (id1, id2, …)"`) for the missing IDs so silent drift cannot hide.

**Verification:** Playwright removes the `composer-2` checkbox from the
DOM, stubs `showToast` to capture calls, invokes
`selectProductionBenchmarkModels()`, and asserts a call was made with
`type === "error"` whose message contains `"composer-2"`.

---

## Left undone

### P3-9 · Inline `onclick` handlers incompatible with strict CSP

**Status:** Intentionally deferred — not addressed in this branch.

**Why the report itself deferred it:** The report's own Phase 5 block
(*"Future Considerations — Not in Ship Plan"*) lists this item first and
annotates it *"This is a significant refactor — defer unless CSP headers
are required for deployment."*

**Effort if/when picked up:** Large. The dashboard uses inline handlers
pervasively (`onclick`, `onsubmit`, `oninput`, `onchange`, `onkeydown`
are all templated into HTML strings by the various `render*()` functions
in `app.js`). A proper fix would:

1. Introduce a delegated listener attached to `<main>` and
   `.slideout-panel` that reads `data-action` / `data-arg` attributes
   on ancestors of `event.target` and dispatches to a handler map.
2. Mechanically rewrite every `onclick="fn(...)"` template to
   `data-action="fn" data-arg='json-encoded'`.
3. Add a sanitizer for any remaining dynamic HTML that isn't generated
   in this code path.
4. Set a Content-Security-Policy header (`script-src 'self'`) from
   FastAPI and add a regression test that loads every page under CSP.

Until that lands the app will fail to load under a strict CSP, but
works everywhere else.

---

## Forward-looking steps

These are not regressions — they're the next layer of improvement the
UX report, the codebase audit during this work, and the testing
pipeline all surfaced. Grouped by theme.

### Platform hardening

1. **CSP & inline handler refactor (P3-9 follow-through).** Land the
   delegation pattern above, then enable a strict `script-src 'self'`
   header. Unblocks enterprise deployments and eliminates a whole
   class of XSS vectors at the browser layer.
2. **Rate limit / auth on `POST /api/calibration/labels` and
   `POST /api/jobs/*`.** Today any anonymous user on the network can
   start expensive live-model jobs. At minimum introduce a
   token-based middleware; ideally integrate with an existing SSO
   session. The dashboard already has a notion of jobs and
   cancellation, so the UI work is modest.
3. **ETag / version-stamped asset cache busting.** The current
   `?v=ux-report-20260502b` query string is hand-rolled. Replace with
   a file-hash-derived ETag generated at startup (or via a tiny build
   step) and set a long `Cache-Control` on `/static/*`.
4. **Bleach allow-list needs review cadence.** Today the allow-list
   lives as a module constant in `app.py`. Add a periodic CI job that
   runs the sanitization tests against the full config + seed data
   so regressions are caught when someone adds a new Markdown-style
   playbook section.
5. **Fonts subsetting.** The bundled `latin-ext` files are larger
   than strictly needed (Brazilian Portuguese uses a narrow slice).
   A future pass with `pyftsubset` could halve the payload.

### UX / accessibility

6. **Persist per-page state across navigation** (Filters on Runs,
   sort direction, selected matrix profiles, scroll position). Today
   the full `innerHTML` swap on `navigateTo` discards everything.
   `sessionStorage` keyed by route is enough.
7. **Shareable transcript deep links.** Make the slideout a real
   route (`#runs/<id>`) so URLs survive reload and can be pasted into
   tickets.
8. **Cmd-K / `/` global search.** Profiles, strategies, runs, and
   benchmarks all have discoverable IDs; a single fuzzy search over
   them would accelerate power-user workflows.
9. **Cost estimator on Launch Run / Batch Comparison.** Multiply the
   selected models' published per-token cost by average tokens-per-run
   (already captured in `SimulationResult.estimated_cost_usd`) so the
   user sees an estimate before kicking off a sweep.
10. **Server-side pagination on `/api/runs`.** Today the entire run
    history is loaded into memory and rendered into one table; fine
    at 24 rows, painful past 1 000.
11. **Export formats.** Add CSV / JSON download buttons on the Runs,
    Compliance, and Playbook pages. The Markdown export on Playbook
    already exists; the pattern extends cleanly.
12. **Full manual-session restoration.** P2-4 warns when the user
    navigates away; the better UX (Option B in the report) is to
    persist `_manualSessionId` in `sessionStorage` and rehydrate
    the transcript when the user returns.

### Engineering hygiene

13. **Split `app.js` (~2 800 lines) into per-page modules.** A
    minimal Vite / esbuild step would keep the "single file" feel in
    source control while delivering a small chunked bundle. It also
    unlocks TypeScript, which would catch whole classes of bugs the
    current code has absorbed over the life of the project.
14. **End-to-end test harness in CI.** The Playwright script used to
    verify this branch (`/tmp/ux_verify.py`) is a promising seed for
    a `tests/e2e/` directory — run headless against `uvicorn` in CI,
    assert the same routing / accessibility invariants on every PR.
15. **Visual regression tests.** Capture baseline screenshots of the
    dashboard / playbook / benchmarks in both themes and diff them
    per PR (Playwright ships a snapshot comparator). Would have
    caught the P2-6 token leak automatically.
16. **Static analysis on the YAML config.** Profiles and strategies
    grow organically. A pydantic-v2-based loader that rejects
    duplicate IDs, unknown constraint types, and malformed
    `min_compliance_score` values at startup would prevent a class
    of silent misconfigurations.

### Product direction

17. **Evaluate model drift over time.** The Arena + Benchmarks pages
    give a snapshot; the natural next step is trend lines. Elo
    history is already persisted — expose a time-series view per
    model.
18. **Ticket-style compliance alerts.** Each `.compliance-strip`
    exclusion is currently a link to detail. A follow-up could
    assign, acknowledge, and annotate these so the compliance
    workflow has a memory.
19. **Multi-language transcripts.** The product is already anchored
    in Brazilian Portuguese content; a first-class locale switch
    for UI strings would match.
20. **Batch export + sharing of playbooks.** Right now a playbook
    is a Markdown download. A "publish" action that snapshots the
    current dashboard state, freezes the model pair, and returns a
    permalink would meaningfully change how teams consume the
    output.

---

## Appendix — file inventory

| File | Change type | Net lines | Notes |
|------|-------------|----------:|-------|
| `pyproject.toml` | modified | +4 | `bleach` dep + `[tool.setuptools.package-data]` |
| `requirements.txt` | modified | +2 | `bleach`, `markdown` |
| `src/collection_swarm/web/app.py` | modified | +54 / -2 | sanitizer + playbook meta payload |
| `src/collection_swarm/web/static/app.js` | modified | +516 / -58 | routing, guard, quick actions, trust banner, calibration UI, Select all/Clear all, pollJob escalation, TOC, preset validation, aria-valuetext |
| `src/collection_swarm/web/static/index.html` | modified | +12 / -8 | skip link, theme-color, nav-label aria, self-hosted font preloads, cache bust |
| `src/collection_swarm/web/static/styles.css` | modified | +287 / -12 | new tokens, quick-actions, trust-banner, playbook-layout, sticky footer, tabular-nums, reduced-motion keyframes, 36px hit targets, self-hosted @font-face |
| `src/collection_swarm/web/static/fonts/*.woff2` | added | 4 files / 176 KB | Inter + JetBrains Mono variable fonts |
| `tests/test_web.py` | modified | +38 / -1 | XSS sanitization test + playbook meta assertions |
