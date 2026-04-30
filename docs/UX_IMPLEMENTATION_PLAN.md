# UX Report Implementation Plan

This plan translates every finding from `docs/ux-report.md` into actionable work items,
organized into six workstreams. Each item specifies the files that change, what changes,
and the acceptance criteria. Items within each workstream are ordered by impact.

## Architecture Note

All UI work is scoped to three files:

- `src/collection_swarm/web/static/app.js` (routing, rendering, interaction)
- `src/collection_swarm/web/static/styles.css` (design system, layout, theming)
- `src/collection_swarm/web/static/index.html` (shell, sidebar, slideout)

Backend API changes (new endpoints or response shape changes) go in:

- `src/collection_swarm/web/app.py`
- `src/collection_swarm/store.py` (new query methods)

---

## Workstream 1: Dashboard Decision Surface

**Goal:** Transform the dashboard from an activity summary into a decision-support
tool. Users should see "which strategy to use, which to avoid, and why" before they
see operational metrics.

**UX report references:** Dashboard findings, Cognitive Load Assessment, P1 (Reframe
Dashboard Around Decisions).

### 1.1 Elevate Strategy Rankings to top of dashboard

**Files:** `app.js` (`renderDashboard`)

**Change:** Move the Strategy Rankings section above the Average Scores / Outcome
Distribution grid. The strategy ranking is the highest-value insight. It currently
sits below two chart cards.

**Implementation:**
- In `renderDashboard`, move `strategySection` above the `.grid-2` block.
- Add a brief lead-in: "Best strategy per debtor profile, ranked by payment
  probability."

**Acceptance:** Strategy Rankings appears immediately below the overview strip, before
score and outcome charts.

### 1.2 Add compliance exceptions summary to dashboard

**Files:** `app.js` (`renderDashboard`), `app.py` (optional: include exclusions in
`/api/dashboard` response)

**Change:** Add a compact compliance alert area between Strategy Rankings and the
score/outcome grid. When exclusions exist, show count and the most critical
strategy-profile pairs. When none exist, show a single-line "No compliance exceptions"
confirmation with evidence count.

**Implementation:**
- Fetch `/api/compliance/exclusions` in parallel with `/api/dashboard`.
- Render a lightweight alert strip (not full cards). Use danger background for
  exclusions, success background for all-clear.
- Each exclusion shows strategy x profile, compliance score, escalation risk.
- "View details" links to the Compliance page.

**Acceptance:** Dashboard shows compliance status without navigating away. Exclusions
render with danger treatment; all-clear renders with success treatment and run count.

### 1.3 Add first-run guidance panel

**Files:** `app.js` (`renderDashboard`), `styles.css`

**Change:** When `total_runs === 0`, replace the empty-state charts with a guided
start panel offering three actions:

1. "Run a demo simulation" (navigates to Launch with defaults pre-filled).
2. "Compare strategies for a profile" (navigates to Matrix with one profile
   pre-selected).
3. "Review compliance risks" (navigates to Compliance).

Each action includes a one-sentence explanation of what it produces.

When `total_runs > 0`, hide this panel. Consider showing it as a collapsible "Getting
started" section for low run counts (< 5).

**Implementation:**
- Add a `renderFirstRunPanel()` function that returns the HTML.
- Add `.first-run-panel`, `.first-run-action` styles.
- Conditionally render in `renderDashboard` based on `total_runs`.

**Acceptance:** Empty dashboard shows three clear actions. Each navigates to the
correct page. Panel disappears after simulations exist.

### 1.4 Demote operational metrics to collapsible section

**Files:** `app.js` (`renderDashboard`), `styles.css`

**Change:** Move Cost and Tokens out of the primary overview strip into a collapsible
"Operational Details" area below the score/outcome grid. The overview strip should
focus on Runs, Completed, Failed, and Success Rate.

**Implementation:**
- Remove Cost and Tokens from the overview strip.
- Add a `<details>` element below the grid with summary "Operational Details"
  containing cost, token counts, and any other infrastructure metrics.

**Acceptance:** Overview strip contains 4 items max. Cost/tokens are visible via
expand, not competing with strategic metrics.

