# Collection Swarm Dashboard — Definitive UX Report & Ship Plan

**Date:** 2026-05-02  
**Status:** Consolidated from three independent agent reviews, code-verified, with implementation spec  
**Tested build:** `app.js?v=ux-fixes-20260430b` on FastAPI `0.136.1`  
**Data:** 24 seeded simulations (`collection-swarm seed --count 24`)  
**Viewport:** Desktop 1920×1200 (primary), mobile 390×844 and 400 px (verified by two reviewers)  
**Source files audited:** `index.html` (124 lines), `styles.css` (2,949 lines), `app.js` (2,533 lines), `app.py` (1,284 lines)

---

## Part I — Cross-Review Synthesis

Three independent UX audits were conducted. This section critically evaluates each, reconciles disagreements, and establishes ground truth.

### Report A (PR #23 — `ux-report-2026-05-02.md`, 200 lines)

**Approach:** Heuristic evaluation (Nielsen 10) + persona-driven red-flag analysis. Strongest on identifying first-time-user cognitive load, trust framing for generated content, and deep-link navigation failure. Used browser screenshots and source inspection.

**Nielsen score given:** 26/40.

**Strengths:**
- Only report to identify the **trust framing gap** in the Playbook — generated recommendations appear as authoritative advice without sufficient caveats about sample size, synthetic origin, or legal limitations. Critical for a debt-collection domain product.
- Correctly identified the first-run dashboard has **no dominant call-to-action** for new users. (Code verification: a first-run state with action cards *does* exist in `app.js` lines 584–592, but only renders when `total_completed_runs === 0`. With seeded data, it never shows. Report A's concern is valid: the seeded/populated dashboard still lacks a clear "start here" path.)
- Persona red flags for three user types (analyst, power user, compliance reviewer) are well-differentiated and actionable.

**Weaknesses:**
- **Overstated the hash-navigation bug.** Report A claimed "direct hash navigation does not render the target route." Code verification shows the bootstrap IIFE (`app.js` line 2531) *does* read `location.hash` on initial page load and calls `navigateTo()`. A fresh load at `http://localhost:8000/#compliance` *does* render the Compliance page. What fails is mid-session hash changes (no `hashchange` listener) and back/forward (the `popstate` handler reads `e.state` which is null for the initial entry). The bug is real but narrower than stated.
- Tested fewer pages than the other two reviewers (omitted Arena, Playbook, Manual Run, Calibration, Model Benchmarks from the explicit walkthrough list).
- Heuristic scores (26/40) are the most conservative of the three but lack per-page granularity to justify the gap.

**Unique findings to preserve:**
1. Trust framing for generated content (P1)
2. `document.title` stays generic across routes
3. Route params in `history.state` but not in URL — reloads lose context
4. Metric help via `title` attribute is inconsistent and inaccessible to keyboard/AT users

---

### Report B (PR #24 — `ux-report.md`, 282 lines)

**Approach:** End-to-end browser walkthrough of all 13 pages + code-level audit. The most technically rigorous report. Verified interactions (transcript slideout, theme toggle, mobile drawer, invalid route), then cross-referenced with source code line numbers.

**Nielsen score given:** 30/40.

**Strengths:**
- **Most technically precise.** Identified that `handleRunRowKey` (line 823) is defined but never wired to any `<tr>` element — the keyboard handler exists dead in the code. Confirmed by source review.
- **Only report to flag the Calibration UI gap:** the backend exposes `POST /api/calibration/labels` and `POST /api/jobs/calibration`, but the frontend is read-only with a "use the CLI" hint. This is a real feature gap, not a design opinion.
- **Only report to identify the Playbook XSS risk:** `markdown.markdown(md_text, extensions=["tables", "fenced_code"])` renders server-side HTML that is injected via `innerHTML` in `app.js` line 1581. The Python `markdown` library does not strip raw HTML by default. If config-authored Markdown contains `<script>` tags, they execute. Code-verified: no sanitization layer exists.
- **Only report to identify token leaks:** benchmark fit-badge colors are hardcoded as inline OKLCH values in `app.js` (lines ~1913–1944) and some `styles.css` rules (`.bench-fit-badge.fit-strong`) are dark-only. Light-mode benchmarks will have contrast issues.
- **Only report to identify the "all checked" default problem:** Batch Comparison and Model Benchmarks default all checkboxes to checked, meaning a stray click submits a massive job.
- Identified the `pollJob` silent-retry issue: after 3 failures it toasts once then keeps polling without further user notification.
- False-positive correction: verified that all 144 inputs on Batch Comparison, Arena, and Benchmarks are properly labeled via wrapping `<label>` elements.

**Weaknesses:**
- Anti-pattern analysis ("does this look AI-generated?") is opinionated and somewhat subjective — calling the benchmark hero strip and gradient logo "AI slop tells" is a style judgment, not a usability finding. These are standard SaaS patterns.
- The "provocative questions" section is thought-provoking but speculative — suggesting the slideout should become a full route, or that Profiles/Strategies need `Cmd-K` search, are product vision questions beyond UX audit scope.
- Nielsen score (30/40) is reasonable but some heuristic scores (e.g., Error prevention = 2) seem harsh given that matrix count warnings and constrained inputs *do* exist.

**Unique findings to preserve:**
1. `handleRunRowKey` dead handler (P1 accessibility)
2. Calibration frontend gap (P2 functional)
3. Playbook Markdown XSS sink (P2 security)
4. Benchmark token leaks for light mode (P2 visual)
5. All-checked defaults on matrix forms (P2 error prevention)
6. `pollJob` silent retry after 3 failures (P2 feedback)
7. `btn-compact` (30 px) and `filter-clear` (28 px) below WCAG 2.5.5 touch target (44×44) (P3)
8. Score meters missing `aria-valuetext` (P3)
9. `prefers-reduced-motion` doesn't disable `@keyframes` (P3)
10. Google Fonts CDN as render-blocking external resource (P3 performance)
11. Manual Run silently drops session on navigation (P2 data loss)
12. CSP incompatibility: inline `onclick` everywhere (P3 security hardening)

---

### Report C (PR #25 — `UX_REPORT.md`, 467 lines)

**Approach:** Design-system-first analysis with OKLCH contrast math, token inventory, spacing audit, and page-by-page ratings. Browser-tested all 14 pages with screenshots and video recording.

**Overall score given:** 9.2/10.

**Strengths:**
- **Most thorough design-system analysis.** Catalogued every token category (spacing, radius, font, shadow, animation, easing), both theme variants, and the dark-mode weight compensation. No other report went this deep on tokens.
- **Quantitative contrast analysis** using OKLCH lightness delta. Identified `--text-tertiary` in light mode as borderline WCAG AA (delta 0.37). All three reports flagged this, but only Report C computed the numbers.
- **Most complete page coverage.** Tested all 14 sidebar destinations including Calibration, Model Benchmarks, and the theme toggle.
- Breakpoint inventory is the most thorough: documented all 5 responsive breakpoints with exact CSS behavior.

**Weaknesses:**
- **Significantly overrated the product.** 9.2/10 and multiple 10/10 page ratings do not reconcile with the P1 bugs found by Reports A and B (hash routing, dead keyboard handler, XSS risk, Calibration gap). A dashboard with broken deep linking and a potential XSS sink cannot be 9.2/10.
- **Missed critical bugs.** Did not identify: hash routing gap (found by A and B), `handleRunRowKey` dead handler (found by B), Playbook XSS risk (found by B), Calibration UI gap (found by B), all-checked defaults (found by B), `pollJob` silent retry (found by B), Manual Run session loss (found by B), benchmark token leaks (found by B).
- Navigation rating of 9.5/10 is unjustified given the routing issues.
- "Back/forward browser navigation works correctly via `popstate` listener" — this is partially incorrect. The `popstate` handler reads `e.state`, which is `null` for the initial history entry, causing fallback to dashboard on the first back-button press.

**Unique findings to preserve:**
1. `--text-xs` (11 px) below the 12 px accessibility floor
2. `tabular-nums` suggestion for percentage columns
3. `<meta name="theme-color">` for mobile browser chrome
4. Token extraction as standalone module suggestion

---

### Reconciled Scores

| Dimension | A (26/40) | B (30/40) | C (9.2/10) | Definitive |
|-----------|-----------|-----------|------------|------------|
| Visual design & tokens | Good | Good | Excellent | **Excellent** — the design system is genuinely strong |
| Information architecture | Good | Good | Excellent | **Very Good** — strong IA, but first-run path is unclear |
| Navigation & routing | Poor | Poor | Over-rated | **Needs Work** — hash routing gap, no `document.title` |
| Keyboard & accessibility | Fair | Fair | Over-rated | **Fair** — solid foundations with concrete gaps |
| Error prevention | Fair | Fair | Not assessed | **Fair** — defaults-all-checked, no form validation |
| Trust & domain safety | Poor | Fair | Not assessed | **Needs Work** — XSS risk, no trust framing |
| Empty states | Excellent | Excellent | Excellent | **Excellent** — best UX dimension, all agree |
| Mobile responsive | Unknown | Good | Unknown | **Good** — code-verified, partially browser-verified |

**Definitive Nielsen score: 28/40.** Above average for a technical dashboard. The gap to "ship-ready" is concentrated in routing, security, accessibility, and first-run UX — not in visual design.

---

## Part II — Exhaustive Findings Registry

Every finding from all three reports, deduplicated, code-verified, and classified. This is the single source of truth.

### Severity Definitions

- **P0 — Blocker:** Must fix before any user-facing deployment. Security risk or data-loss scenario.
- **P1 — Critical:** Breaks a core workflow. Fix before launch.
- **P2 — Important:** Degrades experience for a meaningful user segment. Fix in first post-launch sprint.
- **P3 — Nice to have:** Polish, optimization, or edge-case improvement. Schedule opportunistically.

---

### P0 — Blockers

#### P0-1: Playbook Markdown XSS Sink

**Reported by:** B  
**Verified:** Yes

`app.py` line 452 renders Markdown via `markdown.markdown(md_text, extensions=["tables", "fenced_code"])`. The Python `markdown` library does **not** strip raw HTML by default. The result is injected via `innerHTML` in `app.js` line 1581 into `<article class="playbook-content">`.

If any config file, strategy description, or simulation transcript contains `<script>`, `<img onerror>`, or similar, it executes in the browser context.

The Markdown source (`md_text`) originates from `generate_playbook()` which interpolates strategy IDs, profile IDs, and compliance messages — all derived from YAML config files. An attacker who can modify config or a malicious LLM response that leaks into strategy metadata could inject arbitrary JavaScript.

**Fix:**

```python
# app.py — server-side sanitization
import bleach

ALLOWED_TAGS = ["p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li",
                "table", "thead", "tbody", "tr", "th", "td", "code", "pre",
                "blockquote", "strong", "em", "a", "br", "hr", "span"]
ALLOWED_ATTRS = {"a": ["href", "title"], "th": ["align"], "td": ["align"]}

html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])
html = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)
```

Add `bleach` to `pyproject.toml` dependencies.

**Effort:** Low (5 lines of code + 1 dependency).

---

### P1 — Critical

#### P1-1: Hash Routing is Half-Implemented

**Reported by:** A, B  
**Verified:** Yes (with nuance)

**What works:**
- Initial page load reads `location.hash` and renders the correct page (line 2531).
- `navigateTo()` correctly calls `pushState` with hash URLs (line 29).
- Sidebar button clicks navigate correctly.

**What's broken:**
- No `hashchange` listener. Manually editing the hash in the address bar (without a full reload) does nothing.
- `popstate` handler reads `e.state` (line 35), which is `null` for the initial history entry. Pressing Back to the initial entry shows the dashboard regardless of the original hash.
- Invalid routes (e.g., `#runs/nonexistent`) silently render the dashboard with the wrong URL retained.
- `document.title` is never updated — every page shows "Collection Swarm" in the browser tab.
- Route params (selected profile, demo flag) are stored in `history.state` but not encoded in the URL. Reloads lose context.

**Fix spec:**

```javascript
// 1. Add hashchange listener (app.js, near line 44)
window.addEventListener('hashchange', () => {
  const hash = location.hash.replace('#', '') || 'dashboard';
  if (hash !== currentPage) navigateTo(hash);
});

// 2. Fix popstate to read hash as fallback
window.addEventListener('popstate', (e) => {
  const state = e.state || {};
  const page = state.page || location.hash.replace('#', '') || 'dashboard';
  currentPage = page;
  // ...existing nav-link update...
  renderPage(page, state.params || {});
});

// 3. Update document.title on every navigation
function navigateTo(page, params = {}) {
  // ...existing code...
  const titles = {
    dashboard: 'Dashboard', runs: 'Simulation Runs', launch: 'Launch Run',
    matrix: 'Batch Comparison', manual: 'Manual Run', playbook: 'Playbook',
    compliance: 'Compliance', arena: 'Arena', evolution: 'Evolution',
    calibration: 'Calibration', benchmarks: 'Model Benchmarks',
    profiles: 'Profiles', strategies: 'Strategies'
  };
  document.title = `${titles[page] || 'Page'} — Collection Swarm`;
  // ...rest of existing code...
}

// 4. Add unknown-route handling in renderPage
async function renderPage(page, params = {}) {
  const known = ['dashboard','runs','launch','matrix','manual','playbook',
                 'compliance','arena','evolution','calibration','benchmarks',
                 'profiles','strategies'];
  if (!known.includes(page)) {
    mainEl.innerHTML = emptyState('Page Not Found',
      `No page "${escapeHTML(page)}". <button class="text-link" onclick="navigateTo(\'dashboard\')">Go to Dashboard</button>`);
    return;
  }
  // ...existing code...
}
```

**Effort:** Medium (routing is load-bearing; needs careful testing of all navigation paths).

---

#### P1-2: Runs Table Rows Not Keyboard-Operable

**Reported by:** A, B, C  
**Verified:** Yes

`handleRunRowKey` (line 823) is defined but never wired. The `<tr>` elements have `onclick` (line 797) but no `tabindex`, `role`, or `onkeydown`. Keyboard users can only reach transcripts via the small "View" button.

**Fix spec:**

In the `renderRuns()` function (line ~796), change the `<tr>` template:

```javascript
// Before:
<tr onclick="openTranscript(${jsArg(r.id)})">

// After:
<tr tabindex="0"
    role="row"
    onclick="openTranscript(${jsArg(r.id)})"
    onkeydown="handleRunRowKey(event, ${jsArg(r.id)})"
    aria-label="Run ${escapeAttr(r.id)}, ${escapeAttr(fmtId(r.profile_id))} × ${escapeAttr(fmtId(r.strategy_id))}">
```

Add a focus-visible style:

```css
/* styles.css */
.data-table tbody tr:focus-visible {
  outline: 2px solid var(--accent-primary);
  outline-offset: -2px;
  background: var(--bg-hover);
}
```

**Effort:** Low.

---

#### P1-3: First-Run Dashboard Lacks Clear Next Action (for Populated State)

**Reported by:** A  
**Verified:** Partially

The zero-data first-run panel exists (lines 584–592) with three action cards. But with seeded or production data, the dashboard presents 6+ modules above the fold with no dominant CTA. A new analyst must scan strategy rankings, compliance alerts, charts, and operational details before understanding what to do.

**Fix spec:**

Add a lightweight "quick actions" strip above the strategy rankings when `total_completed_runs > 0`:

```javascript
function quickActionsStrip() {
  return `
    <div class="quick-actions">
      <button class="btn" onclick="navigateTo('launch')">Launch new run</button>
      <button class="btn" onclick="navigateTo('matrix')">Compare strategies</button>
      <button class="btn" onclick="navigateTo('compliance')">Review compliance</button>
    </div>`;
}
```

Collapse "Operational Details" by default (already implemented — just verify it stays collapsed).

**Effort:** Low.

---

#### P1-4: Generated Playbook Needs Trust Framing

**Reported by:** A  
**Verified:** Yes (domain-critical)

Generated playbook content includes strategy recommendations, compliance guidance, and objection handling advice. In a debt-collection domain, this can be mistaken for operational policy or legal advice. The current metadata line shows timestamp and simulation count, but lacks:

- Source disclaimer ("Synthetic simulation output — not legal or operational advice")
- Model pair used for generation
- Confidence/uncertainty indicators
- Compliance threshold assumptions
- "Review before operational use" banner

**Fix spec:**

Add a trust banner at the top of the playbook content in `renderPlaybook()`:

```javascript
const trustBanner = `
  <div class="trust-banner">
    <strong>Synthetic Analysis</strong>
    <p>This playbook is generated from ${fmtNum(data.simulation_count || 0)} simulated conversations
    using scripted backends. It is not legal advice, operational policy, or a substitute for
    human compliance review. Review all recommendations before operational use.</p>
  </div>`;
```

Style with a distinct info/warning treatment (not error-red, which would alarm; use `--info-bg` with a visible icon).

**Effort:** Low.

---

### P2 — Important

#### P2-1: `<main>` as `aria-live="polite"` Is Noisy

**Reported by:** A, B  
**Verified:** Yes

`index.html` line 103: `<main aria-live="polite">`. Every `innerHTML` swap on navigation triggers a screen reader re-read of the entire page content. This is verbose and disorienting.

**Fix:** Remove `aria-live` from `<main>`. Apply `aria-live="polite"` only to genuinely live regions: toast container, job progress panels, status badges.

```html
<!-- index.html line 103 -->
<main class="main-content" id="main-content" role="main">
```

The toast container already has `aria-live="polite"` (line 116 of `app.js`). Job panels need it added individually.

**Effort:** Low.

---

#### P2-2: Calibration Page is Read-Only Despite Backend Write Endpoints

**Reported by:** B  
**Verified:** Yes

Backend exposes `POST /api/calibration/labels` (line 553) and `POST /api/jobs/calibration` (line 561). The frontend Calibration page only displays existing data and tells users to use the CLI.

**Fix spec:**

Add a "Run Calibration" button and a label-upload form to the Calibration page:

```javascript
// In renderCalibration():
const launchSection = `
  <div class="card">
    <div class="card-header"><h2>Run Calibration</h2></div>
    <div class="card-body">
      <form onsubmit="startCalibration(event)">
        ${checkboxList('calibration-models', 'Models', models, models)}
        <div class="btn-row">
          <button class="btn btn-primary" type="submit">Start calibration</button>
        </div>
      </form>
    </div>
  </div>`;
```

Wire `startCalibration()` to `POST /api/jobs/calibration` with `pollJob` for progress tracking, matching the pattern used by Launch Run and Batch Comparison.

**Effort:** Medium.

---

#### P2-3: Batch Comparison & Benchmarks Default All Checkboxes to Checked

**Reported by:** B  
**Verified:** Yes

In `checkboxList()` (line ~1268), the third argument (`checked`) defaults to the full list. Batch Comparison renders with all profiles × all strategies × all models × all judges selected. A careless click on "Start" submits a massive combinatorial job.

**Fix spec:**

Default to empty selections. Add "Select all" / "Clear all" helper buttons (already exist for Benchmarks via `selectAllBenchmarkModels`; extend to Batch Comparison):

```javascript
// Change checkboxList default behavior:
function checkboxList(name, label, options, checked = []) {
  // checked now defaults to empty array instead of full list
}
```

Update call sites in `renderMatrix()` to pass `[]` instead of the full list. Add a `matrix-count` display that shows "0 simulations" until selections are made.

**Effort:** Low-Medium.

---

#### P2-4: Manual Run Silently Drops Session on Navigation

**Reported by:** B  
**Verified:** Yes (code path confirmed)

`_manualSessionId` is set on session start but cleared implicitly when `renderPage` is called for a different page (full `innerHTML` swap). The backend session remains alive, but the frontend loses track of it. Returning to Manual Run shows a fresh form.

**Fix spec:**

Option A (simplest): Show a confirmation dialog before navigating away during an active session:

```javascript
function navigateTo(page, params = {}) {
  if (currentPage === 'manual' && window._manualSessionId) {
    if (!confirm('You have an active manual session. Leave and lose progress?')) return;
  }
  // ...existing code...
}
```

Option B (better UX): Persist `_manualSessionId` across navigations and restore the session when returning to the Manual Run page.

**Effort:** Low (Option A) / Medium (Option B).

---

#### P2-5: `pollJob` Silently Retries After 3 Failures

**Reported by:** B  
**Verified:** Yes

After 3 consecutive API failures, `pollJob` (line 1362–1367) shows a single toast ("Connection interrupted, retrying…") but continues polling indefinitely with no further user notification. The job panel stays in queued/running state permanently.

**Fix spec:**

Add an escalation threshold. After 10 consecutive failures, stop polling and show a persistent error state:

```javascript
// In pollJob catch block:
if (_pollFailCounts[pollKey] >= 10) {
  clearPoll(pollKey);
  const panel = $(`#${panelId}`);
  if (panel) panel.innerHTML = emptyState('Connection Lost',
    'Unable to reach the server. <button class="btn" onclick="location.reload()">Reload page</button>');
  showToast('Polling stopped — connection lost', 'error', 10000);
  return;
}
```

**Effort:** Low.

---

#### P2-6: Benchmark Token Leaks (Light Mode)

**Reported by:** B  
**Verified:** Yes

Benchmark fit-badge colors are hardcoded as inline OKLCH values in `app.js` (lines ~1913–1944 in `benchmarkFitClass`/inline styles). Some `.bench-fit-badge` CSS rules are dark-theme only. Light-mode benchmarks will have washed-out or unreadable badge colors.

**Fix spec:**

Move all benchmark badge colors to CSS custom properties in both theme blocks:

```css
[data-theme="dark"] {
  --fit-strong: oklch(68% 0.17 155);
  --fit-moderate: oklch(75% 0.16 75);
  --fit-weak: oklch(65% 0.2 25);
  --fit-strong-bg: oklch(20% 0.04 155);
  --fit-moderate-bg: oklch(22% 0.04 75);
  --fit-weak-bg: oklch(20% 0.05 25);
}
[data-theme="light"] {
  --fit-strong: oklch(45% 0.17 155);
  --fit-moderate: oklch(55% 0.16 75);
  --fit-weak: oklch(50% 0.22 25);
  --fit-strong-bg: oklch(96% 0.03 155);
  --fit-moderate-bg: oklch(96% 0.03 75);
  --fit-weak-bg: oklch(96% 0.04 25);
}
```

Replace inline OKLCH values in `app.js` with `var(--fit-*)` references.

**Effort:** Medium.

---

#### P2-7: Tertiary Text Contrast in Light Mode

**Reported by:** B, C  
**Verified:** Yes (OKLCH lightness delta 0.37, below comfortable AA margin)

`--text-tertiary` in light mode is `oklch(60% 0.008 275)` on `--bg-root` `oklch(97% 0.006 275)`. Used for timestamps, subtitles, metadata. WCAG AA requires 4.5:1 contrast for normal text; this pairing is borderline.

**Fix:**

```css
[data-theme="light"] {
  --text-tertiary: oklch(50% 0.008 275); /* was 60% */
}
```

**Effort:** Trivial.

---

### P3 — Nice to Have

#### P3-1: No Skip-to-Content Link

**Reported by:** A, B, C  
**Verified:** Yes

No skip link exists. Keyboard users tab through 14+ sidebar items on every page load.

**Fix:**

```html
<!-- index.html, first child of <body> -->
<a href="#main-content" class="sr-only" style="position:absolute;z-index:100;
   top:-100px;left:0;padding:8px 16px;background:var(--accent-primary);
   color:var(--text-inverse);font-weight:600;border-radius:0 0 8px 0;
   transition:top 0.15s" onfocus="this.style.top='0'" onblur="this.style.top='-100px'">
  Skip to main content
