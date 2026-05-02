# Collection Swarm — Web Dashboard UX Report

**Tested URL:** `http://127.0.0.1:8000` (FastAPI dashboard, `collection-swarm serve`)
**Build:** `app.js?v=ux-fixes-20260430b`
**Demo data:** 24 seeded simulations (`collection-swarm seed --count 24`)
**Browsers:** Chromium via Selenium remote debugging
**Viewports tested:** 1024×655 desktop, 390×844 mobile, 1024px light theme
**Method:** end-to-end click-through of all 13 pages plus targeted code-level audit of `index.html`, `styles.css` (≈2,950 lines) and `app.js` (≈2,530 lines).

---

## TL;DR

The dashboard is **functionally complete, fast, and visually coherent**. Every nav target loaded with no console errors, no failed network requests, and theme/mobile behavior worked. The product feels closer to a polished internal ops tool than to typical AI-slop SaaS, helped by purposeful empty states, OKLCH tokens, and a real focus-trap on the slideout.

The headline gaps are **not visual** — they are **interaction depth and IA fidelity**:

1. **Keyboard parity on the Runs table is incomplete.** Rows are not focusable; the per-row "View" button is the only keyboard path to a transcript. The row's own click target and the dead `handleRunRowKey` handler imply the intent was full row-as-button.
2. **Hash routing is one-way.** `navigateTo()` writes via `pushState`, but the app never listens to `hashchange`/`popstate` for the hash itself, so back/forward and direct hash edits silently land on the dashboard with the URL still showing the old route.
3. **Calibration is a read-only window onto a backend that supports writes.** `/api/calibration/labels` and `/api/jobs/calibration` exist; the UI only links to the CLI.
4. **The whole `<main>` is `aria-live="polite"` and gets `innerHTML` swapped on every navigation.** This is a noisy assistive-tech experience and the main perf footgun.
5. **Several "absolute-ban" motifs** (hero metric strip on Benchmarks, glass blur on the slideout overlay, gradient logo, dense card grids) are present. They are not fatal; they're the difference between a 7/10 and a 9/10 design.

**Nielsen heuristic score: 30/40.** Above-average for an internal analytics tool. See full table below.

---

## Walkthrough

<img src="/opt/cursor/artifacts/dashboard_overview.png" alt="Collection Swarm dashboard overview, dark theme" />
Dashboard overview, dark theme. Clean strategy-rankings module, OKLCH compliance/risk semantics, prominent compliance-exclusion callout.

<img src="/opt/cursor/artifacts/runs_list.png" alt="Simulation Runs table" />
Simulation Runs page with 13 columns, sticky header, dedicated `View` button per row.

<img src="/opt/cursor/artifacts/transcript_slideout.png" alt="Transcript slideout panel" />
Transcript slideout: roleplay turns, judgment scoring strip, prev/next chrome. Closes on Escape; focus returns to invoker.

<img src="/opt/cursor/artifacts/dashboard_light_theme.png" alt="Dashboard in light theme" />
Light theme: tokens swap cleanly; compliance-exception band keeps its red tint correctly.

<img src="/opt/cursor/artifacts/dashboard_mobile_menu_open.png" alt="Mobile sidebar open at 390px" />
Mobile sidebar at 390px: off-canvas drawer with overlay scrim works as expected.

<img src="/opt/cursor/artifacts/launch_form.png" alt="Launch Run configuration form" />
Launch Run: profile + strategy selectors with inline help, advanced settings collapsed, single primary CTA.

<img src="/opt/cursor/artifacts/playbook.png" alt="Generated playbook page" />
Generated Playbook: server-rendered Markdown article. Long; no in-page TOC.

<img src="/opt/cursor/artifacts/model_benchmarks.png" alt="Model Benchmarks page with hero" />
Model Benchmarks: notice the "Production evaluation" hero strip with three vertical KPI tiles. This is the impeccable "hero-metric template" pattern.

---