### 1.5 Add metric definitions via tooltips

**Files:** `app.js` (`scoreBarHTML`, `renderDashboard`), `styles.css`

**Change:** Add tooltip text to each score bar and overview metric explaining what it
measures and how to interpret it.

**Implementation:**
- Add a `title` attribute or a custom tooltip to `scoreBarHTML` for each known metric.
- Define tooltip text per metric: "Payment Probability: Estimated likelihood the
  debtor would actually pay based on judge assessment (higher is better)."
- Add tooltip for Escalation Risk clarifying it's a lower-is-better metric.
- Style tooltips consistently (dark background, max-width 280px, slight delay).

**Acceptance:** Hovering any metric label shows a definition. Escalation Risk tooltip
explicitly says "lower is better."

### 1.6 Clarify escalation risk visual treatment

**Files:** `app.js` (`scoreBarHTML` or `renderDashboard`), `styles.css`

**Change:** Escalation Risk is a lower-is-better metric displayed alongside
higher-is-better metrics using the same good/mid/bad color scale. This can confuse
interpretation.

**Implementation:**
- Invert the color logic for Escalation Risk: low values get `score-good`, high
  values get `score-bad`.
- Add "(lower is better)" label suffix or a small icon indicator.
- In the strategy comparison table, apply the same inversion.

**Acceptance:** Escalation Risk of 0.1 shows green, 0.5 shows red. Visual treatment
matches meaning across all score displays.

---

## Workstream 2: Launch and Matrix Clarity

**Goal:** Help users make informed choices when configuring simulations. Reduce
cognitive load by providing context, hiding advanced options, and previewing impact.

**UX report references:** Launch Run findings, Matrix Runs findings, Cognitive Load
Assessment, P1 (Add Context to Launch and Matrix Controls).

### 2.1 Add profile and strategy descriptions to selectors

**Files:** `app.js` (`renderLaunch`, `renderMatrix`), `app.py` (`/api/config/run-options`)

**Change:** When a user selects a profile or strategy, show a brief description below
the selector: archetype, debt amount, key constraints (for profiles); tone, opening
approach, negotiation tactic (for strategies).

**Implementation:**
- Backend: ensure `/api/config/run-options` includes summary fields for each profile
  and strategy (archetype, debt_amount, tone, opening_approach at minimum).
- Frontend: add `onchange` handlers that update a description area below each
  selector.
- Show the description in a muted text block below the selector.

**Acceptance:** Selecting a profile shows its archetype and debt amount. Selecting a
strategy shows its tone and approach.

### 2.2 Move model selectors behind "Advanced" disclosure

**Files:** `app.js` (`renderLaunch`, `renderMatrix`, `renderManual`)

**Change:** Model selection (conversation model, judge model) is infrastructure, not
strategy. Most users should use defaults.

**Implementation:**
- Wrap model selectors in a `<details><summary>Advanced model settings</summary>`
  element.
- Keep defaults pre-selected and functional when collapsed.

**Acceptance:** Launch, Matrix, and Manual pages show profile/strategy selectors
directly. Model selectors are accessible but collapsed by default.

### 2.3 Show live matrix size calculation

**Files:** `app.js` (`renderMatrix`)

**Change:** Show a live calculation: `profiles x strategies x reps = N total
simulations` that updates as checkboxes and reps change.

**Implementation:**
- Add an `updateMatrixCount()` function triggered by checkbox and input changes.
- Display the calculation prominently near the submit button.
- Add a warning when total exceeds a threshold (e.g., 50 simulations): "This will
  run N simulations. Large matrices take longer and cost more."

**Acceptance:** Changing any checkbox or rep value immediately updates the simulation
count. Warning appears for large matrices.

### 2.4 Rename "Matrix Runs" to "Batch Comparison"

**Files:** `index.html` (sidebar nav label), `app.js` (`renderMatrix` page header)

