# UX Implementation Report

**Branch:** `cursor/ux-report-improvements-746a`  
**Base:** `main`  
**Date:** 2026-05-02  
**Source:** `docs/UX_REPORT.md` (consolidated from three independent agent reviews)

---

## Overview

This branch addresses every actionable finding from the definitive UX report across Phases 0 through 4. Two commits land 24 fixes spanning security, navigation, keyboard accessibility, error prevention, and visual polish. The only item from the ship plan left unimplemented is P3-9 (CSP inline handler migration), which the report itself deferred to Phase 5 as a future consideration.

### Scope

| Metric | Value |
|--------|-------|
| Files changed | 7 source files + 14 font files |
| Lines added | ~728 |
| Lines removed | ~40 |
| New dependency | `bleach>=6.0` |
| Tests | 112 passing (1 new) |

---

## Phase 0 — Security Gate

### P0-1: Playbook Markdown XSS Sink

**Problem:** The Python `markdown` library does not strip raw HTML by default. Strategy descriptions or config-authored Markdown containing `<script>` or `<img onerror>` tags would execute in the browser when rendered via `innerHTML` in the Playbook page.

**Fix:** Added `bleach` as a dependency and wrapped the Markdown HTML output with `bleach.clean()` using an explicit allowlist of safe tags (`p`, `h1`-`h6`, `table`, `code`, `pre`, `a`, `strong`, `em`, etc.) and attributes (`href`, `title`, `align`). The sanitization runs server-side in `app.py` before the HTML reaches the client.

**Files changed:** `pyproject.toml`, `src/collection_swarm/web/app.py`

**Verification:** New test `test_playbook_xss_sanitized` confirms that `<script>` and `onerror` do not appear in the playbook HTML response.

---

## Phase 1 — Core Navigation & Keyboard

### P1-1: Hash Routing is Half-Implemented

**Problem:** The app read `location.hash` once on initial load but had no `hashchange` listener. Manually editing the hash mid-session did nothing. The `popstate` handler read `e.state`, which is `null` for the initial history entry, causing the first Back press to always show Dashboard. `document.title` never changed. Invalid routes silently rendered Dashboard with the wrong URL retained.

**Fix (four parts):**

1. Added a `hashchange` listener that calls `navigateTo` when the hash changes externally.
2. Fixed `popstate` to fall back to `location.hash` when `e.state` is null.
3. Added a `PAGE_TITLES` map and set `document.title` on every navigation to `"Page Name — Collection Swarm"`.
4. The existing `renderPage` default case already renders an empty state for unknown routes; this was verified as working correctly.

**Files changed:** `src/collection_swarm/web/static/app.js`

### P1-2: Runs Table Rows Not Keyboard-Operable

**Problem:** `handleRunRowKey` was defined but never wired to any `<tr>` element. Table rows had `onclick` but no `tabindex`, `role`, or `onkeydown`. Keyboard users could only reach transcripts via the small "View" button.

**Fix:** Added `tabindex="0"`, `role="row"`, `onkeydown="handleRunRowKey(event, ...)"`, and a descriptive `aria-label` to each `<tr>` in the runs table. Added a `tr:focus-visible` CSS rule with an accent-colored outline and hover background.

**Files changed:** `src/collection_swarm/web/static/app.js`, `src/collection_swarm/web/static/styles.css`

### P1-3: Dashboard Lacks Clear Next Action (Populated State)

**Problem:** The zero-data first-run panel exists, but with seeded or production data the dashboard presents multiple modules with no dominant call-to-action.

**Fix:** Added a `quickActionsStrip()` function that renders three buttons ("Launch new run", "Compare strategies", "Review compliance") when `total_runs > 0`. The strip appears above the strategy rankings section.

**Files changed:** `src/collection_swarm/web/static/app.js`, `src/collection_swarm/web/static/styles.css`

### P1-4: Generated Playbook Needs Trust Framing

**Problem:** Playbook content includes strategy recommendations and compliance guidance for a debt-collection domain. Without a disclaimer, this could be mistaken for operational policy or legal advice.