## Design Health Score (Nielsen heuristics)

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 3 | Job panels show queued/running/done well; row click on Runs has no focus/active state, so keyboard users can't tell what's selected. `pollJob` toasts "Connection interrupted" but keeps polling silently. |
| 2 | Match system / real world | 3 | Mostly business-correct (FDCPA, BCB liquidation, Pix). Internal jargon leaks through in IDs (`willbank_fgc_waiting_high_balance`) shown verbatim in tables and badges. |
| 3 | User control and freedom | 2 | No undo/cancel on destructive choices (running a 50-sim matrix); cancel exists for jobs (`/api/jobs/{id}/cancel`) but not surfaced everywhere. Back-button does not restore page. |
| 4 | Consistency and standards | 3 | Cards-everywhere is consistent; benchmark page tabs use a different keyboard model than dashboard tabs. Two overlapping checkbox-list helpers (`checkboxList` vs `benchmarkCheckboxList`) drift. |
| 5 | Error prevention | 2 | No client-side `required` on Launch/Manual/Matrix forms; defaults select all profiles/strategies/models so a stray click submits a 50+ run job. `#matrix-count.warning` mitigates but only after the fact. |
| 6 | Recognition rather than recall | 3 | Sidebar labels + icons are good. Hero "Production" preset on Benchmarks hard-codes IDs (`composer-2`, `gpt-5.5`) that may silently miss models if API list drifts. |
| 7 | Flexibility and efficiency | 3 | Sortable, filterable runs table; CSV export; theme toggle; mobile drawer; per-row View button. Missing: keyboard shortcut to dismiss slideout via row arrow keys, deep-linking by ID, saved filter views. |
| 8 | Aesthetic and minimalist | 3 | OKLCH palette is restrained; typography hierarchy works. Density is high — eight-card dashboard, hero strip on Benchmarks, dual KPI banner on dashboard. |
| 9 | Error recovery | 2 | Invalid `#runs/<bad-id>` silently shows the dashboard while keeping the URL unchanged. Failed API calls surface only as a transient toast. |
| 10 | Help and documentation | 4 | Empty states are unusually good — they teach the CLI command to populate the page (Arena, Evolution, Calibration). Inline form copy is confident and brief. |
| **Total** | | **30/40** | Above average; ceiling is held down by routing, error handling, and the few "ban-list" motifs. |

---

## Anti-pattern verdict ("does this look AI-generated?")

Mostly no — there are real signals of intent (purpose-built compliance band, strategy-rankings tabs, Portuguese microcopy from real Brazilian collection law). But there are AI-slop tells worth naming:

- **Hero-metric strip.** `benchmark-hero` (`app.js` ~1626–1636, `styles.css` ~1520–1576) is the textbook "big number / small caption / supporting stat / accented headline" SaaS pattern. The headline "Find the model mix that can safely drive Collection Swarm." pushes it further into marketing register.
- **Glassmorphism on the slideout overlay.** `styles.css` ~913–917 uses `backdrop-filter: blur(...)` decoratively.
- **Decorative gradient logo.** `index.html` ~26–27 — a violet→indigo `linearGradient`. Small surface but it sets the tone.
- **Card overuse.** Most pages are wall-to-wall `.card`. A handful of surfaces (Strategies, Profiles, Compliance exclusions) would breathe better as plain typographic blocks.
- **Dashboard "Operational Details" disclosure** plus the four-stat pill row at top is the standard SaaS dashboard hero arrangement.

The cross-register absolute bans the codebase **does avoid**: side-stripe colored borders, gradient text, dark glow shadows, identical-card icon grids.

---

## Per-page findings

### Dashboard (`#dashboard`)
- **Works:** four-stat KPI strip, profile-tab strategy rankings (clean tab transition), compliance-exception callout above the fold, average-scores bar with semantic color coding, outcome distribution.
- **Issues:**
  - The KPI strip ("Runs 24 / Completed 24 / Failed 0 / Success 100%") is decorative when there are no failures — consider hiding `Failed` when zero or collapsing into a single-line summary.
  - The compliance-exception card is the only non-card surface; visually loud (red tint) but the "View details" link is the same color as the body text and easy to miss.
  - "Operational Details" disclosure at the bottom is invisible until expanded — what it contains is not previewed in the heading.

