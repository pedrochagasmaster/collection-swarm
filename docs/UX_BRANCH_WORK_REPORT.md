# UX Branch Work Report

Branch: `cursor/implement-ux-report-9923`  
Base: `44f6cfb096c05d3c0cd750e2ae96168f5ac35b2c`  
Head reviewed: `e06172cdb0cd23c626c4b4e504f638c48b5c54a2`  
Source report: `docs/UX_REPORT.md`

## Executive summary

This branch implements the practical ship plan from `docs/UX_REPORT.md`: the P0 Playbook XSS blocker, the P1 navigation and trust fixes, the P2 accessibility and error-prevention work, the Calibration UI gap, and most P3 polish items.

The branch does not complete the large CSP refactor, build-time cache busting, or the future product roadmap items that the UX report explicitly placed outside the ship plan. It also handles the Google Fonts risk by removing external font requests and using local/system fallbacks, rather than downloading and self-hosting Inter and JetBrains Mono font files.

## What changed

- Added `bleach` sanitization to Playbook HTML generation and covered unsafe Markdown input with a regression test.
- Hardened SPA routing with page titles, back/forward support, hashchange handling, unknown-route UI, and in-page hash protection for skip links and Playbook TOC anchors.
- Added dashboard quick actions for populated dashboards.
- Made runs table rows keyboard-operable.
- Added Playbook trust framing and generated table of contents.
- Scoped live regions to toasts and job/status panels instead of the entire `<main>`.
- Changed matrix checkbox defaults to avoid accidental large jobs and added select/clear helpers.
- Added a manual-session navigation guard.
- Added job polling escalation after repeated API failures.
- Added Calibration run and label-upload forms.
- Moved benchmark fit colors into theme tokens and validated production benchmark presets.
- Added accessibility and polish fixes: skip link, larger text floor, reduced motion, numeric alignment, touch target improvements, sticky theme toggle, theme-color metadata, and visible sidebar section labels.
- Added automated regression coverage for Playbook XSS, Playbook metadata, and static UI affordances.

## Issue-by-issue status

### P0 blockers

| ID | Finding | Status | How it was addressed |
| --- | --- | --- | --- |
| P0-1 | Playbook Markdown XSS sink | Done | `app.py` now renders Markdown, sanitizes it with `bleach.clean`, limits tags/attributes/protocols, and strips unsafe content. `pyproject.toml` and `requirements.txt` include `bleach`. `tests/test_web.py` verifies `<script>`, event handlers, and `javascript:` links are removed. |

### P1 critical issues

| ID | Finding | Status | How it was addressed |
| --- | --- | --- | --- |
| P1-1 | Hash routing is half-implemented | Done | Added page title mapping, active-nav updates, hashchange handling, popstate fallback, unknown-route rendering, and in-page hash protection so skip links and TOC anchors do not become SPA routes. |
| P1-2 | Runs table rows not keyboard-operable | Done | Runs table rows now render with `tabindex="0"`, `role="row"`, `onkeydown="handleRunRowKey(...)"`, and descriptive `aria-label` values. CSS adds row focus styling. |
| P1-3 | Populated dashboard lacks next action | Done | Added `quickActionsStrip()` for populated dashboards with Launch new run, Compare strategies, and Review compliance actions. |
| P1-4 | Generated Playbook needs trust framing | Done | Added a Synthetic Analysis notice above Playbook content. The backend now returns `simulation_count`, and the banner uses that real count. |

### P2 important issues

| ID | Finding | Status | How it was addressed |
| --- | --- | --- | --- |
| P2-1 | `<main aria-live="polite">` is noisy | Done | Removed `aria-live` from `<main>`. Toasts and job/count panels keep scoped live-region behavior. |
| P2-2 | Calibration page is read-only | Mostly done | Added Run Calibration and Upload Labels forms. `startCalibration()` posts to `/api/jobs/calibration` and polls progress. `submitCalibrationLabels()` posts to `/api/calibration/labels`. Per-model selection was not added because the current backend calibration endpoint does not accept model IDs. |
| P2-3 | Batch/benchmark selections default all checked | Done | `checkboxList()` and `benchmarkCheckboxList()` now default to empty selections unless explicit defaults are passed. Batch Comparison profiles and strategies start unchecked; model dimensions use explicit safe defaults. Select all and Clear all helpers are shown. |
| P2-4 | Manual Run silently drops session on navigation | Done | Added `beforeNavigate()` confirmation when leaving an active manual session. This implements the report's simpler option A. |
| P2-5 | `pollJob` silently retries after three failures | Done | Added shared `handlePollFailure()` escalation. After ten failures, polling stops, the panel shows Connection Lost, status updates when available, and a persistent toast appears. Benchmark polling uses the same helper. |
| P2-6 | Benchmark token leaks in light mode | Done | Added theme-specific benchmark fit tokens and replaced inline benchmark heatmap/fit colors with CSS variables. |
| P2-7 | Tertiary text contrast in light mode | Done | Changed light-mode `--text-tertiary` from `oklch(60% ...)` to `oklch(50% ...)`. |