</a>
```

**Effort:** Trivial.

---

#### P3-2: Score Meters Missing `aria-valuetext`

**Reported by:** B  
**Verified:** Yes

`scoreBarHTML()` (line ~268) renders `role="meter"` without `aria-valuetext`. Screen readers hear raw numbers without context (e.g., "0.81" instead of "81% — Good").

**Fix:** Add `aria-valuetext` with a human-readable label:

```javascript
function scoreBarHTML(label, value, color) {
  const pct = Math.round(value * 100);
  const level = pct >= 80 ? 'Good' : pct >= 50 ? 'Fair' : 'Poor';
  return `<div role="meter" aria-valuenow="${value}" aria-valuemin="0"
    aria-valuemax="1" aria-valuetext="${pct}% — ${level}" aria-label="${label}">…</div>`;
}
```

**Effort:** Low.

---

#### P3-3: `prefers-reduced-motion` Doesn't Disable `@keyframes`

**Reported by:** B  
**Verified:** Yes

`styles.css` lines 207–214 set `animation-duration: 0.01ms` and `transition-duration: 0.01ms`, but named `@keyframes` (`btn-spin`, `skeleton-pulse`) still play their first frame. Users who request reduced motion may still see a brief flash.

**Fix:** Add `animation: none !important;` to the reduced-motion block:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation: none !important;
    transition-duration: 0.01ms !important;
  }
}
```