### Simulation Runs (`#runs`)
- **Works:** sticky header, sortable columns, debounced filter (200 ms, `app.js` ~818), per-row `View` button with `aria-label`, status/outcome badges with semantic color, transcript slideout with prev/next.
- **Issues:**
  - **Row keyboard parity (P1).** `<tr onclick="...">` (line 797) gives mouse users a giant click target; keyboard users only have the small `View` button. The handler `handleRunRowKey` exists at line 823 but is never wired — almost certainly an incomplete refactor.
  - Cells are truncated to 200 px with no native tooltip on most columns (only `started_at` has a `title`). `Conversation Model: Low Digital Access Guida...` loses information.
  - Empty state inside `<td colspan="13">` (line 790) renders block content inside a table cell — fine functionally, but cell padding fights the empty-state layout.

### Launch Run (`#launch`)
- **Works:** two clean selects with inline descriptions; "Advanced model settings" collapsed by default; single high-affordance primary button; live-progress panel always present.
- **Issues:**
  - No `required` attributes; submit fires unconditionally. With local backends this is harmless; with paid backends a misclick spends money.
  - The right panel says "Ready" before any action — fine, but offers no "what will happen" preview (no token cost estimate, no expected wall-time).
  - "Advanced model settings" hides the choice that most affects cost (Cursor SDK vs local). Defaults are safe; discoverability is not.

### Batch Comparison (`#matrix`)
- **Works:** dense matrix builder; `updateMatrixCount()` (line 1294) calculates total simulations live and adds `.warning` past 50.
- **Issues:**
  - All checkboxes default to **checked**, including all profiles × all strategies × all models × all judges — selecting nothing requires a manual deselect-all per group. This is the inverse of error-prevention defaults.
  - Job history list and the active job panel coexist; relationship is not signposted.
  - <img src="/opt/cursor/artifacts/batch_comparison_form.png" alt="Batch Comparison form" />

### Manual Run (`#manual`)
- **Works:** start session, send turn, finish session; uses local backends fine.
  - <img src="/opt/cursor/artifacts/manual_run_in_progress.png" alt="Manual run in progress" />