**Fix:** Added a `.trust-banner` element at the top of the Playbook page with an info icon and the text: *"This playbook is generated from simulated conversations using scripted backends. It is not legal advice, operational policy, or a substitute for human compliance review."*

**Files changed:** `src/collection_swarm/web/static/app.js`, `src/collection_swarm/web/static/styles.css`

---

## Phase 2 — Accessibility & Error Prevention

### P2-1: `<main>` as `aria-live="polite"` Is Noisy

**Problem:** Every `innerHTML` swap on navigation triggered a screen reader re-read of the entire page content.

**Fix:** Removed `aria-live="polite"` from the `<main>` element in `index.html`. Added `aria-live="polite"` programmatically to individual job progress panels in `renderJobPanel()`, which are the genuinely live regions.

**Files changed:** `src/collection_swarm/web/static/index.html`, `src/collection_swarm/web/static/app.js`

### P2-2: Calibration Page is Read-Only Despite Backend Write Endpoints

**Problem:** The backend exposes `POST /api/calibration/labels` and `POST /api/jobs/calibration`, but the frontend Calibration page only displayed existing data and told users to use the CLI.

**Fix:** Added a "Run Calibration" form section to the Calibration page with an optimize checkbox and a submit button. Wired a `startCalibration()` function to `POST /api/jobs/calibration` with `pollJob` integration for progress tracking. Added a "Calibration Jobs" panel that lists prior calibration jobs.

**Files changed:** `src/collection_swarm/web/static/app.js`

### P2-3: Batch Comparison & Benchmarks Default All Checkboxes to Checked

**Problem:** `checkboxList()` defaulted `selected` to `null`, which was treated as "all checked". Opening Batch Comparison with all profiles, strategies, models, and judges selected meant a careless click could submit a massive job.

**Fix:** Changed the default parameter of both `checkboxList()` and `benchmarkCheckboxList()` from `null` to `[]` (empty array). Updated the conditional logic so items are only checked when explicitly included in the `selected` array. Updated call sites in `renderMatrix()` to pass `[]` for profiles and strategies, while keeping sensible defaults for model selections.

**Files changed:** `src/collection_swarm/web/static/app.js`

### P2-4: Manual Run Silently Drops Session on Navigation

**Problem:** Navigating away from Manual Run during an active session cleared the frontend session state with no warning.

**Fix:** Added a guard at the top of `navigateTo()` that checks if the current page is `manual` and `_manualSessionId` is set. If so, a `confirm()` dialog asks the user before proceeding.

**Files changed:** `src/collection_swarm/web/static/app.js`

### P2-5: `pollJob` Silently Retries After 3 Failures

**Problem:** After 3 consecutive API failures, `pollJob` showed a single toast but continued polling indefinitely with no further notification.

**Fix:** Added an escalation threshold: after 10 consecutive failures, polling stops, the job panel shows a persistent "Connection Lost" empty state, and an error toast with a 10-second duration is displayed.

**Files changed:** `src/collection_swarm/web/static/app.js`

### P2-6: Benchmark Token Leaks (Light Mode)

**Problem:** Benchmark fit-badge colors were hardcoded as inline OKLCH values in JavaScript and some CSS rules were dark-theme only. Light-mode benchmarks had washed-out or unreadable badge colors.

**Fix:** Added CSS custom properties `--fit-strong`, `--fit-moderate`, `--fit-strong-bg`, `--fit-moderate-bg`, `--bench-text-on-light`, and `--bench-text-on-dark` to both the dark and light theme blocks with appropriate values. Replaced all inline OKLCH references in `app.js` (heatmap, bar chart, fit distribution, legend) with `var()` references. Updated `.bench-fit-badge.fit-strong` and `.fit-unsafe` CSS rules to use the theme tokens.

**Files changed:** `src/collection_swarm/web/static/styles.css`, `src/collection_swarm/web/static/app.js`

### P2-7: Tertiary Text Contrast in Light Mode

**Problem:** `--text-tertiary` in light mode was `oklch(60% 0.008 275)`, producing a borderline WCAG AA contrast ratio against the light background.

**Fix:** Changed to `oklch(50% 0.008 275)`, increasing the lightness delta and bringing the contrast ratio comfortably above the AA threshold.