### P3 polish and hardening

| ID | Finding | Status | How it was addressed |
| --- | --- | --- | --- |
| P3-1 | No skip-to-content link | Done | Added a visible-on-focus skip link and `tabindex="-1"` on `<main>`. |
| P3-2 | Score meters missing `aria-valuetext` | Done | `scoreBarHTML()` now emits human-readable `aria-valuetext`. |
| P3-3 | Reduced motion does not disable keyframes | Done | Reduced-motion media query now includes `animation: none !important`. |
| P3-4 | Touch targets below target size | Done | `.btn-compact` and `.filter-clear` now use taller hit areas and `min-width: 44px`. |
| P3-5 | `--text-xs` below 12 px | Done | Bumped `--text-xs` to `0.75rem`. |
| P3-6 | Numeric columns lack tabular numbers | Done | Added tabular numeric styling for table numeric columns. |
| P3-7 | Google Fonts external dependency | Partially done | Removed Google Fonts requests from `index.html` and left local/system font fallbacks. The exact self-hosted font-file implementation was not added. |
| P3-8 | Sidebar section labels hidden from screen readers | Done | Removed `aria-hidden="true"` from nav section labels. |
| P3-9 | Inline handlers block strict CSP | Deferred | Not implemented. The report itself calls this high effort and says to defer unless CSP headers are required. |
| P3-10 | Title, theme-color, cache busting | Partial | Dynamic `document.title` and theme-color meta tags are implemented. Build-time hash/ETag cache busting is not implemented; the manual `?v=` string remains. |
| P3-11 | Playbook lacks in-page TOC | Done | `generatePlaybookTOC()` builds anchor links from `h2`/`h3` elements when enough headings exist. |
| P3-12 | Theme toggle discoverability | Done | `.sidebar-footer` is sticky at the bottom of the sidebar. |
| P3-13 | Hardcoded production benchmark model IDs | Done | Production preset now validates wanted IDs against available inputs and shows a toast for missing models. |

## Deferred or incomplete work

1. **Strict CSP support**: Inline `onclick` and other inline handlers remain. Supporting strict `script-src 'self'` requires migrating templates to event delegation and should be treated as a dedicated refactor.
2. **Build-time cache busting**: `index.html` still references `app.js` with a static query string. A build step, manifest, or ETag strategy is still needed.
3. **Self-hosted font binaries**: The external Google Fonts dependency was removed, but the branch did not add `/static/fonts/` assets and `@font-face` rules.
4. **Calibration model selection**: The UI can run calibration and upload labels, but it does not expose model checkboxes because the backend request schema currently has no model field.
5. **Future product ideas**: State persistence, transcript deep linking, global search, module splitting, cost estimation, run pagination, and export expansion were not implemented because the UX report listed them as future considerations, not ship-plan work.

## Testing and verification

Automated verification run on this branch:

- `python3 -m pytest tests/test_web.py -k 'playbook_html_strips_unsafe_markup or static_assets_include_ux_report_fixes' -v`
- `python3 -m pytest tests/test_web.py -v`
- `python3 -m pytest tests/test_web.py -k 'playbook_html or static_assets_include_ux_report_fixes' -v`
- `python3 -m pytest -q`

Final result: `113 passed`.

Manual browser verification covered:

- Direct hash navigation to Compliance.
- Dashboard quick actions with seeded data.
- Playbook trust banner, table of contents, and real simulation count.
- Batch Comparison unchecked defaults and select/clear helpers.
- Calibration Run Calibration and Upload Labels forms.
- Simulation Runs table rendering and transcript access surface.

Video capture could not be produced because the screen recorder could not access display `:1` due to X authorization. Screenshots were saved as artifacts instead.

## Recommended next steps

### Before public deployment

1. Decide whether strict CSP is a deployment requirement. If yes, schedule an event-delegation refactor before enabling CSP headers.
2. Replace the static asset query string with a real cache-busting strategy.
3. Add a small browser-level test suite for client-side routing, skip link behavior, Playbook TOC anchors, and polling escalation. The current automated coverage is strong for backend/static regressions but not true browser interaction.
4. Add accessibility verification with a screen reader or browser accessibility tooling for live-region behavior, row keyboard access, and focus order.

### Next product iteration

1. Persist page-local state in `sessionStorage`, starting with Manual Run, filters, and selected matrix options.
2. Add transcript deep links such as `#runs/<id>` so saved runs are shareable and reload-safe.
3. Add global search for profiles, strategies, runs, and benchmark reports.
4. Split `app.js` into page modules once a frontend build step exists.
5. Add run pagination and richer export workflows for larger datasets.
6. Extend calibration APIs if model-specific calibration is desired, then expose model selectors in the Calibration UI.

## Bottom line

The branch addresses the UX report's practical ship-blocking and first-pass launch-readiness work. The remaining items are either explicitly deferred by the report, require new build/security architecture, or need backend contract changes before the UI can expose them cleanly.
