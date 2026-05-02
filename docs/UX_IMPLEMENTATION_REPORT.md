# UX Improvements Implementation Report

**Branch:** `cursor/ux-report-improvements-596f`  
**Date:** 2026-05-02  
**Source:** `docs/UX_REPORT.md` (consolidated from three independent UX audits)  
**Definitive score before work:** 28/40 (Nielsen heuristics)

---

## Scope

The UX report identified 24 findings across four severity tiers (P0 through P3) organized into five ship phases. This branch implements Phases 0 through 4, addressing 22 of the 24 findings. Two P3 items were intentionally deferred per the report's own guidance.

### Files changed

| File | Lines added | Lines removed |
|------|------------|---------------|
| `pyproject.toml` | 1 | 0 |
| `src/collection_swarm/web/app.py` | 9 | 0 |
| `src/collection_swarm/web/static/app.js` | ~170 | ~30 |
| `src/collection_swarm/web/static/index.html` | 8 | 5 |
| `src/collection_swarm/web/static/styles.css` | ~95 | ~14 |
| `tests/test_web.py` | 7 | 0 |

---

## How Each Finding Was Addressed

### Phase 0 — Security

#### P0-1: Playbook Markdown XSS Sink (Blocker)

**Problem:** The Python `markdown` library does not strip raw HTML. Playbook content rendered via `innerHTML` could execute injected `<script>` tags or event handler attributes originating from config files or LLM outputs.

**Fix:** Added `bleach>=6.0` to `pyproject.toml`. In `app.py`, the `get_playbook()` endpoint now passes the Markdown HTML output through `bleach.clean()` with an explicit allowlist of safe tags (`p`, `h1`-`h6`, `table`, `ul`, `ol`, `li`, `code`, `pre`, `blockquote`, `strong`, `em`, `a`, `br`, `hr`, `span`) and safe attributes (`href`, `title` on anchors, `align` on table cells). Any tag or attribute not in the allowlist is escaped.

**Verification:** Added `test_playbook_html_strips_script_tags` to `tests/test_web.py` confirming no `<script>` or `onerror=` survives in the HTML output. All 39 tests pass.

---

### Phase 1 — Core Navigation & Keyboard

#### P1-1: Hash Routing is Half-Implemented (Critical)

**Problem:** No `hashchange` listener, so editing the URL hash mid-session did nothing. `popstate` read `e.state` which is `null` for the initial history entry, causing Back to always land on Dashboard. Invalid routes silently rendered Dashboard. `document.title` never changed.

**Fix:** Four changes in `app.js`:

1. Added a `hashchange` listener that calls `navigateTo()` when the hash changes.
2. Fixed the `popstate` handler to fall back to `location.hash` when `e.state` is null or missing.
3. Added a `PAGE_TITLES` map and set `document.title` to `"PageName — Collection Swarm"` on every navigation.
4. Added an unknown-route handler in `renderPage()` that shows a "Page Not Found" state with a link back to Dashboard.

#### P1-2: Runs Table Rows Not Keyboard-Operable (Critical)

**Problem:** `handleRunRowKey()` existed in the code but was never wired to any DOM element. Table rows had `onclick` but no `tabindex`, `role`, or `onkeydown`. Keyboard users could not navigate or activate rows.

**Fix:** Updated the `<tr>` template in `filterRuns()` to include `tabindex="0"`, `role="row"`, `onkeydown="handleRunRowKey(event, ...)"`, and a descriptive `aria-label`. Added a `.data-table tbody tr:focus-visible` CSS rule with accent outline and hover background.

#### P1-3: First-Run Dashboard Lacks Clear Next Action for Populated State (Critical)

**Problem:** The zero-data first-run panel existed, but once data was present, users saw 6+ modules with no dominant call-to-action.

**Fix:** Added a quick-actions strip with three buttons ("Launch new run", "Compare strategies", "Review compliance") that renders when `total_runs > 0`. Placed above the strategy rankings section. Styled with flexbox and gap spacing.

#### P1-4: Generated Playbook Needs Trust Framing (Critical)

**Problem:** Playbook content could be mistaken for legal or operational advice in a debt-collection domain.

**Fix:** Added a trust banner at the top of the Playbook page with the text: "This playbook is generated from N simulated conversations using scripted backends. It is not legal advice, operational policy, or a substitute for human compliance review." The banner uses `--info-bg` background with a visible border, distinct from error styling.

---

### Phase 2 — Accessibility & Error Prevention

#### P2-1: `<main>` as `aria-live="polite"` Is Noisy (Important)

**Problem:** Every `innerHTML` swap triggered a screen reader re-read of the entire page.

**Fix:** Removed `aria-live="polite"` from the `<main>` element in `index.html`. Added `aria-live="polite"` dynamically to job progress panel containers in the `renderJobPanel()` function, which are the elements that genuinely update live.

#### P2-2: Calibration Page Is Read-Only Despite Backend Write Endpoints (Important)

**Problem:** Backend exposed `POST /api/calibration/labels` and `POST /api/jobs/calibration`, but the frontend was read-only with a "use the CLI" hint.