**Files changed:** `src/collection_swarm/web/static/styles.css`

---

## Phase 3 — Polish & Hardening

### P3-1: No Skip-to-Content Link

**Fix:** Added an `<a href="#main-content" class="skip-link">Skip to main content</a>` as the first child of `<body>`. The link is positioned offscreen by default and slides into view on focus via a CSS transition.

**Files changed:** `src/collection_swarm/web/static/index.html`, `src/collection_swarm/web/static/styles.css`

### P3-2: Score Meters Missing `aria-valuetext`

**Fix:** Added `aria-valuetext="${pct}% — ${meaning}"` to the `role="meter"` element in `scoreBarHTML()`, where `meaning` is "Good", "Watch", or "Risk" depending on the score.

**Files changed:** `src/collection_swarm/web/static/app.js`

### P3-3: `prefers-reduced-motion` Doesn't Disable `@keyframes`

**Fix:** Changed `animation-duration: 0.01ms !important; animation-iteration-count: 1 !important;` to `animation: none !important;`, which fully suppresses all keyframe animations.

**Files changed:** `src/collection_swarm/web/static/styles.css`

### P3-4: Touch Targets Below WCAG 2.5.5

**Fix:** Increased `.btn-compact` `min-height` from 30px to 36px. Increased `.filter-clear` `min-height` from 28px to 36px. Both are compromise values that maintain table density while significantly improving touch target reliability.

**Files changed:** `src/collection_swarm/web/static/styles.css`

### P3-5: `--text-xs` Below 12px Floor

**Fix:** Changed `--text-xs` from `0.6875rem` (11px at 16px root) to `0.75rem` (12px).

**Files changed:** `src/collection_swarm/web/static/styles.css`

### P3-6: No `tabular-nums` on Numeric Columns

**Fix:** Added `.data-table td:nth-child(n+9) { font-variant-numeric: tabular-nums; }` to align percentage digits in the payment and compliance columns.

**Files changed:** `src/collection_swarm/web/static/styles.css`

### P3-7: Google Fonts as Render-Blocking External Resource

**Fix:** Downloaded all Inter (7 subsets, weights 350-700) and JetBrains Mono (6 subsets, weights 400-500) woff2 files from Google Fonts. Created a local `fonts.css` with `@font-face` declarations referencing `/static/fonts/`. Removed the `<link rel="preconnect">`, `<link rel="preload">`, and `<link rel="stylesheet">` tags for `fonts.googleapis.com` from `index.html`. The app now loads fonts locally with `font-display: swap`, eliminating the FOIT/FOUT risk and external dependency.

**Files changed:** `src/collection_swarm/web/static/index.html`, `src/collection_swarm/web/static/fonts/` (14 new files)

### P3-8: Sidebar Section Labels Hidden from Screen Readers

**Fix:** Removed `aria-hidden="true"` from all three `.nav-label` divs ("Overview", "Analysis", "Configuration"). These section headers provide useful navigation context for screen reader users.

**Files changed:** `src/collection_swarm/web/static/index.html`

### P3-10: `document.title` / `<meta theme-color>` / Cache Busting

**Fix:** `document.title` is covered by P1-1. Added two `<meta name="theme-color">` tags with `media` queries for dark (`#0f0f17`) and light (`#f5f5f7`) color schemes. Cache busting was not changed as it requires build infrastructure decisions outside the scope of UX fixes.

**Files changed:** `src/collection_swarm/web/static/index.html`

### P3-11: Playbook Lacks In-Page TOC

**Fix:** Added a `generatePlaybookTOC()` function that runs after the Playbook content is rendered. It queries all `h2` and `h3` elements, assigns stable IDs, and inserts a navigable table of contents with smooth-scroll links. The TOC only appears when the content has 4 or more headings.

**Files changed:** `src/collection_swarm/web/static/app.js`, `src/collection_swarm/web/static/styles.css`

### P3-12: Theme Toggle Discoverability

**Fix:** Added `position: sticky; bottom: 0; background: var(--bg-surface);` to `.sidebar-footer`, keeping the theme toggle visible regardless of sidebar scroll position.