**Effort:** Trivial.

---

#### P3-4: Touch Targets Below WCAG 2.5.5 (44×44 px)

**Reported by:** B  
**Verified:** Yes

`.btn-compact` has `min-height: 30px`. `.filter-clear` has `min-height: 28px`. Both are used in dense contexts (Runs table, filter bar).

**Fix:** Increase `min-height` to 36 px (compromise) or 44 px (full compliance). Add `min-width: 44px` where appropriate.

**Effort:** Low (may affect table density — test visually).

---

#### P3-5: `--text-xs` Below 12 px Floor

**Reported by:** C  
**Verified:** Yes

`--text-xs: 0.6875rem` = 11 px at 16 px root. Used for supplementary labels. Below the commonly recommended 12 px minimum for legibility.

**Fix:** `--text-xs: 0.75rem;` (12 px).

**Effort:** Trivial.

---

#### P3-6: No `tabular-nums` on Numeric Columns

**Reported by:** C  
**Verified:** Cosmetic issue confirmed

Percentage columns in tables don't use `font-variant-numeric: tabular-nums`, causing slight horizontal misalignment between rows (e.g., "8%" vs "97%").

**Fix:**

```css
.data-table td:nth-child(n+9) { /* payment, success columns */
  font-variant-numeric: tabular-nums;
}
```