**Change:** "Matrix Runs" is technical jargon. "Batch Comparison" (or "Strategy
Comparison") better describes the user intent.

**Implementation:**
- Update sidebar button text.
- Update page header h1 and description.
- Keep the `data-page="matrix"` value for routing stability.

**Acceptance:** Sidebar and page header say "Batch Comparison." All routing continues
to work.

### 2.5 Replace [END_CONVERSATION] token in Manual Run

**Files:** `app.js` (`renderManualSession`), possibly `app.py` (manual session handling)

**Change:** The textarea placeholder exposes internal implementation syntax
(`[END_CONVERSATION]`). Users should not need to type protocol tokens.

**Implementation:**
- Remove the `[END_CONVERSATION]` instruction from the placeholder.
- Update placeholder to: "Type your response as the [role]."
- The "Finish and judge" button already exists and handles session termination. Make
  it more prominent or add a confirmation step.
- Optionally add a checkbox: "End conversation after this turn" that auto-appends the
  signal server-side.

**Acceptance:** No implementation tokens visible in the UI. Users end conversations
via button, not by typing protocol strings.

### 2.6 Add cancel job action

**Files:** `app.js` (`renderJobPanel`), `app.py` (new `/api/jobs/{id}/cancel` endpoint)

**Change:** There is no way to cancel a running or queued job.

**Implementation:**
- Backend: add a `POST /api/jobs/{id}/cancel` endpoint that sets `job.status =
  "cancelled"` and cancels the associated asyncio task.
- Frontend: add a "Cancel" button in `renderJobPanel` when status is "running" or
  "queued".
- Handle cancellation gracefully: save partial results, show "Cancelled" status.

**Acceptance:** Running and queued jobs show a Cancel button. Clicking it stops the
job and updates the UI.

---

## Workstream 3: Runs Table Power Features

**Goal:** Transform the runs table from a simple list into an analysis workspace with
sorting, search, export, and comparison.

**UX report references:** Simulation Runs findings, Power User persona, P2 (Upgrade
Runs Table for Analysis Workflows).

### 3.1 Add sortable table columns

**Files:** `app.js` (`renderRuns`, `filterRuns`), `styles.css`

**Change:** Table headers should be clickable to sort by that column. Support
ascending and descending sort. Visual indicator shows current sort column and
direction.

**Implementation:**
- Track `_sortColumn` and `_sortDirection` in module state.
- Add `onclick` handlers to `<th>` elements.
- Sort the filtered array before rendering.
- Add sort indicator (arrow) to the active header. Style with CSS.
- Default sort: by `started_at` descending (newest first).

**Acceptance:** Clicking any column header sorts the table. Clicking again reverses
direction. Arrow indicator shows current sort.

### 3.2 Add search field

**Files:** `app.js` (`renderRuns`, `filterRuns`)

**Change:** Add a text search field that filters runs by run ID, profile, strategy,
outcome, or transcript content.

**Implementation:**
- Add a text input to the filter bar.
- In `filterRuns`, apply a case-insensitive substring match across relevant fields.
- Debounce input (200ms) to avoid excessive re-renders.

**Acceptance:** Typing in the search field filters the table in real-time across
multiple fields.

### 3.3 Add active filter chips

**Files:** `app.js` (`filterRuns`), `styles.css`

**Change:** When filters are active, show chips below the filter bar displaying each
active filter with a dismiss button. This makes active filters scannable at a glance.

**Implementation:**
- After applying filters, render chip elements for each non-empty filter.
- Each chip shows the filter name and value, with an X button to clear that specific
  filter.
- Style chips as small badges with dismiss affordance.

**Acceptance:** Active filters appear as dismissible chips. Dismissing a chip clears
that filter and updates the table.

### 3.4 Add CSV export

**Files:** `app.js` (`renderRuns`)

**Change:** Add an "Export CSV" button that exports the current filtered view.

**Implementation:**
- Add a button to the filter bar or page header.
- Generate CSV from the currently filtered runs array.
- Trigger a browser download with a timestamped filename.
- Include all visible columns plus judgment scores.

**Acceptance:** Clicking Export CSV downloads a CSV file containing all currently
filtered runs with headers.

### 3.5 Add Space key activation for table rows

**Files:** `app.js` (`filterRuns`)

**Change:** Table rows with `role="button"` only respond to Enter key. Space should
also activate them per ARIA button pattern.

**Implementation:**
- In the `onkeydown` handler on table rows, add Space key support.
- Prevent default scroll behavior when Space activates a row.

**Acceptance:** Pressing Space on a focused table row opens the transcript, same as
Enter.

### 3.6 Add multi-run comparison mode (stretch)

**Files:** `app.js`, `styles.css`

**Change:** Allow selecting multiple runs and viewing them side-by-side for
comparison.

**Implementation:**
- Add checkboxes to table rows.
- Add a "Compare selected" button that opens a comparison view.
- Comparison view shows transcripts and scores in columns.
- Minimum 2, maximum 4 runs for comparison.

**Acceptance:** Users can select 2-4 runs and see them compared side-by-side with
scores and transcripts.

---

## Workstream 4: Accessibility Hardening

**Goal:** Fix the specific accessibility gaps identified in the report: focus
management, keyboard behavior, ARIA semantics, and motion preferences.

**UX report references:** Accessibility Findings, P2 (Harden Accessibility for
Dialogs, Rows, Tabs, and Motion).

### 4.1 Add focus trap and restoration to transcript slideout

**Files:** `app.js` (`openTranscript`, `closeTranscript`), `styles.css`

**Change:** The slideout has `role="dialog"` and `aria-modal="true"` but lacks focus
trap and focus restoration.

**Implementation:**
- Store `document.activeElement` before opening the slideout.
- After opening, focus the close button.
- Trap Tab/Shift+Tab within the slideout (cycle between first and last focusable
  elements).
- On close, restore focus to the previously focused element.

**Acceptance:** Opening the slideout traps focus. Tabbing cycles within the panel.
Closing restores focus to the row that opened it.

### 4.2 Add complete ARIA tab semantics and keyboard handling

**Files:** `app.js` (`renderDashboard` profile tabs), `styles.css`

**Change:** Dashboard tabs need `aria-controls`, matching panel IDs, and arrow-key
navigation per the ARIA tabs pattern.

**Implementation:**
- Add unique `id` to each tab button.
- Add `aria-controls` pointing to the tabpanel ID.
- Add `id` to the tabpanel.
- Implement left/right arrow key navigation between tabs.
- Set `tabindex="-1"` on inactive tabs, `tabindex="0"` on active tab.

**Acceptance:** Arrow keys navigate between tabs. Tab key moves focus out of the tab
list. ARIA attributes are correct and verifiable by screen readers.

### 4.3 Disable smooth scrolling in reduced-motion mode

**Files:** `styles.css`

**Change:** The reduced-motion media query should also disable smooth scrolling.

**Implementation:**
- Add `scroll-behavior: auto` inside `@media (prefers-reduced-motion: reduce)`.

**Acceptance:** Users with reduced-motion preference get instant scroll jumps.

### 4.4 Mark decorative SVGs as hidden

**Files:** `app.js` (generated HTML containing SVGs)

**Change:** Decorative SVGs in dynamically generated controls should consistently use
`aria-hidden="true"`.

**Implementation:**
- Audit all SVG generation in `app.js`.
- Add `aria-hidden="true"` to SVGs that are decorative (icons next to text labels).
- Verify SVGs that convey meaning have appropriate `aria-label` or `role="img"`.

**Acceptance:** All decorative SVGs have `aria-hidden="true"`. No SVGs silently
contribute unlabeled content to screen readers.

### 4.5 Add non-color reinforcement for score meaning

**Files:** `app.js` (`scoreBarHTML`), `styles.css`

**Change:** Color-coded scores need non-color reinforcement for users who cannot
distinguish colors.

**Implementation:**
- Add text labels or icons next to score values: a checkmark for good, a warning
  triangle for mid, an X for bad.
- For Escalation Risk specifically, ensure the inverted scale is clear through both
  color and label.

**Acceptance:** Score meaning is conveyed through both color and a secondary indicator
(icon or text).

---

## Workstream 5: Compliance Evidence

**Goal:** Make compliance findings defensible by showing thresholds, evidence counts,
audit trails, and direct links to supporting transcripts.

**UX report references:** Compliance Monitor findings, Compliance Reviewer persona,
P2 (Strengthen Compliance Evidence).

### 5.1 Show configured thresholds

**Files:** `app.js` (`renderCompliance`), `app.py` (include thresholds in
`/api/compliance/exclusions` response or add a `/api/compliance/config` endpoint)

**Change:** Users cannot see what thresholds triggered the exclusions.

**Implementation:**
- Backend: include `min_compliance_score` and `max_escalation_risk` in the compliance
  API response.
- Frontend: display thresholds at the top of the Compliance page: "Excluded when
  compliance < 80% or escalation risk > 30%."
- Show threshold lines visually in each exclusion card.

**Acceptance:** Compliance page displays the configured thresholds. Each exclusion
card shows how far the score exceeds/falls below the threshold.

### 5.2 Show evidence counts

**Files:** `app.js` (`renderCompliance`), `app.py` (include simulation count per
exclusion)

**Change:** Each exclusion should show how many simulations support the finding.

**Implementation:**
- Backend: include `simulation_count` in each exclusion object.
- Frontend: display "Based on N simulations" on each card.

**Acceptance:** Each exclusion card shows the number of supporting simulations.

### 5.3 Link exclusions to supporting transcripts

**Files:** `app.js` (`renderCompliance`), `app.py` (include sample run IDs in
exclusion response)

**Change:** There is no audit trail from exclusion to transcript evidence.

**Implementation:**
- Backend: include up to 3 representative `run_ids` per exclusion (e.g., worst
  compliance, highest escalation).
- Frontend: add "View evidence" links that open the transcript slideout for each
  sample run.

**Acceptance:** Each exclusion card has clickable links to 1-3 supporting transcripts.

### 5.4 Add coverage warnings

**Files:** `app.js` (`renderCompliance`)

**Change:** "All Clear" may be overconfident if data coverage is low.

**Implementation:**
- When exclusions are empty, display the total run count and warn if below a minimum
  threshold (e.g., < 3 runs per profile-strategy combination).
- Text: "All combinations clear across N runs. Some combinations have fewer than 3
  data points; additional runs would increase confidence."

**Acceptance:** All-clear state shows run count and warns about low-coverage
combinations.

---

## Workstream 6: UI Polish and Content Clarity

**Goal:** Address the remaining UX findings around copy, visual identity, responsive
behavior, and content pages.

**UX report references:** Theme Toggle, Responsive Behavior, Debtor Profiles,
Collector Strategies, Playbook, Visual Originality, Typography findings.

### 6.1 Add "Launch with this" actions to Profile and Strategy cards

**Files:** `app.js` (`renderProfiles`, `renderStrategies`)

**Change:** Profile and Strategy cards are read-only. Users should be able to start a
simulation directly from a card.

**Implementation:**
- Add "Run simulation" and "Compare strategies" buttons to profile cards.
- Add "Launch with this strategy" button to strategy cards.
- Buttons navigate to Launch or Matrix with the relevant selection pre-filled (via
  `navigateTo` params).

**Acceptance:** Profile and strategy cards have action buttons that navigate to the
correct launch page with selections pre-populated.

### 6.2 Add Playbook export action

**Files:** `app.js` (`renderPlaybook`)

**Change:** The Playbook page has no export or download action.

**Implementation:**
- Add an "Export Markdown" button that fetches `/api/playbook?format=markdown` and
  triggers a browser download.
- Add a "Copy to clipboard" button.

**Acceptance:** Users can download the playbook as Markdown or copy it to clipboard.

### 6.3 Add next/previous run navigation to transcript slideout

**Files:** `app.js` (`openTranscript`)

**Change:** Viewing transcripts requires closing, selecting next row, reopening. Add
inline navigation.

**Implementation:**
- Track the current run index in the filtered runs list.
- Add "Previous" and "Next" buttons to the slideout header.
- Update content without closing the slideout.

**Acceptance:** Users can navigate between runs inside the slideout without returning
to the table.

### 6.4 Improve theme toggle label clarity

**Files:** `app.js` (`toggleTheme` or theme init), `index.html`

**Change:** The toggle label is ambiguous (does it show current state or target
state?).

**Implementation:**
- Update the theme label to show "Theme: Dark" / "Theme: Light" indicating current
  state.
- Or use "Switch to light" / "Switch to dark" indicating the action.

**Acceptance:** Theme toggle clearly communicates either current state or intended
action.

### 6.5 Add performance summaries to Profile and Strategy cards

**Files:** `app.js` (`renderProfiles`, `renderStrategies`), `app.py` (new endpoints
or extend existing)

**Change:** Configuration cards do not show how each profile or strategy performs.

**Implementation:**
- Backend: add `/api/config/profiles` enrichment with average scores per profile, or
  a new endpoint.
- Frontend: show a compact score summary (average payment probability, compliance,
  run count) on each card.

**Acceptance:** Profile and strategy cards show summary performance data when
simulations exist.

### 6.6 Fix console error (Unexpected token '<')

**Files:** `app.py` (static file serving or API error responses)

**Change:** A recurring console error suggests an HTML response is being parsed as
JavaScript or JSON.

**Implementation:**
- Inspect network requests: verify all script URLs return JavaScript content-type.
- Verify API polling endpoints return JSON for both success and error cases, not HTML
  error pages.
- Add `Content-Type: application/json` headers explicitly to error responses if
  missing.

**Acceptance:** No `Unexpected token '<'` errors in the browser console during normal
operation, including during simulation launches and polling.

---

## Implementation Order

Work should proceed in this order, chosen to maximize user-facing value early while
building foundational pieces that later workstreams depend on.

| Phase | Workstream | Items | Rationale |
|-------|-----------|-------|-----------|
| 1 | WS4 (Accessibility) | 4.1-4.5 | Fixes correctness issues. Low risk, high trust. |
| 2 | WS1 (Dashboard) | 1.1-1.6 | Highest-value UX transformation. Reframes the product. |
| 3 | WS2 (Launch/Matrix) | 2.1-2.6 | Reduces cognitive load for the primary action path. |
| 4 | WS5 (Compliance) | 5.1-5.4 | Strengthens evidence and audit trail. |
| 5 | WS3 (Runs Table) | 3.1-3.6 | Power-user features for analysis workflows. |
| 6 | WS6 (Polish) | 6.1-6.6 | Final quality and content improvements. |

### Branching Strategy

Each workstream should be a separate branch and PR:

1. `cursor/accessibility-hardening` (WS4)
2. `cursor/dashboard-decisions` (WS1)
3. `cursor/launch-clarity` (WS2)
4. `cursor/compliance-evidence` (WS5)
5. `cursor/runs-analysis` (WS3)
6. `cursor/ui-polish` (WS6)

### Testing Strategy

Each workstream should include:

- **Automated:** Run existing `pytest` test suite to verify no backend regressions.
- **Manual browser testing:** Start the app with seeded data
  (`collection-swarm seed && collection-swarm serve`), then walk through the modified
  pages in both dark and light themes.
- **Accessibility verification:** Keyboard-only navigation test for WS4 changes.
  Verify focus trap, tab order, and ARIA attributes.
- **Responsive check:** Verify changes at 375px, 768px, and 1440px widths.

---

## Metrics

After all workstreams, the following UX report scores should improve:

| Heuristic | Before | Target |
|-----------|--------|--------|
| Match between system and real world | 2 | 3 |
| User control and freedom | 2 | 3 |
| Error prevention | 2 | 3 |
| Flexibility and efficiency of use | 2 | 3 |
| Aesthetic and minimalist design | 2 | 3 |
| Help users recognize, diagnose, and recover from errors | 2 | 3 |
| Help and documentation | 1 | 2 |
| **Total** | **22/40** | **28/40** |

---

## Open Questions from UX Report

These questions should be answered before or during implementation. The plan above
assumes the following defaults:

1. **Target audience:** Analysts who understand collections strategy. The UI should
   still guide first-time use, but domain terminology is acceptable.
2. **Model selection:** Advanced configuration. Defaults are pre-selected; models are
   behind a disclosure.
3. **Manual Run audience:** Internal QA. `[END_CONVERSATION]` tokens are replaced
   with UI controls.
4. **Compliance evidence level:** Threshold summary + transcript links. Exportable
   audit packets are deferred.
5. **Visual identity:** Strategy lab with evidence-based feel. Not a generic
   analytics dashboard, but not a radical departure from current design.
