# Consolidated UX Implementation Strategy

**Date:** 2026-05-02
**Author:** Comparative analysis of PRs #26, #27, #28, #29 against `docs/UX_REPORT.md`
**Methodology:** Code-level diff analysis, automated test execution, and live browser verification of each branch

---

## 1. Background

Three independent UX audits (PRs #23, #24, #25) were synthesised into a definitive UX report (`docs/UX_REPORT.md`), which identified 25 findings across four severity tiers (P0–P3) and defined a five-phase ship plan. Four separate implementation PRs were then created from the same `main` baseline, each claiming to address the report's findings:

| PR | Branch | Title | Diff (excl. fonts/docs) |
|----|--------|-------|------------------------|
| #26 | `cursor/ux-report-improvements-596f` | Implement all UX report improvements (P0-P3) | +539 / -40 |
| #27 | `cursor/ux-report-improvements-746a` | Implement all UX report improvements (P0-P3) | +1003 / -40 |
| #28 | `cursor/ux-report-improvements-62ef` | ux: implement P0–P3 fixes from UX_REPORT | +1432 / -71 |
| #29 | `cursor/implement-ux-report-9923` | Implement UX report dashboard improvements | +743 / -62 |

This document compares all four, identifies the strongest implementation for each finding, flags gaps and conflicts, and proposes a final consolidated strategy.

---

## 2. Coverage Matrix

Each UX report finding was evaluated against each PR's actual code changes (not just claims in the implementation report). A finding is marked **Done** only if the code change matches the report's specification and the feature was verified working.

| ID | Finding | PR #26 | PR #27 | PR #28 | PR #29 | Best |
|----|---------|:------:|:------:|:------:|:------:|------|
| **P0-1** | Playbook XSS sanitisation | ✅ | ✅ | ✅ | ✅ | **#28** (most thorough: protocol allow-list, `strip=True`, `class` attrs on `span`/`div`/`code`) |
| **P1-1** | Hash routing + `document.title` + unknown routes | ✅ | ✅ | ✅ | ✅ | **#28** (`KNOWN_PAGES` constant, `replaceState` on bootstrap, guard-aware routing) |
| **P1-2** | Runs table keyboard operability | ✅ | ✅ | ✅ | ✅ | Tie #28/#29 (both wire `handleRunRowKey`, `tabindex`, `role`, `aria-label`) |
| **P1-3** | Quick actions on populated dashboard | ✅ (3 btn) | ✅ (3 btn) | ✅ (4 cards) | ✅ (3 btn) | **#28** (4 action cards with icons + subtitles vs plain buttons) |
| **P1-4** | Playbook trust banner | ✅ | ✅ | ✅ | ✅ | **#28** (banner includes model pair, compliance thresholds, sim count from API `meta`) |
| **P2-1** | Scoped `aria-live` (remove from `<main>`) | ✅ | ✅ | ✅ | ✅ | **#28** (most granular: adds `aria-live` to 4 job panels + Manual Run transcript) |
| **P2-2** | Calibration UI forms | ✅ | ✅ | ✅ | ✅ | **#28** (3-section layout: Judge Alignment, Run Calibration with "Store optimised variant", Upload Labels with "Insert example") |
| **P2-3** | Empty checkbox defaults + Select/Clear all | ✅ | ✅ | ✅ | ✅ | **#28** (per-group Select all / Clear all with `setCheckboxGroup` helper reused by Benchmarks/Arena) |
| **P2-4** | Manual session navigation guard | ✅ | ✅ | ✅ | ✅ | **#28** (routing-level `setNavigationGuard`/`clearNavigationGuard` vs inline `confirm()`) |
| **P2-5** | `pollJob` failure escalation | ✅ | ✅ | ✅ | ✅ | **#28/#29** (both implement 10-failure threshold; #29 adds shared `handlePollFailure` helper) |
| **P2-6** | Benchmark token leaks (CSS vars) | ✅ | ✅ | ✅ | ✅ | **#28** (most complete: `--fit-strong*`, `--fit-unsafe*`, `--bench-debtor`, `--heatmap-text-*` tokens; every inline OKLCH replaced) |
| **P2-7** | Tertiary contrast (light mode) | ✅ | ✅ | ✅ | ✅ | All equivalent (`oklch(50%)` from `oklch(60%)`) |
| **P3-1** | Skip-to-content link | ✅ | ✅ | ✅ | ✅ | **#29** (also adds `tabindex="-1"` to `<main>` for Safari focus handling) |
| **P3-2** | `aria-valuetext` on score meters | ✅ | ✅ | ✅ | ✅ | All equivalent |
| **P3-3** | `prefers-reduced-motion` disables `@keyframes` | ✅ | ✅ | ✅ | ✅ | All equivalent |
| **P3-4** | Touch target sizing (36px+) | ✅ | ✅ | ✅ | ✅ | **#29** (also adds `min-width: 44px`) |
| **P3-5** | `--text-xs` → 0.75rem | ✅ | ✅ | ✅ | ✅ | All equivalent |
| **P3-6** | `tabular-nums` on numeric columns | ✅ | ✅ | ✅ | ✅ | All equivalent |
| **P3-7** | Self-host Google Fonts | ❌ | ✅ (13 files, 236 KB) | ✅ (4 files, 175 KB) | ❌ (removed only) | **#28** (4 variable `.woff2` files, smaller total, proper `@font-face`) |
| **P3-8** | Remove `aria-hidden` from nav labels | ✅ | ✅ | ✅ | ✅ | All equivalent |
| **P3-9** | CSP inline `onclick` migration | ❌ | ❌ | ❌ | ❌ | Deferred in all (per report guidance) |
| **P3-10** | `<meta theme-color>` | ✅ | ✅ | ✅ | ✅ | All equivalent |
| **P3-11** | Playbook in-page TOC | ✅ | ✅ | ✅ | ✅ | **#28** (sticky sidebar layout with `playbook-layout` grid) |
| **P3-12** | Sticky sidebar footer | ✅ | ✅ | ✅ | ✅ | All equivalent |
| **P3-13** | Production preset model validation | ✅ | ✅ | ✅ | ✅ | All equivalent |

### Summary count (done / total 25, excluding P3-9 deferred)

| PR | Findings addressed | Unique strengths |
|----|:-:|------------------|
| #26 | 22/24 | Smallest diff; deferred P3-7 |
| #27 | 23/24 | Adds self-hosted fonts (P3-7); larger font set |
| #28 | **24/24** | Most complete; best implementations per finding; variable fonts (smaller); richest tests |
| #29 | 22/24 | Most test count (113 vs 112); `handlePollFailure` shared helper; skip link `tabindex`; partial P3-7 (removed CDN, no self-hosting) |

---

## 3. Code Quality Comparison

### 3.1 Backend (`app.py`)

| Aspect | PR #26 | PR #27 | PR #28 | PR #29 |
|--------|--------|--------|--------|--------|
| XSS sanitisation | `bleach.clean()` inline | `bleach.clean()` inline | Dedicated `_render_safe_markdown()` helper with `strip=True` + protocol allowlist | `bleach.clean()` inline with protocol allow-list |
| Allowed tags | Standard set | + `dl`/`dt`/`dd` | + `div`, `span` with `class` attrs | Standard set |
| Playbook API response | Unchanged (no `meta`) | Unchanged (no `meta`) | Returns `meta` object (sim count, models, thresholds, timestamp) | Returns flat `simulation_count` field |
| Code organisation | Minimal constants | Better naming (`_BLEACH_ALLOWED_*`) | Best (dedicated function, docstring, structured `meta`) | Good (explicit `PLAYBOOK_ALLOWED_PROTOCOLS`) |

**Winner: PR #28.** The `_render_safe_markdown()` helper is reusable, the `meta` return object is well-structured for the trust banner, and allowing `class` on `span`/`div`/`code` prevents stripping legitimate Markdown extension output.

### 3.2 Frontend (`app.js`)

| Aspect | PR #26 | PR #27 | PR #28 | PR #29 |
|--------|--------|--------|--------|--------|
| Quick actions | 3 plain buttons | 3 plain buttons | 4 icon cards with subtitles | 3 buttons in strip |
| Trust banner | Text-only disclaimer | Text-only disclaimer | Rich banner: sim count, model pair, thresholds | Uses `data.simulation_count` from API |
| Playbook TOC | Simple heading list | Simple heading list | Grid layout with sticky sidebar | Heading-based list |
| Routing guard | Inline `confirm()` in `navigateTo` | Inline `confirm()` in `navigateTo` | `setNavigationGuard`/`clearNavigationGuard` pattern | Inline `beforeNavigate()` helper |
| Poll escalation | Basic threshold + stop | Basic threshold + stop | Reusable pattern across 4 panels | Shared `handlePollFailure()` helper |
| Calibration UI | Basic form + textarea | Basic form + textarea | 3-section layout + "Insert example" + "Store optimised" checkbox | Run + Upload forms |
| Checkbox management | `toggleAllCheckboxes()` | `toggleAllCheckboxes()` | `setCheckboxGroup()` with auto-count-update | `checkboxGroupActions()` helper |

**Winner: PR #28.** More polished UI patterns, reusable abstractions, and richer feature implementations. PR #29's `handlePollFailure` shared helper is a good pattern that should be adopted.

### 3.3 Styles (`styles.css`)

| Aspect | PR #26 | PR #27 | PR #28 | PR #29 |
|--------|--------|--------|--------|--------|
| New CSS additions | +95 lines | +149 lines | +287 lines | +217 lines |
| Benchmark tokens | Partial | Partial | Complete (`--fit-*`, `--fit-*-bg`, `--bench-debtor`, `--heatmap-text-*`) | Complete (`--fit-strong`, `--fit-unsafe*`) |
| Quick action styling | Basic flexbox | Basic flexbox | Card grid with hover transforms + accent icons | Flex strip |
| Trust banner | `--info-bg` block | `--info-bg` block | Themed with icon + border | Styled block |
| Touch targets | `min-height: 36px` | `min-height: 36px` | `min-height: 36px` | `min-height: 36px` + `min-width: 44px` |

**Winner: PR #28** for completeness; PR #29 for the `min-width: 44px` touch target detail.

### 3.4 Test Coverage

| Aspect | PR #26 | PR #27 | PR #28 | PR #29 |
|--------|--------|--------|--------|--------|
| Total tests | 112 | 112 | 112 | 113 |
| New test methods | 1 (XSS) | 1 (XSS) | 3 (XSS + meta + markdown meta) | 3 (XSS + meta + static regression) |
| Test rigour | Basic assertion | Basic assertion | Tests payloads (`<script>`, `onerror`, `javascript:`), verifies safe tags survive | Tests payloads, static asset regression for 20+ UX fixes |
| Static regression test | ❌ | ❌ | ❌ | ✅ (`test_static_assets_include_ux_report_fixes`) |

**Winner: PR #29** for the innovative static regression test that checks the deployed HTML/CSS/JS contain markers for every UX fix. This prevents regressions where a merge conflict silently drops a fix. PR #28 has the most thorough XSS test (verifying safe content survives sanitisation).

---

## 4. Implementation Differences (Key Decisions)

### 4.1 Font Strategy

| Approach | PRs | Pros | Cons |
|----------|-----|------|------|
| Keep Google Fonts CDN | #26 | Zero effort | External dependency, privacy, perf |
| Remove CDN, system fallback | #29 | Zero bandwidth, maximum privacy | Inconsistent typography across OS |
| Self-host (13 subset files, 236 KB) | #27 | Complete coverage (cyrillic, latin-ext, vietnamese) | Large, many files |
| Self-host (4 variable files, 175 KB) | #28 | Optimal: variable fonts, latin + latin-ext only, 26% smaller | Best balance |

**Recommendation: PR #28's approach.** Variable `.woff2` fonts are the modern standard. Four files covering Inter (latin + latin-ext) and JetBrains Mono (latin + latin-ext) are sufficient for a product dashboard. The 175 KB total is acceptable.

### 4.2 Quick Actions Design

| Approach | PRs | Description |
|----------|-----|-------------|
| 3 plain buttons | #26, #27, #29 | Basic button row: "Launch new run", "Compare strategies", "Review compliance" |
| 4 icon cards with subtitles | #28 | Cards with icons, bold labels, and subtitles; includes "Open the playbook" |

**Recommendation: PR #28's 4-card approach.** The Playbook is one of the product's highest-value outputs (per the UX report itself) and deserves a quick-action card. Icons and subtitles provide better scannability.

### 4.3 Trust Banner Metadata

| Approach | PRs | Data shown |
|----------|-----|------------|
| Client-side text only | #26, #27 | Static disclaimer text |
| API `simulation_count` flat field | #29 | Disclaimer + count from API |
| API `meta` object | #28 | Count, conversation models, judge models, thresholds, timestamp |

**Recommendation: PR #28's `meta` object.** The trust banner's purpose is to provide full provenance. Showing which models generated the analysis and what thresholds were used gives compliance reviewers the information they need without clicking through to settings.

### 4.4 Navigation Guard Architecture

| Approach | PRs | Pattern |
|----------|-----|---------|
| Inline `confirm()` check | #26, #27, #29 | `if (currentPage === 'manual' && _manualSessionId) confirm(...)` |
| Guard registration pattern | #28 | `setNavigationGuard(fn)` / `clearNavigationGuard()` checked in `navigateTo()` |

**Recommendation: PR #28's guard pattern.** It's extensible — future features (unsaved Calibration form, active batch job) can register their own guards without modifying `navigateTo()`.

### 4.5 Poll Failure Escalation

| Approach | PRs | Pattern |
|----------|-----|---------|
| Per-panel inline logic | #26, #27, #28 | Threshold check duplicated in each `pollJob` call site |
| Shared `handlePollFailure()` helper | #29 | Single function reused by `pollJob` and benchmark polling |

**Recommendation: PR #29's shared helper.** DRY principle. This should be adopted regardless of which PR is chosen as the base.

### 4.6 Playbook TOC Layout

| Approach | PRs | Layout |
|----------|-----|--------|
| Simple heading list above content | #26, #27, #29 | Inline TOC prepended to article |
| Grid layout with sticky sidebar | #28 | `playbook-layout` grid: TOC in left column, content in right |

**Recommendation: PR #28's grid layout.** For a long document (16+ H2s, 33+ H3s), a sticky sidebar TOC is significantly more usable than an inline list that scrolls away.

---

## 5. Gaps and Issues

### 5.1 Issues Found in All PRs

1. **No `hashchange` de-duplication.** All PRs add both `hashchange` and `popstate` listeners, but don't guard against double-navigation when both fire for the same hash change. PR #28 partially addresses this by checking `hash !== currentPage` in the listener.

2. **`bleach` deprecation.** The `bleach` library is in maintenance mode (the maintainer recommends migrating to `nh3`). All PRs add `bleach>=6.0`. For a new addition, `nh3` would be more forward-looking, but `bleach` works correctly and this is a minor concern.

3. **No browser-level integration tests.** All PRs add Python-level tests but no Playwright/Selenium tests that verify the JavaScript actually works. PR #28 mentions running Playwright from `/tmp/ux_verify.py` but this script is not committed.

### 5.2 Per-PR Issues

| PR | Issue |
|----|-------|
| #26 | Missing P3-7 (self-hosted fonts). Smallest implementation, fewer abstractions. |
| #27 | 13 font files (236 KB) is excessive; includes cyrillic/vietnamese subsets unlikely needed. Same basic implementations as #26. |
| #28 | No `handlePollFailure` shared helper (duplicates escalation logic). No `min-width: 44px` on touch targets. |
| #29 | Missing self-hosted fonts (removed CDN but falls back to system fonts — Inter/JetBrains Mono are part of the brand). 3 quick actions instead of 4. Flat `simulation_count` instead of structured `meta`. |

---

## 6. Final Recommended Strategy

### 6.1 Use PR #28 as the Base

PR #28 (`cursor/ux-report-improvements-62ef`) is the clear winner:

- **Most complete coverage:** 24/24 shippable findings implemented (the only PR to complete P3-7 self-hosted fonts with optimal variable `.woff2` files).
- **Best implementation quality:** Dedicated `_render_safe_markdown()` helper, structured `meta` API response, extensible navigation guard, 4-card quick actions with icons, grid-based Playbook TOC.
- **Richest test coverage:** XSS test verifies both dangerous removal and safe content survival. Playbook meta fields tested. 112 total tests pass.
- **Best documentation:** `docs/UX_REPORT_IMPLEMENTATION.md` is a thorough audit trail mapping every finding to its fix, verification method, and forward-looking recommendations.

### 6.2 Cherry-Pick from Other PRs

Adopt these specific improvements from other PRs into the #28 base:

| Source | What to adopt | Why |
|--------|---------------|-----|
| PR #29 | `handlePollFailure()` shared helper | DRY: single function for poll escalation, reused by all panels |
| PR #29 | `min-width: 44px` on `.btn-compact` / `.filter-clear` | Better WCAG 2.5.5 compliance for touch targets |
| PR #29 | `tabindex="-1"` on `<main>` for skip link | Safari focus handling requires explicit `tabindex` on non-interactive skip targets |
| PR #29 | `test_static_assets_include_ux_report_fixes` regression test | Prevents silent UX regression when merge conflicts drop fixes |
| PR #29 | In-page hash protection (`isPageHash()`) | Prevents skip link / TOC anchor clicks from being treated as SPA route changes |

### 6.3 Specific Merge Instructions

1. **Merge PR #28** into `main` as the primary implementation.
2. **After merging #28**, create a follow-up PR that:
   - Extracts poll escalation into a shared `handlePollFailure(pollKey, panelId, failCount)` helper (from PR #29's pattern).
   - Adds `min-width: 44px` to `.btn-compact` and `.filter-clear` in `styles.css`.
   - Adds `tabindex="-1"` to the `<main>` element in `index.html`.
   - Adds an `isPageHash()` guard in the `hashchange` listener to distinguish SPA routes from in-page anchors.
   - Ports PR #29's `test_static_assets_include_ux_report_fixes` test (adapting assertions to match PR #28's code).
3. **Close PRs #26, #27, #29** as superseded, linking to the merged PR #28 and the follow-up PR.

### 6.4 Items Remaining After Merge

These items are deferred per the UX report's own guidance ("Phase 5 — Future Considerations"):

| Item | Effort | Trigger |
|------|--------|---------|
| P3-9: CSP inline `onclick` migration | High | Required only if deployment mandates strict CSP headers |
| State persistence (`sessionStorage`) | Medium | Improves UX for power users navigating back/forward |
| Transcript deep linking (`#runs/<id>`) | Medium | Enables shareable transcript URLs |
| `app.js` module splitting | Medium | Improves maintainability; PR #22 already started this with a different approach |
| Build-time cache busting | Low | Replace manual `?v=` query strings |
| `bleach` → `nh3` migration | Low | `bleach` is in maintenance mode |

---

## 7. Detailed PR Comparison Table

| Dimension | PR #26 | PR #27 | PR #28 (Recommended) | PR #29 |
|-----------|--------|--------|----------------------|--------|
| **Diff size** | +539/-40 | +1003/-40 | **+1432/-71** | +743/-62 |
| **Total tests** | 112 | 112 | 112 | **113** |
| **New tests** | 1 | 1 | 3 | **3** |
| **Findings covered** | 22/24 | 23/24 | **24/24** | 22/24 |
| **Font strategy** | CDN (unchanged) | Self-host (236 KB) | **Self-host (175 KB)** | System fallback |
| **Quick actions** | 3 buttons | 3 buttons | **4 cards w/ icons** | 3 buttons |
| **Trust banner** | Static text | Static text | **Rich (models, thresholds)** | Count only |
| **Calibration UI** | Basic form | Basic form | **3-section layout** | 2 forms |
| **Nav guard** | Inline confirm | Inline confirm | **Registered guard** | Inline helper |
| **Playbook TOC** | Inline list | Inline list | **Sticky sidebar grid** | Inline list |
| **Benchmark tokens** | Partial | Partial | **Complete** | Complete |
| **XSS test** | Basic | Basic | **Thorough** | Good |
| **Regression test** | ❌ | ❌ | ❌ | **✅** |
| **Poll helper** | Inline | Inline | Inline | **Shared** |
| **Touch width** | ❌ | ❌ | ❌ | **✅ (44px)** |
| **Skip link tabindex** | ❌ | ❌ | ❌ | **✅** |
| **Implementation report** | Good | Good | **Excellent** | Good |
| **Walkthrough artefacts** | Screenshots | Screenshots | **Video + screenshots** | Screenshots |
| **Overall grade** | B | B+ | **A** | B+ |

---

## 8. Conclusion

PR #28 is the recommended base for the consolidated implementation. It covers every shippable finding from the UX report with the highest implementation quality across backend sanitisation, frontend UI patterns, CSS theming, font optimisation, and documentation. The few improvements found in PR #29 (shared poll helper, touch target width, skip link `tabindex`, static regression test, in-page hash guard) should be adopted as a follow-up commit on top of PR #28.

Merging PR #28 plus the cherry-picked improvements from PR #29 would bring the dashboard from the baseline Nielsen score of 28/40 to an estimated 34–36/40, with the remaining gap concentrated in deferred items (CSP hardening, state persistence, module splitting) that the UX report itself classifies as future considerations.