**Effort:** Trivial.

---

#### P3-7: Google Fonts as Render-Blocking External Resource

**Reported by:** B  
**Verified:** Yes

`index.html` lines 9–12 load Inter and JetBrains Mono from `fonts.googleapis.com`. Enterprise networks may block this. The `rel="preload"` helps but doesn't eliminate the FOIT/FOUT risk.

**Fix:** Self-host the font files in `/static/fonts/`. Use `@font-face` with `font-display: swap`.

**Effort:** Medium.

---

#### P3-8: Sidebar Section Labels Hidden from Screen Readers

**Reported by:** C  
**Verified:** Yes

`.nav-label` elements use `aria-hidden="true"`, meaning screen readers skip the "Overview", "Analysis", "Configuration" group headers.

**Fix:** Remove `aria-hidden="true"` from `.nav-label` divs. They provide useful context.

**Effort:** Trivial.

---

#### P3-9: Inline `onclick` Handlers Incompatible with Strict CSP

**Reported by:** B  
**Verified:** Yes

All event handling uses inline `onclick="..."` in HTML templates. A strict Content-Security-Policy (`script-src 'self'`) would break the entire app.

**Fix:** Migrate to `addEventListener` delegation patterns. This is a significant refactor — defer unless CSP headers are required for deployment.