**Files changed:** `src/collection_swarm/web/static/styles.css`

### P3-13: Hardcoded Model IDs in Production Preset

**Fix:** Modified `selectProductionBenchmarkModels()` to validate each wanted model ID against the set of currently available checkbox inputs. Any IDs not found in the available list trigger a warning toast listing the missing models.

**Files changed:** `src/collection_swarm/web/static/app.js`

---

## What Was Left Undone

### P3-9: Inline `onclick` Handlers Incompatible with Strict CSP

The entire application uses inline `onclick="..."` in HTML template strings. A strict Content-Security-Policy header (`script-src 'self'`) would break every interactive element. Fixing this requires migrating all event handling to `addEventListener` delegation patterns.

**Why it was deferred:** The UX report explicitly placed this in "Phase 5 — Future Considerations (Not in Ship Plan)" and described it as a "large refactor; defer unless CSP headers are required for deployment." It touches every page renderer and helper function in the 2,500-line `app.js`. The risk of regressions is high and the benefit is only realized when CSP headers are actively enforced.

### P3-10 (partial): Cache Busting

The report noted that the current cache busting strategy is a manual `?v=` query string. Deriving a version from a file hash at build time or using ETags requires build tooling changes that are outside the scope of UX fixes.

---

## Future Steps

These items are drawn from the report's Phase 5 "Future Considerations" section, augmented with observations from implementation.

### Near-term (next development cycle)

1. **CSP hardening (P3-9).** Migrate from inline `onclick` to delegated `addEventListener` patterns. This is the largest remaining technical debt item and a prerequisite for deploying with strict CSP headers. Consider tackling it alongside the module splitting effort below, since both require restructuring `app.js`.

2. **Module splitting.** Break `app.js` (now ~2,700 lines) into per-page modules with a build step (e.g., esbuild or Vite). This would improve developer experience, enable tree-shaking, and make the CSP migration more manageable.

3. **State persistence.** Cache page-local state (filters, sort order, selected tabs, manual session IDs) per route in `sessionStorage`. Currently, navigating away and pressing Back loses all filter and form state. This is the most common "paper cut" for power users.

4. **Cache busting.** Introduce content-hash-based cache busting for `app.js` and `styles.css`, either through a build step or by having the server compute ETags.

### Medium-term (product maturity)

5. **Transcript deep linking.** Make the slideout a full route (`#runs/<id>`) so transcript URLs are shareable and survive page reloads. This would also enable browser bookmarking of specific runs.

6. **`Cmd-K` global search.** Add a keyboard-triggered command palette for searching Profiles, Strategies, Runs, and pages from anywhere in the app.

7. **Run pagination.** Add server-side pagination for the Runs table. The current approach loads all runs into memory, which will degrade beyond ~200 rows.

8. **Cost estimation.** Show estimated API cost and runtime on the Launch Run page based on the selected model, backend, and historical data.

### Long-term (product direction)

9. **Export functionality.** CSV/JSON export for runs, playbook, and compliance data. The Playbook already has Markdown export; extending this to other pages would complete the data portability story.

10. **Compliance audit trail.** Link exclusion cards to supporting transcripts, show configured thresholds inline, add coverage warnings when profile/strategy combinations have insufficient runs, and package judge reasoning as an exportable audit packet.

11. **Decision support.** Reframe the dashboard around strategic decisions rather than operational metrics: lead with "best strategy by profile" and "compliance exceptions requiring review," add confidence indicators based on sample size, and surface risk badges on launch forms.

12. **Mobile hardening.** Run dedicated testing at 375px, 390px, and 768px viewports. Convert dense tables to card layouts on small screens. Verify mobile drawer focus behavior end-to-end.

---

## Test Results

All 112 tests pass on this branch, including 1 new test for XSS sanitization:

```
tests/test_web.py::TestPlaybook::test_playbook_xss_sanitized PASSED
```

Manual testing confirmed: hash navigation, dynamic page titles, keyboard-operable table rows, quick actions strip, trust framing banner, empty checkbox defaults, skip-to-content link, theme toggle discoverability, light-mode contrast, and self-hosted font loading.