- **Issues:**
  - Navigating away while a session is open silently drops `_manualSessionId` with no warning. Returning shows a fresh form, so the in-flight session looks gone (it isn't — backend keeps it).
  - Sending a turn shows no optimistic UI; the input clears only after the round trip.

### Playbook (`#playbook`)
- **Works:** server-rendered Markdown via `markdown.markdown` (`app.py` ~449), copy/export buttons, code-style monospace tags for IDs.
- **Issues:**
  - Long page (16 H2s, 33 H3s observed); no in-page TOC, no anchor links.
  - The Markdown is injected via `innerHTML` into `article.playbook-content` (`app.js` ~1581). If the Markdown extension allows raw HTML, the playbook is an XSS sink driven by config files. Worth confirming the converter strips raw HTML.

### Compliance (`#compliance`)
- **Works:** clear list of profile×strategy combinations excluded by the configured thresholds; tone is appropriately serious.
- **Issues:**
  - "Exclusion cards" are visually dense red-tinted blocks; the threshold values (compliance < 0.8, escalation > 0.3) are present in source but not surfaced as configurable in the UI.

### Arena (`#arena`)
- **Works:** Elo-style leaderboard scaffold, tournament configuration, history-by-entity drilldown.
- **Issues:**
  - Empty state CTA is informative ("Start a tournament to update Elo ratings") but the form to start one is on the same page below — first-time users may not realize the "empty" message resolves itself once they fill the form.
  - Tournament progress panel uses the same `pollJob` pattern as Matrix; identical UX inconsistencies inherited.

### Evolution (`#evolution`)
- **Works:** clean empty state with a CLI hint.
- **Issues:**
  - No in-app way to trigger evolution (`/api/evolution/pool` is GET-only). The whole page is read-only.

### Calibration (`#calibration`)
- **Works:** lists current calibration variants and label results.
- **Issues (P2 functional gap):**
  - Backend exposes `POST /api/calibration/labels` and `POST /api/jobs/calibration` (`app.py` ~552–572). The UI exposes neither. The page directs users to the CLI/API instead. This is the largest backend↔frontend asymmetry in the app.

### Model Benchmarks (`#benchmarks`)
- **Works:** "Production" quick-pick (`selectProductionBenchmarkModels`), per-role benchmark toggles, rich result tables.
- **Issues:**
  - The hero strip (see Anti-patterns) is the most overtly "AI SaaS" surface in the app.
  - "Production" hard-codes model IDs (`composer-2`, `gpt-5.5`, `claude-sonnet-4-6`, …) at `app.js` ~1696–1699; if the backend `/api/config/models` ever drops one of those IDs, the preset silently selects fewer than promised, with no warning.
  - Benchmark tabs (`switchBenchTab`, ~1856) implement a different keyboard model than the dashboard tabs (~491, ~618), with no `aria-controls` or arrow-key navigation. Inconsistent within the same product.

### Profiles / Strategies (`#profiles`, `#strategies`)
- **Works:** complete catalog rendered as typographic blocks; no card chrome (good).
- **Issues:**
  - Read-only. No filter, no anchor links, no copy-to-clipboard for IDs. For a list this long (14 profiles, 13 strategies) a search box would help.

---

## Cross-cutting findings

### Accessibility (WCAG)

| Severity | Where | Finding |
|---|---|---|
| **P1** | `app.js` ~797–814 (rows), ~823 (`handleRunRowKey` defined but unused) | Rows lack `tabindex` and `role="button"`; the only keyboard path to a transcript is the small per-row `View` button. The dead handler implies the intent. **Fix:** wire `tabindex="0"` + `keydown` (Enter/Space) to rows, or remove the row-level `onclick` and rely solely on the `View` button (and document that). |
| **P2** | `index.html` ~103 — `<main aria-live="polite">` swapped via `innerHTML` per nav | Verbose AT announcements on every navigation. **Fix:** scope `aria-live` to genuinely live regions (job panels, toasts), not the whole main. |
| **P2** | `app.js` ~1856 (`switchBenchTab`) | Benchmark tabs are mouse-oriented; no `aria-controls`, no arrow navigation, no `aria-selected`. Dashboard tabs at ~491 implement the better pattern; benchmark tabs should match. |
| **P2** | `styles.css` `--text-tertiary` × small caps | Sidebar nav-labels and KPI captions sit at the WCAG-AA threshold for small text. Worth measuring with a contrast tool against your specific OKLCH values. |
| **P2** | `app.py` ~449 + `app.js` ~1581 | Playbook Markdown rendered via `markdown.markdown` and injected as `innerHTML`. If raw HTML is permitted by the Markdown extension, this is an XSS class issue. **Fix:** disable raw-HTML in the Markdown extension or sanitize server-side. |
| **P3** | `styles.css` ~206–214 | `prefers-reduced-motion` disables transitions globally but does not disable the named `@keyframes` (`btn-spin`, `skeleton-pulse`). Some users still see motion. |
| **P3** | `index.html` | No "skip to main content" link; SPA without it forces keyboard users through the full sidebar on every page. |
| **P3** | `.btn-compact` (`styles.css` ~1330) `min-height: 30px`; `.filter-clear` ~1208 `min-height: 28px` | Below the WCAG 2.5.5 44×44 touch-target guideline. The dense Runs row uses these. |
| **P3** | Score "meters" (`scoreBarHTML`, `app.js` ~268) | `role="meter"` without `aria-valuetext`; SR users hear the raw number, not the human-meaningful label ("OK / Watch / Risk"). |

**Inputs are not unlabeled.** A first-pass console scan flagged 51/27/60 "unlabeled" inputs on Batch Comparison, Arena, and Model Benchmarks. After verification, every input is wrapped in `<label class="check-option">…</label>` (`app.js` ~1268, ~1276), which is a fully valid programmatic label. Re-running the labeling check explicitly:

| Page | Total inputs | Labeled by `for` | Labeled by wrap | By `aria` | Truly unlabeled |
|---|---:|---:|---:|---:|---:|
| Batch Comparison | 53 | 2 | 51 | 0 | **0** |
| Arena | 33 | 6 | 27 | 0 | **0** |
| Model Benchmarks | 61 | 1 | 60 | 0 | **0** |

### Information architecture & routing

- **Hash routing is half-implemented.** `navigateTo()` (`app.js` ~17) calls `pushState` but the app never subscribes to `hashchange`. The `popstate` handler restores `e.state`, not the hash, so:
  - Navigating to `http://127.0.0.1:8000/#runs/nonexistent` lands on the **Dashboard** while the URL still shows `#runs/nonexistent`. This is the "invalid route silently shows dashboard" behavior captured in `invalid_run_id.png`.
  - <img src="/opt/cursor/artifacts/invalid_run_id.png" alt="Invalid run ID silently shows dashboard" />
- **Page state is wholesale-discarded on nav.** `renderPage` blasts `mainEl.innerHTML`. Filters, sort columns, manual sessions, all reset on every visit. `_sortColumn` etc. are stored on `window`, but only re-applied if you stay on the page.
- **Sidebar grouping is good.** Three groups (Overview / Analysis / Configuration) with semantic icons. Active state and `aria-current="page"` are correct. The order ("Launch Run" before "Batch Comparison" and "Manual Run") matches the natural progression.

### Visual / typographic system

- **Tokens are real.** OKLCH custom properties for foreground, surfaces, semantic states; dual theme via `[data-theme="light"]`.
- **Token leaks.** `app.js` injects literal OKLCH values for benchmark fit badges (~1913–1944, ~1990) and `.bench-fit-badge.fit-strong` backgrounds in `styles.css` (~2135) are tuned for dark only — not remapped under `[data-theme="light"]`. Risk: light-mode benchmark heatmaps will look washed out or unreadable in some cells.
- **Typography is dense.** Body copy at ~13–14 px on a 16 px root; `--text-xs` is 11 px. Readable on a desktop, fatiguing in long sessions. Inter 350-weight body is intentional; some forms could move to 400 for WCAG-friendliness.
- **Cards everywhere.** With 6+ cards per typical page, the layout reads as "grid of containers" instead of a story. Strategies and Profiles already do better by going typographic.

### State coverage

- **Loading:** initial skeleton on `renderPage` (~437); per-section skeleton on strategy rankings (~634). No skeletons inside the slideout — it briefly shows nothing before the API resolves.
- **Empty:** unusually thoughtful — Arena, Evolution, Calibration all teach the user a concrete next action. This is the single best UX dimension of the app.
- **Error:** `pollJob` (~1362) throws a toast after 3 failures and then **keeps polling silently**. The job panel stays in a perpetual queued/running state. Users can miss the toast and never realize the connection broke.
- **Success/feedback:** form submission → toast → job panel; clear and consistent.

### Forms & controls

- Defaults heavily checked across matrix builders. Combined with no client-side validation, this is the main "user shoots own foot" risk.
- `inputField` (`app.js` ~1256) is `type="number"` without `inputmode` — fine on desktop, suboptimal on mobile.
- The Runs filter panel debounces at 200 ms (`debouncedFilterRuns`, ~818) — good.

### Performance & code quality

- **Single 2,533-line `app.js`**, no bundler, no module split. Every nav re-runs a full `innerHTML` swap and re-fetches its API data. Acceptable today; will hurt as features grow.
- **Inline `onclick="..."`** is everywhere. Moves behavior into markup; CSP-unfriendly if you ever tighten headers.
- **No `console.log` left in shipping code** (verified by grep).
- **`escapeHTML` is used consistently** for user-supplied strings except in the Playbook Markdown path noted above.
- **Google Fonts CDN.** `index.html` ~9–11 — render-blocking external resource; enterprise networks sometimes block this. Consider self-hosting Inter + JetBrains Mono.

### Microcopy

- Mostly confident, brief, and domain-correct (Portuguese terminology lines up with BCB/Will Bank context).
- "Connection interrupted" toast is misleading when polling continues.
- Error strings from FastAPI bubble up raw (`apiPost`, ~174) — `"API error: 404"` is unhelpful for non-developers.
- Benchmark hero copy ("…can safely drive Collection Swarm") shifts tone toward marketing on what is otherwise a neutral ops UI.

### Mobile / responsive

- Sidebar becomes an off-canvas drawer with overlay scrim; focus return is implemented (`app.js` ~91–103). Solid baseline.
- Runs table relies on `overflow-x: auto` plus `td { max-width: 200px }` ellipsis — at 390 px the truncation is heavy and tooltips are missing on most columns.
- Benchmark and Compliance pages have horizontal-scroll inner panels at narrow widths.

---

## Persona red flags

**Alex (analyst, mostly keyboard).** Opens Runs, presses Tab to scan rows — never lands on a row, always lands on the small `View` button. Sorts columns with mouse only (no `aria-sort`). Filters work fine. Tries to share a deep link to a transcript: cannot — there is no per-run URL.

**Jordan (first-time PM, exploring).** Lands on Dashboard, sees four stat pills + a strategy-rankings tab carousel + a red compliance band + an Average-Scores bar + Outcome Distribution + Operational Details disclosure — six top-level affordances above the fold. Picks "Calibration" because the word sounds important; reads "No calibration runs yet" with a CLI command — gives up because there's no in-app way to trigger one.

**Riya (operations lead, mobile commuter).** Opens on phone, drawer works, but the Runs table is unreadable (`...` everywhere, no tooltips). Tries to launch a run from her phone — Launch form works, but advanced model settings are collapsed and she doesn't realize "scripted" is the default.

---

## Priority fixes (impact-ordered)

1. **[P1] Make Runs rows fully keyboard-operable.** Add `tabindex="0"`, wire the existing `handleRunRowKey`, add a focus-visible state. Two-line fix; biggest immediate accessibility win.
2. **[P1] Hash-route hardening.** Subscribe to `hashchange`; on unknown route, render a small "Run not found" view with a link back to `#runs`. Stop silently falling back to the dashboard.
3. **[P2] Build the Calibration UI.** Surface the existing `/api/calibration/labels` and `/api/jobs/calibration` endpoints. Today the page lies about what's possible.
4. **[P2] Sanitize Playbook Markdown render path.** Confirm the Markdown extension blocks raw HTML, or sanitize before injecting.
5. **[P2] Narrow `aria-live` from `<main>` to actual live regions** (job panels, toast container).
6. **[P2] Default checkbox grids to *unchecked* on Batch Comparison and Benchmarks.** Selecting "all of everything" should be a deliberate gesture (preset button), not the default.
7. **[P3] Quiet the Benchmarks hero.** Remove the marketing headline and KPI strip; keep the form. The page already has enough information density.
8. **[P3] Persist navigation state.** Cache page-local state (filters, sort, manual session) per route so back/forward doesn't blow it away.
9. **[P3] Self-host Inter + JetBrains Mono.** Eliminates render-blocking third-party request and survives offline/enterprise networks.
10. **[P3] Add a "skip to main content" link** at the top of `<body>`.

---

## What's working (worth preserving)

- **Empty-state writing.** Arena/Evolution/Calibration empty states teach the next action — keep this voice.
- **Slideout focus management.** Real focus trap, focus return on close, Escape to dismiss. Better than most apps.
- **Theme tokens.** OKLCH-driven dual theme is honest and mostly complete (modulo the benchmark fit-badge leaks).
- **Compliance posture.** Above-the-fold compliance-exception band + Compliance page + automatic exclusion in Playbook is a coherent compliance story, not a marketing bullet.
- **Mobile drawer.** Off-canvas with proper overlay and focus return; rare to get right.

---

## Provocative questions

- **What if Launch Run estimated cost up front?** Most user anxiety on this page is "is this going to charge me?" — a tiny "≈ R$ 0.0017 with current settings" line would defuse that.
- **What if the Dashboard had only one above-the-fold module?** Today it has six. The compliance-exception band is by far the most actionable.
- **Does Model Benchmarks need a hero, or does it need a wizard?** A three-step picker ("which roles? which models? which probes?") would replace both the hero and the dense form.
- **Should Profiles and Strategies be searchable from the global header?** Power users will want `Cmd-K` for `cooperative_hardship`, not a sidebar trip.
- **Should the slideout become a full route (`#runs/<id>`) instead of an overlay?** It would give shareable links and survive page reload — both currently absent.