**Effort:** High.

---

#### P3-10: `document.title` / `<meta theme-color>` / Cache Busting

**Reported by:** A, C  
**Verified:** Yes

- `document.title` never changes (covered in P1-1 fix).
- No `<meta name="theme-color">` for mobile browser chrome.
- Cache busting is a manual `?v=` string.

**Fix:**

```html
<!-- index.html -->
<meta name="theme-color" content="#0f0f17" media="(prefers-color-scheme: dark)">
<meta name="theme-color" content="#f5f5f7" media="(prefers-color-scheme: light)">
```

Cache busting: derive version from file hash at build time, or use an ETag-based strategy.

**Effort:** Low.

---

#### P3-11: Playbook Lacks In-Page TOC

**Reported by:** B  
**Verified:** Yes

The Playbook page renders a long Markdown document (16+ H2s, 33+ H3s) with no table of contents or anchor links. Users must scroll the entire page.

**Fix:** Generate a TOC from heading elements after the Markdown is rendered:

```javascript
function generateTOC(container) {
  const headings = container.querySelectorAll('h2, h3');
  if (headings.length < 4) return '';
  // ...build TOC HTML...
}
```

**Effort:** Medium.

---

#### P3-12: Theme Toggle Discoverability

**Reported by:** C  
**Verified:** Yes (two reviewers couldn't find/click it)

The theme toggle is at the absolute bottom of the sidebar. With 14 nav items plus section headers, it may be below the viewport fold.

**Fix:** Add `position: sticky; bottom: 0` to `.sidebar-footer`:

```css
.sidebar-footer {
  position: sticky;
  bottom: 0;
  background: var(--bg-surface);
  border-top: 1px solid var(--border-subtle);
  padding: var(--space-3) var(--space-4);
}
```

**Effort:** Low.

---

#### P3-13: Hardcoded Model IDs in Production Preset

**Reported by:** B  
**Verified:** Yes

`selectProductionBenchmarkModels()` (line 1697) hardcodes `['composer-2', 'gpt-5.5', ...]`. If the backend model list changes, the preset silently selects fewer models with no warning.

**Fix:** Validate selected IDs against the current model list and show a toast if any are missing:

```javascript
window.selectProductionBenchmarkModels = function() {
  const available = new Set($$('input[name="benchmark-models"]').map(i => i.value));
  const wanted = ['composer-2', 'gpt-5.5', ...];
  const missing = wanted.filter(id => !available.has(id));
  if (missing.length) showToast(`Models not available: ${missing.join(', ')}`, 'warning');
  // ...select available ones...
};
```

**Effort:** Low.

---

## Part III — What Ships Well (Preserve These)

All three reports agree on these strengths. They must not regress during fixes:

1. **Empty-state writing.** Arena, Evolution, Calibration, Manual Run — each teaches the user a concrete next action. This is the single best UX dimension.
2. **Slideout focus management.** Real focus trap, focus return on close, Escape to dismiss. Better than most shipping products.
3. **OKLCH design system.** Perceptually uniform, dual-themed, with token parity across dark/light. The dark-mode weight compensation (font-weight 350) is a rare thoughtful detail.
4. **Compliance posture.** Above-the-fold compliance banner, dedicated Compliance page, automatic exclusion in Playbook. This is a coherent compliance story for a sensitive domain.
5. **Mobile drawer.** Off-canvas with overlay, focus return, Escape dismiss. All three reports confirmed it works.
6. **Semantic color system.** Success/warning/danger/info with background and border variants. Color is never the sole differentiator — badges always include text.
7. **Typography pairing.** Inter + JetBrains Mono with clear hierarchy and `fmtId()` humanization.
8. **Progressive disclosure.** "Advanced model settings" collapsible, "Operational Details" disclosure, strategy ranking tabs.

---

## Part IV — Implementation Plan

### Ship Phases

The plan is ordered to minimize risk and maximize user-facing impact per phase. Each phase is independently deployable.

---

### Phase 0 — Security Gate (Ship-Blocker)

**Target:** Must complete before any user-facing deployment.  
**Items:** P0-1  
**Files changed:** `app.py`, `pyproject.toml`

| Step | File | Change | Lines |
|------|------|--------|-------|
| 0.1 | `pyproject.toml` | Add `bleach>=6.0` to dependencies | ~1 line |
| 0.2 | `app.py` | Import `bleach`, define allowed tags/attrs | ~8 lines |
| 0.3 | `app.py` | Wrap `markdown.markdown()` output with `bleach.clean()` in `get_playbook()` (line 452) | ~2 lines |
| 0.4 | `tests/test_web.py` | Add test: inject `<script>alert(1)</script>` in strategy description, verify it's stripped from playbook HTML response | ~15 lines |

**Verification:** `pytest tests/test_web.py -k playbook_xss -v`

---

### Phase 1 — Core Navigation & Keyboard (P1 fixes)

**Target:** Fix the highest-impact UX gaps.  
**Items:** P1-1, P1-2, P1-3, P1-4  
**Files changed:** `app.js`, `index.html`, `styles.css`

| Step | Item | File | Change | Lines |
|------|------|------|--------|-------|
| 1.1 | P1-1 | `app.js` | Add `hashchange` listener, fix `popstate` fallback to read hash, add unknown-route handler, update `document.title` per page | ~40 lines |
| 1.2 | P1-2 | `app.js` | Wire `tabindex="0"`, `role="row"`, `onkeydown="handleRunRowKey"` to `<tr>` in `renderRuns()` | ~5 lines |
| 1.3 | P1-2 | `styles.css` | Add `tr:focus-visible` style | ~5 lines |
| 1.4 | P1-3 | `app.js` | Add `quickActionsStrip()` function, insert in `renderDashboard()` below stats when `total > 0` | ~15 lines |
| 1.5 | P1-3 | `styles.css` | Style `.quick-actions` strip | ~10 lines |
| 1.6 | P1-4 | `app.js` | Add trust banner HTML in `renderPlaybook()` above the playbook content | ~12 lines |
| 1.7 | P1-4 | `styles.css` | Style `.trust-banner` with `--info-bg`, icon, padding | ~10 lines |

**Verification:**
- Navigate to `http://localhost:8000/#compliance` — verify Compliance renders.
- Press Back — verify previous page renders (not dashboard).
- Navigate to `#nonexistent` — verify "Page Not Found" renders.
- Check browser tab title changes on each navigation.
- Tab through Runs table — verify rows receive focus and Enter opens transcript.
- Load Dashboard with seed data — verify quick-actions strip appears.
- Load Playbook — verify trust banner appears above content.

---

### Phase 2 — Accessibility & Error Prevention (P2 fixes)

**Target:** Bring accessibility to AA compliance, fix error-prevention gaps.  
**Items:** P2-1, P2-3, P2-4, P2-5, P2-6, P2-7  
**Files changed:** `app.js`, `index.html`, `styles.css`

| Step | Item | File | Change |
|------|------|------|--------|
| 2.1 | P2-1 | `index.html` | Remove `aria-live="polite"` from `<main>` |
| 2.2 | P2-1 | `app.js` | Add `aria-live="polite"` to job progress panel containers |
| 2.3 | P2-3 | `app.js` | Change `checkboxList()` default to empty array; update call sites in `renderMatrix()` |
| 2.4 | P2-3 | `app.js` | Add "Select all" / "Clear all" buttons to Batch Comparison |
| 2.5 | P2-4 | `app.js` | Add `beforeNavigate()` guard that warns if `_manualSessionId` is active |
| 2.6 | P2-5 | `app.js` | Add failure escalation threshold (10 retries) in `pollJob`, show persistent error state |
| 2.7 | P2-6 | `styles.css` | Move benchmark badge colors to CSS custom properties in both themes |
| 2.8 | P2-6 | `app.js` | Replace inline OKLCH values with `var(--fit-*)` references |
| 2.9 | P2-7 | `styles.css` | Darken `--text-tertiary` in light mode from `oklch(60%)` to `oklch(50%)` |

**Verification:**
- Screen reader test: navigate between pages, verify no full-page announcements.
- Open Batch Comparison — verify no checkboxes are pre-selected.
- Start Manual Run, navigate away — verify confirmation dialog appears.
- Kill server, verify `pollJob` stops after 10 failures with persistent error message.
- Switch to light mode, view benchmarks — verify badge colors are readable.
- Switch to light mode, check tertiary text contrast with devtools.

---

### Phase 3 — Calibration UI & Feature Completeness (P2-2)

**Target:** Close the backend↔frontend gap.  
**Items:** P2-2  
**Files changed:** `app.js`, `styles.css`

| Step | File | Change |
|------|------|--------|
| 3.1 | `app.js` | Add `startCalibration()` function wired to `POST /api/jobs/calibration` |
| 3.2 | `app.js` | Add calibration form UI in `renderCalibration()` with model selection checkboxes |
| 3.3 | `app.js` | Add `pollJob` integration for calibration progress tracking |
| 3.4 | `app.js` | Add label upload UI (file picker or textarea) wired to `POST /api/calibration/labels` |
| 3.5 | `styles.css` | Any calibration-specific styles (reuse existing card/form patterns) |

**Verification:**
- Open Calibration page — verify "Run Calibration" form appears alongside existing data display.
- Select models, click Start — verify job starts and progress polls correctly.
- Verify label upload form submits to `/api/calibration/labels` and shows success toast.

---

### Phase 4 — Polish & Hardening (P3 fixes)

**Target:** Final polish pass before public launch.  
**Items:** P3-1 through P3-13  

| Step | Item | File | Change | Effort |
|------|------|------|--------|--------|
| 4.1 | P3-1 | `index.html` | Add skip-to-content link | Trivial |
| 4.2 | P3-2 | `app.js` | Add `aria-valuetext` to score meters | Low |
| 4.3 | P3-3 | `styles.css` | Fix `prefers-reduced-motion` to disable `@keyframes` | Trivial |
| 4.4 | P3-4 | `styles.css` | Increase `.btn-compact` and `.filter-clear` min-height | Low |
| 4.5 | P3-5 | `styles.css` | Bump `--text-xs` from 0.6875rem to 0.75rem | Trivial |
| 4.6 | P3-6 | `styles.css` | Add `tabular-nums` to numeric table columns | Trivial |
| 4.7 | P3-7 | `static/fonts/` | Self-host Inter + JetBrains Mono, update `@font-face` | Medium |
| 4.8 | P3-8 | `index.html` | Remove `aria-hidden` from `.nav-label` | Trivial |
| 4.9 | P3-10 | `index.html` | Add `<meta name="theme-color">` for both schemes | Trivial |
| 4.10 | P3-11 | `app.js` | Generate TOC for Playbook from headings | Medium |
| 4.11 | P3-12 | `styles.css` | Make `.sidebar-footer` sticky | Low |
| 4.12 | P3-13 | `app.js` | Validate production preset IDs against available models | Low |

**Verification:** Full regression test of all 14 pages in both themes, at desktop and mobile breakpoints.

---

### Phase 5 — Future Considerations (Not in Ship Plan)

These are product direction questions, not ship-blockers:

- **CSP hardening** (P3-9): Migrate from inline `onclick` to `addEventListener` delegation. Large refactor; defer unless CSP is a deployment requirement.
- **State persistence**: Cache page-local state (filters, sort, manual sessions) per route in `sessionStorage` so back/forward doesn't blow it away.
- **Transcript deep linking**: Make the slideout a full route (`#runs/<id>`) for shareable URLs that survive page reload.
- **`Cmd-K` global search**: Search Profiles, Strategies, and Runs from anywhere.
- **Module splitting**: Break `app.js` (2,533 lines) into per-page modules with a build step.
- **Cost estimation**: Show estimated API cost on Launch Run based on selected model + backend.
- **Run pagination**: Add server-side pagination for the Runs table beyond ~100 rows.
- **Export functionality**: CSV/JSON export for runs, playbook, and compliance data.

---

## Appendix A — Files Modified Per Phase

| Phase | `index.html` | `styles.css` | `app.js` | `app.py` | `pyproject.toml` | Tests |
|-------|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 | | | | ✓ | ✓ | ✓ |
| 1 | | ✓ | ✓ | | | |
| 2 | ✓ | ✓ | ✓ | | | |
| 3 | | ✓ | ✓ | | | |
| 4 | ✓ | ✓ | ✓ | | | |

---

## Appendix B — Testing Matrix

| Test | Phase | Type | Command / Steps |
|------|-------|------|-----------------|
| XSS sanitization | 0 | Automated | `pytest tests/test_web.py -k xss` |
| Hash navigation | 1 | Manual | Load `#compliance`, `#nonexistent`; press Back/Forward |
| Keyboard rows | 1 | Manual | Tab through Runs table, press Enter on focused row |
| Title updates | 1 | Manual | Navigate all pages, check browser tab title |
| Trust banner | 1 | Manual | Load Playbook, verify banner text |
| Quick actions | 1 | Manual | Load Dashboard with data, verify strip appears |
| aria-live scope | 2 | Screenreader | Navigate pages, verify no full-page re-read |
| Checkbox defaults | 2 | Manual | Open Batch Comparison, verify empty selections |
| Session guard | 2 | Manual | Start Manual session, navigate away, verify dialog |
| Poll escalation | 2 | Manual | Kill server during active job, count toasts |
| Light-mode badges | 2 | Manual | Switch to light theme, open Benchmarks, check badges |
| Contrast | 2 | DevTools | Measure tertiary text contrast ratio in light mode |
| Calibration UI | 3 | Manual | Run calibration from UI, verify job completes |
| Full regression | 4 | Manual | All 14 pages, both themes, desktop + mobile |
| Reduced motion | 4 | Manual | Enable reduced-motion, verify no animations |
| Touch targets | 4 | DevTools | Measure button hit areas on mobile viewport |

---

## Appendix C — Reviewer Comparison Matrix

| Finding | Report A (PR #23) | Report B (PR #24) | Report C (PR #25) |
|---------|:---:|:---:|:---:|
| Hash routing bug | ✓ (overstated) | ✓ (precise) | ✗ (missed) |
| `handleRunRowKey` dead handler | ✗ | ✓ | ✗ |
| Playbook XSS risk | ✗ | ✓ | ✗ |
| Calibration UI gap | ✗ | ✓ | ✗ |
| All-checked defaults | ✗ | ✓ | ✗ |
| `pollJob` silent retry | ✗ | ✓ | ✗ |
| Manual session loss | ✗ | ✓ | ✗ |
| Trust framing gap | ✓ | ✗ | ✗ |
| First-run CTA gap | ✓ | ✗ | ✗ |
| `document.title` static | ✓ | ✗ | ✗ |
| Persona red flags | ✓ | ✓ | ✗ |
| Tertiary text contrast | ✗ | ✓ | ✓ |
| OKLCH token analysis | ✗ | ✓ | ✓ |
| Design system deep-dive | ✗ | Partial | ✓ |
| Page-by-page ratings | ✗ | ✓ | ✓ |
| Breakpoint inventory | ✗ | Partial | ✓ |
| Benchmark token leaks | ✗ | ✓ | ✗ |
| Touch target compliance | ✗ | ✓ | ✗ |
| CSP incompatibility | ✗ | ✓ | ✗ |
| `aria-live` on `<main>` | ✓ | ✓ | ✗ |
| Skip link missing | ✓ | ✓ | ✓ |
| `aria-valuetext` on meters | ✗ | ✓ | ✗ |
| Reduced motion `@keyframes` | ✗ | ✓ | ✗ |
| Google Fonts CDN risk | ✗ | ✓ | ✗ |
| `--text-xs` below 12px | ✗ | ✗ | ✓ |
| `tabular-nums` | ✗ | ✗ | ✓ |
| `<meta theme-color>` | ✗ | ✗ | ✓ |
| **Total unique findings** | **5** | **19** | **4** |

**Verdict:** Report B (PR #24) was the most technically rigorous and caught the most unique, code-verified issues — including the only security finding (XSS) and the only functional gap (Calibration). Report A (PR #23) contributed the most valuable domain-level insight (trust framing) and persona analysis. Report C (PR #25) had the most thorough design-system analysis but missed all critical bugs and significantly overrated the product.

The definitive score of **28/40** reflects the reality: an excellent visual foundation with real routing, security, and accessibility gaps that must be fixed before shipping to real users.