**Fix:** Added a "Run Calibration" card to the Calibration page with a JSON label upload textarea and a "Start calibration" button. Wired `startCalibration()` to `POST /api/jobs/calibration` with `pollJob` integration for progress tracking, matching the pattern used by Launch Run and Batch Comparison. Also added a "Calibration Jobs" panel showing job history.

#### P2-3: Batch Comparison & Benchmarks Default All Checkboxes to Checked (Important)

**Problem:** `checkboxList()` defaulted to checking all options when no explicit selection was provided. Batch Comparison rendered with all profiles, strategies, models, and judges selected, risking accidental submission of massive jobs.

**Fix:** Changed `checkboxList()` so that `selected = null` means "none checked" instead of "all checked". Updated Batch Comparison call sites to pass `[]` for profiles and strategies (empty default) and `[defaultModel]` for conversation/judge models (only the default selected). Added "Select all" / "Clear all" buttons to the Profiles and Strategies sections. Arena checkboxes were explicitly updated to pass all IDs, preserving their previous all-selected behavior since tournaments require entities.

#### P2-4: Manual Run Silently Drops Session on Navigation (Important)

**Problem:** Navigating away from Manual Run during an active session discarded the session without warning.

**Fix:** Added a guard at the top of `navigateTo()`: if `currentPage === 'manual'` and `_manualSessionId` is set, a `confirm()` dialog warns the user before allowing navigation.

#### P2-5: `pollJob` Silently Retries After 3 Failures (Important)

**Problem:** After 3 API failures, `pollJob` showed one toast and continued polling indefinitely with no further notification.

**Fix:** Added an escalation threshold: after 10 consecutive failures, polling stops, the job panel shows a persistent "Connection Lost" state with a Reload button, and an error toast persists for 10 seconds.

#### P2-6: Benchmark Token Leaks for Light Mode (Important)

**Problem:** Benchmark fit-badge colors and heatmap scores were hardcoded as inline OKLCH values in JavaScript. These values were tuned for dark mode only, causing washed-out or unreadable colors in light mode.

**Fix:** Added `--fit-strong`, `--fit-moderate`, `--fit-weak` and their `-bg` variants as CSS custom properties in both the `[data-theme="dark"]` and `[data-theme="light"]` blocks. Updated all `.bench-fit-badge` CSS rules to use these variables. Replaced all remaining inline OKLCH values in the JavaScript benchmark visualization code (`heatColor`, `textColor`, `fitColors`, `roleColors`, legend spans) with CSS variable references.

#### P2-7: Tertiary Text Contrast in Light Mode (Important)

**Problem:** `--text-tertiary` in light mode was `oklch(60% 0.008 275)`, producing a borderline WCAG AA contrast ratio against the background.

**Fix:** Changed to `oklch(50% 0.008 275)`, increasing the lightness delta and bringing the contrast ratio comfortably above the AA threshold.

---

### Phase 3 — Calibration UI

Covered under P2-2 above. The calibration form, label upload, job launch, and progress tracking are all implemented.

---

### Phase 4 — Polish & Hardening

#### P3-1: No Skip-to-Content Link

Added a skip link as the first child of `<body>` in `index.html`. The link targets `#main-content`, is visually hidden by default (positioned off-screen), and slides into view on focus. Styled with accent background and inverse text.

#### P3-2: Score Meters Missing `aria-valuetext`

Updated `scoreBarHTML()` to include `aria-valuetext="${pctVal}% — ${meaning}"` on the meter element, giving screen readers context like "81% — Good" instead of a raw number.

#### P3-3: `prefers-reduced-motion` Doesn't Disable `@keyframes`

Changed the reduced-motion media query from `animation-duration: 0.01ms` to `animation: none !important`, which fully cancels all named keyframe animations instead of playing their first frame.

#### P3-4: Touch Targets Below WCAG 2.5.5

Increased `min-height` of `.btn-compact` from 30px to 36px and `.filter-clear` from 28px to 36px. This is a compromise between the full 44px WCAG recommendation and the existing table density.

#### P3-5: `--text-xs` Below 12px Floor

Changed `--text-xs` from `0.6875rem` (11px) to `0.75rem` (12px) in the root token block.

#### P3-6: No `tabular-nums` on Numeric Columns

Added `font-variant-numeric: tabular-nums` to `.data-table td .score-good`, `.score-mid`, and `.score-bad` elements, preventing horizontal misalignment between rows.

#### P3-8: Sidebar Section Labels Hidden from Screen Readers

Removed `aria-hidden="true"` from all three `.nav-label` divs ("Overview", "Analysis", "Configuration") in `index.html`, allowing screen readers to announce group headers.

#### P3-10: `document.title` / `<meta theme-color>`

Added two `<meta name="theme-color">` tags to `index.html` with `media` attributes for dark (`#0f0f17`) and light (`#f5f5f7`) color schemes. The `document.title` fix is covered under P1-1.

#### P3-11: Playbook Lacks In-Page TOC

Added `generatePlaybookTOC()` which parses the rendered Playbook HTML for `h2` and `h3` elements and builds a clickable table of contents. The TOC renders above the article content when the document has 4+ headings. Each heading gets an `id` for anchor navigation. Added CSS for `.playbook-toc`, `.toc-link`, and `.toc-indent`.

#### P3-12: Theme Toggle Discoverability

Added `position: sticky; bottom: 0; background: var(--bg-surface)` to `.sidebar-footer`, ensuring the theme toggle remains visible regardless of sidebar scroll position.

#### P3-13: Hardcoded Model IDs in Production Preset

Updated `selectProductionBenchmarkModels()` to validate each wanted model ID against the set of actually available checkbox inputs. Missing models are reported via a warning toast, and only available models are checked.

---

## What Was Left Undone

### P3-7: Self-Host Google Fonts (Deferred)

**Reason:** Medium implementation effort. Requires downloading Inter and JetBrains Mono font files, adding them to `/static/fonts/`, writing `@font-face` declarations with `font-display: swap`, and removing the Google Fonts CDN links. The report classifies this as a P3 polish item, not a functional or accessibility blocker.

**Risk if unaddressed:** Enterprise networks that block `fonts.googleapis.com` will see fallback system fonts. Performance impact is minor due to existing `rel="preload"` on the font stylesheet.

### P3-9: Inline `onclick` Handlers Incompatible with Strict CSP (Deferred)

**Reason:** High implementation effort. The entire application uses inline `onclick="..."` handlers in HTML templates. Migrating to `addEventListener` delegation would require refactoring every interactive element across all 14 pages. The report explicitly recommends deferring this: "defer unless CSP headers are required for deployment."

**Risk if unaddressed:** A strict `Content-Security-Policy` header with `script-src 'self'` would break the entire application. Not a concern unless the deployment environment mandates CSP.

---

## Future Steps

These items come from the report's Phase 5 (future considerations), the deferred P3 items, and observations during implementation.

### Near-term (next sprint)

1. **Self-host fonts (P3-7).** Download Inter and JetBrains Mono, serve from `/static/fonts/`, and remove the Google Fonts CDN dependency. Straightforward file-copy task.

2. **State persistence across navigation.** Cache page-local state (filters, sort column/direction, active manual sessions) in `sessionStorage` per route, so Back/Forward doesn't reset the page. The routing improvements in P1-1 create a foundation for this.

3. **Transcript deep linking.** Extend the routing system to support `#runs/<id>` URLs that open the slideout directly. Currently transcripts are only accessible via click/keyboard from the Runs table.

### Medium-term (product maturity)

4. **CSP hardening (P3-9).** Migrate from inline `onclick` to a delegated event model. This is a prerequisite for deploying behind a strict Content-Security-Policy. Consider introducing a minimal build step at the same time.

5. **Module splitting.** `app.js` is now ~2,700 lines. Splitting into per-page modules with a bundler (esbuild, Vite) would improve maintainability and enable code splitting for faster initial loads.

6. **`Cmd-K` global search.** A command palette that searches Profiles, Strategies, and Runs from any page. The data is already available via existing API endpoints.

7. **Cost estimation on Launch Run.** Show estimated API cost based on selected model and backend before the user commits to a simulation. The backend already tracks `estimated_cost_usd` per run.

8. **Run pagination.** The Runs table currently loads all runs client-side. Beyond ~100 rows, add server-side pagination with cursor-based API support.

### Long-term (product direction)

9. **Export functionality.** CSV export exists for Runs but not for Playbook, Compliance, or Arena data. Add export actions across all analysis pages.

10. **Decision support layer.** The UX report's central thesis is that the dashboard summarizes activity well but doesn't strongly answer "which strategy should we use." Future work should surface ranked recommendations more prominently, with confidence intervals based on run count, and direct evidence links from recommendations to supporting transcripts.

11. **Mobile-first pass.** The responsive CSS is functional but was not browser-tested below 768px during this implementation. A dedicated mobile pass at 375px, 390px, and 768px breakpoints would catch density and touch-target issues in tables, forms, and the matrix setup page.

---

## Test Results

| Test | Result |
|------|--------|
| `python3 -m pytest tests/test_web.py -x -v` | 39/39 passed |
| XSS sanitization (automated) | No `<script>` or `onerror=` in playbook HTML |
| Hash navigation (manual) | `#compliance`, `#nonexistent`, Back/Forward all work |
| Keyboard rows (manual) | Tab focuses rows, Enter opens transcript |
| Document title (manual) | Title updates on every page navigation |
| Trust banner (manual) | Renders above playbook content with disclaimer |
| Quick actions (manual) | Strip appears on populated dashboard |
| Checkbox defaults (manual) | Batch Comparison profiles/strategies unchecked |
| Calibration form (manual) | Renders with label input, Start button works |
| Page Not Found (manual) | Invalid hash shows error state with Dashboard link |
| Light mode (manual) | All pages render correctly, badge contrast improved |
