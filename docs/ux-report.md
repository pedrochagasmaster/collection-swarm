# Collection Swarm UX Report

Date: 2026-04-30

Reviewer: Cursor Cloud agent using browser-based manual testing, source inspection, an independent design review pass, and deterministic UI pattern detection.

Test target: `http://127.0.0.1:8000`

Test data: 24 seeded simulation runs generated from `collection_swarm.web.seed.generate_seed_data`.

Walkthrough artifact: `/opt/cursor/artifacts/collection_swarm_ux_walkthrough.mp4`

## Executive Summary

Collection Swarm is a credible product dashboard for synthetic debt-collection strategy testing. The app has a strong operational foundation: the information architecture is understandable, seeded data renders clearly, asynchronous simulation progress is visible, transcript review is efficient, filters work, and dark/light theming is consistently applied.

The main UX gap is not basic usability. The gap is decision support. The interface exposes the simulator's machinery before it explains how a user should make a better collections decision. First-time users see many destinations, models, profiles, strategies, scores, outcomes, and launch options without a guided path or enough inline explanation. Power users get useful data, but lack search, sorting, export, comparison, cancellation, and saved workflows.

Recommended focus:

1. Add a guided first-run path on the dashboard.
2. Reframe the dashboard around decisions: best strategy by profile, compliance exceptions, and evidence.
3. Add context to launch selectors: summaries, default recommendations, cost/runtime estimates, and risk hints.
4. Harden accessibility and keyboard behavior around the transcript dialog, table rows, tabs, and reduced motion.
5. Upgrade run analysis workflows with sort, search, export, saved filters, and run comparison.

## Product Context

Collection Swarm is an AI-driven simulator for testing debt-collection strategies before they touch real customers. It runs synthetic conversations between three roles:

- Collector: follows a configured collection strategy.
- Debtor: follows a synthetic profile, financial situation, objection pattern, and hard constraints.
- Judge: scores the transcript for payment outcome, compliance, rapport, escalation risk, and other adoption-critical metrics.

The product helps teams answer questions such as:

- Which strategy works best for hardship profiles?
- Which approaches trigger compliance risk?
- Which model is better at role-playing debtors versus judging outcomes?
- Which transcripts should become training examples?
- How do strategy changes affect payment probability and debtor satisfaction?

This means the interface is a product UI, not a marketing surface. The highest bar is task clarity, trust, repeatability, and fast analysis.

## Methodology

### Runtime Setup

The app was launched locally with a seeded SQLite database:

- Generated 24 demo runs using `collection_swarm.web.seed.generate_seed_data`.
- Started the FastAPI app with `uvicorn` against `output/ux_report.sqlite`.
- Verified `/`, `/api/dashboard`, and `/api/runs?status=` returned successful responses.

### Browser Walkthrough

The browser walkthrough covered:

- Dashboard in dark theme.
- Simulation Runs table.
- Transcript slideout open and close behavior.
- Table filters and clear filters.
- Launch Run form and successful single simulation.
- Matrix Runs setup form.
- Manual Run setup and started session.
- Playbook page.
- Compliance Monitor.
- Debtor Profiles.
- Collector Strategies.
- Theme toggle from dark to light.
- Fullscreen and partial responsive check.

### Independent Review Inputs

Two independent review passes were used:

- Design review pass: evaluated visual hierarchy, information architecture, cognitive load, heuristic scoring, persona risks, and product fit.
- Automated/source pattern pass: inspected markup and JavaScript for accessibility risks, cognitive-load patterns, motion behavior, and deterministic design anti-patterns.

The deterministic detector was also run:

`npx impeccable --json /workspace/src/collection_swarm/web/static/index.html`

It returned two typography findings:

- Overused font: Inter.
- Single font for everything.

For a product dashboard, these are mild findings. Inter is acceptable for dense product UI, but the broader point stands: the interface looks familiar and somewhat generic.

## Test Evidence

Evidence gathered during the audit:

- Local endpoint smoke test: `/`, `/api/dashboard`, and `/api/runs?status=` returned HTTP 200 responses.
- Seeded data check: `/api/dashboard` reported 24 total runs and 24 completed runs.
- Browser walkthrough: the recorded session exercised dashboard review, run table filtering, transcript slideout behavior, a successful single-run launch, matrix setup, manual session setup, playbook, compliance, profiles, strategies, theme toggle, and a limited fullscreen responsive check.
- Video artifact: `/opt/cursor/artifacts/collection_swarm_ux_walkthrough.mp4`.
- Independent design review: produced a 22/40 Nielsen heuristic score and identified decision-support gaps as the dominant UX risk.
- Automated detector: returned two typography findings, overused font and single-font usage.
- Source inspection: found accessibility risks around dialog focus management, table row keyboard activation, tabs, SVG hiding, and reduced-motion behavior.

## Design Health Score

Scale: 0 to 4 per Nielsen heuristic. A 4 means genuinely excellent, not merely functional.

| # | Heuristic | Score | Key Issue |
|---|---|---:|---|
| 1 | Visibility of system status | 3 | Strong skeletons, toasts, progress bars, badges, and live transcripts. Long-running jobs still need cancellation and clearer failure recovery. |
| 2 | Match between system and real world | 2 | Collector, debtor, and judge concepts are clear, but labels such as Matrix Runs, Reps, model IDs, and score names need translation. |
| 3 | User control and freedom | 2 | Filters clear, Escape closes the transcript, and theme toggles work. There is no stop/cancel for queued or running jobs. |
| 4 | Consistency and standards | 3 | Shared sidebar, cards, badges, and forms are consistent. Table rows acting as buttons and custom tabs need stronger standard keyboard behavior. |
| 5 | Error prevention | 2 | Selects and min/max fields help, but launch flows do not preview cost, runtime, risk, or total run count clearly enough. |
| 6 | Recognition rather than recall | 3 | Labels are visible and navigation is explicit. Users still need to infer what profiles, strategies, and models mean before choosing. |
| 7 | Flexibility and efficiency of use | 2 | Matrix runs support batch work, but the Runs table lacks sort, search, export, saved filters, keyboard shortcuts, and comparison. |
| 8 | Aesthetic and minimalist design | 2 | Clean and usable, but metrics compete equally and the dashboard does not express a clear opinion about what matters first. |
| 9 | Help users recognize, diagnose, and recover from errors | 2 | Errors are surfaced, but recovery copy is mostly generic and does not tell users what to do next. |
| 10 | Help and documentation | 1 | No glossary, onboarding, metric definitions, compliance threshold explanation, or contextual help is visible in the UI. |
| Total |  | 22/40 | Usable foundation with meaningful decision-support and hardening work remaining. |

## AI Slop and Visual Originality Verdict

Verdict: medium risk.

The interface does not fail in an obvious way. It avoids severe anti-patterns such as gradient text, decorative glass cards, chaotic neon, and purposeless animation. It uses OKLCH tokens, semantic colors, restrained cards, clear data tables, and familiar navigation.

However, it still feels close to the standard AI-generated dashboard kit:

- Dark indigo theme.
- Inter as the primary UI font.
- Rounded cards and badges.
- Sidebar plus metric strip.
- Colorful score bars.
- Generic gradient logo.
- Similar card grids across configuration pages.

For a product UI, familiarity is often a strength, so this is not a blocker. The concern is that the visual language does not yet express the product's specific domain: synthetic collections strategy, compliance risk, and evidence-based call policy decisions. The interface could feel more like a strategy lab and less like a generic analytics dashboard.

## Cognitive Load Assessment

Overall cognitive load: moderate-high.

The app is understandable after exploration, but it asks a new user to make too many choices before explaining the intended workflow.

Observed load drivers:

- Sidebar exposes 9 destinations.
- Overview section alone contains 5 navigation choices.
- Dashboard top strip exposes 6 metrics.
- Average Scores exposes 5 core metrics plus ranking metrics.
- Runs table exposes 10 columns.
- Launch Run asks for profile, strategy, conversation model, and judge model.
- Matrix Runs adds multi-select profiles, multi-select strategies, reps, and concurrency.
- Manual Run adds role selection and manual termination syntax.

The product's domain is inherently complex, but the UI can reveal complexity more progressively.

Recommended cognitive-load changes:

- Add a dashboard "Start here" module for first-time use.
- Put recommended defaults and explanations directly beside selectors.
- Collapse advanced model controls behind an "Advanced" disclosure.
- Rename Matrix Runs to Batch Comparison or Strategy Matrix, depending on product language.
- Define each score inline on first exposure.
- Treat compliance exceptions as a first-class path, not a secondary page.

## Page-by-Page Findings

### Dashboard

What works:

- The dashboard loads into a rich, non-empty state with clear metrics and charts.
- The top strip communicates operational summary quickly: runs, completed, failed, success, cost, and tokens.
- Average score bars are readable and use consistent meter-like visual language.
- Outcome distribution gives a useful scan of result categories.
- Strategy ranking by profile is a valuable decision surface.

Issues:

- Every metric appears to have similar importance. The user is not told which finding deserves action.
- Cost and token counts appear alongside outcome and compliance metrics, but they serve different decision modes.
- Strategy Rankings is lower on the page even though it may be the highest-value insight.
- First-time users are not guided to run a demo, compare strategies, or inspect compliance.
- Escalation Risk is a lower-is-better metric shown visually beside higher-is-better metrics, which can confuse interpretation.

Recommended changes:

- Lead with "Best strategy by profile" and "Compliance exceptions requiring review."
- Move operational metrics into a secondary strip or collapsible details area.
- Add brief metric definitions or tooltips.
- Add a first-run panel when data is empty or when the user has not launched a run in the current session.
- Invert or relabel escalation risk as "Escalation safety" if using the same good/mid/bad visual treatment as other positive scores.

### Simulation Runs

What works:

- The table is readable at desktop size.
- Status, outcome, payment, and compliance are scannable.
- Filters apply immediately.
- The result count updates after filtering.
- Clear filters appears when filters are active.
- Clicking a row opens a transcript without navigating away from the table.

Issues:

- The table is dense and lacks sorting.
- There is no search by run ID, profile, strategy, outcome, or transcript content.
- There is no export or share action.
- Rows act as buttons but only Enter key activation was found in source, not Space.
- The table uses a horizontal scroll container, but small-screen usability was not fully verified.
- Active filters are only visible through dropdown state and the Clear filters button. Filter chips would scan faster.

Recommended changes:

- Add sortable headers.
- Add a search field.
- Add export CSV or copy link actions.
- Add filter chips for active filters.
- Add multi-select compare mode.
- Support both Enter and Space activation for row buttons, or use actual button/link elements inside the table.

### Transcript Slideout

What works:

- The slideout is one of the strongest UX patterns in the app.
- It preserves table context.
- It shows run metadata, transcript messages, and judgment details together.
- Escape closes the slideout in browser testing.
- The close button also works.

Issues:

- Source inspection did not show a focus trap.
- Source inspection did not show focus restoration to the previously focused row after close.
- The dialog has `role="dialog"` and `aria-modal="true"`, but needs stronger complete dialog behavior.
- There is no next/previous run navigation inside the slideout.
- Long transcripts may need better internal navigation, anchors, or summary.

Recommended changes:

- Store the opener before opening and restore focus on close.
- Trap focus while the slideout is open.
- Add Space and Enter support where relevant.
- Add next/previous run controls.
- Add a transcript summary or "jump to judgment" affordance for long transcripts.

### Launch Run

What works:

- The form is simple and vertically organized.
- Defaults are filled in.
- Starting a simulation gives immediate feedback.
- Live progress and transcript generation are engaging and clear.
- Completion gives useful next actions: View latest run and All runs.

Issues:

- Select options are IDs only. Users do not get enough context to choose well.
- There is no estimated runtime or cost preview.
- There is no risk hint for strategy/profile combinations.
- Advanced model selection is exposed to all users, even when local defaults are likely sufficient.
- There is no cancellation once the job starts.

Recommended changes:

- Add short descriptions below selected profile and strategy.
- Add recommendation badges such as Recommended, Risky, Good for hardship, or Requires validation.
- Move model selectors into Advanced settings.
- Add estimated turns, runtime, and cost.
- Add cancel job action while queued or running.

### Matrix Runs

What works:

- The form is visually organized.
- Profile and strategy checkboxes are readable.
- Defaults produce a reasonable 12-run matrix with the seeded configuration.
- Reps and concurrency are explicit.

Issues:

- "Matrix Runs" and "Reps" are technically accurate but intimidating.
- Total run count is not prominent enough before launch.
- Cost/runtime implications are not previewed.
- There is no saved preset for common comparisons.
- There is no guardrail for very large matrices.

Recommended changes:

- Rename or subtitle the page as "Batch comparison."
- Show a live calculation: profiles x strategies x models x reps = total simulations.
- Add estimated runtime and cost.
- Warn before launching large or expensive matrices.
- Offer presets: Compare all strategies for one profile, Compare top two strategies, Full strategy audit.

### Manual Run

What works:

- The setup form is clear.
- The role choice is easy to understand.
- Starting a session produces an immediate collector message.
- The transcript panel and status badge orient the user.

Issues:

- The textarea placeholder exposes `[END_CONVERSATION]`, which is implementation syntax.
- "Finish and judge" is visible, but the stop instruction still teaches users an internal token.
- There is no guidance about what a good manual test should try to validate.
- Manual role-play could benefit from scripted prompts or scenario goals.

Recommended changes:

- Replace the token instruction with a visible "End conversation" button or checkbox.
- Add scenario goal text, such as "Try to test hardship negotiation under a strict $150/month constraint."
- Add role guidance based on selected profile.
- Add a confirmation before judging if the transcript is very short.

### Playbook

What works:

- The Playbook is one of the product's most valuable outputs.
- It includes compliance notice, analyzed simulation count, profile recommendations, and strategy ranking tables.
- The generated Markdown-to-HTML rendering is readable.

Issues:

- It appears as a static report, with limited interactive affordances.
- Recommendations need more evidence links back to underlying runs.
- Compliance exclusions are present, but could be visually stronger and more traceable.
- There is no export/download action visible in the UI.

Recommended changes:

- Add "View evidence" links from recommendations to representative transcripts.
- Add export Markdown/PDF/copy actions.
- Add filters by profile, strategy, and risk category.
- Add generated-at and data coverage details near the top.

### Compliance Monitor

What works:

- Red warning cards communicate risk clearly.
- Each card identifies the strategy/profile combination.
- Compliance and escalation values are visible.
- Reasons are written in plain language.

Issues:

- Thresholds are not visible.
- Evidence count is not visible.
- There is no audit trail or link to supporting transcripts.
- The "All Clear" state may be overconfident if data coverage is low.

Recommended changes:

- Show configured thresholds.
- Show number of runs supporting each exclusion.
- Link each exclusion to sample transcripts and judge reasoning.
- Add coverage warnings when combinations have insufficient runs.
- Consider severity levels instead of a single red-card treatment.

### Debtor Profiles

What works:

- Cards expose detailed attributes.
- Backstory text gives needed domain context.
- Constraints are visible and visually separated.
- The three profile cards are easy to compare at a high level.

Issues:

- Dense card content may be hard to scan quickly.
- Constraints are important enough to be elevated.
- There is no direct "run this profile" action from the card.
- There is no performance summary per profile.

Recommended changes:

- Move constraints closer to the card header.
- Add "Run simulation" and "Compare strategies" actions.
- Add latest performance summary for each profile.
- Add tags for objection, responsiveness, and risk.

### Collector Strategies

What works:

- Strategy cards are consistent.
- Core strategy attributes are visible.
- The grid is clean and readable.

Issues:

- Strategy cards do not show performance outcomes.
- There is no "best for" or "risky for" guidance.
- There is no direct action to test or compare a strategy.

Recommended changes:

- Add performance summary per strategy.
- Add risk badges by profile.
- Add "Launch with this strategy" and "Compare this strategy" actions.
- Show sample opening or negotiation behavior for each strategy.

### Theme Toggle

What works:

- Dark and light themes are both readable.
- Theme changes apply consistently across the app.
- Badges and score bars remain legible in both modes.

Issues:

- The toggle label can be ambiguous because it reflects the target or current state depending on user interpretation.
- No issue was found severe enough to prioritize here.

Recommended changes:

- Consider labeling the toggle as "Theme: Dark" or "Switch to light" to remove ambiguity.

### Responsive Behavior

What was verified:

- Desktop layout works.
- Fullscreen layout works.
- Source inspection shows responsive CSS at max-width 768px for fixed sidebar, open state, and mobile menu display.

What was not fully verified:

- A true narrow mobile viewport, such as 375px wide, was not successfully tested in browser tooling.

Risks:

- The Runs table may be cramped on mobile.
- Sidebar drawer focus behavior should be checked.
- Form density in Matrix Runs may need mobile-specific restructuring.

Recommended changes:

- Run a dedicated mobile pass at 375px, 390px, 768px, and 1024px.
- Verify mobile drawer focus behavior and Escape handling.
- Convert dense tables to card rows or priority columns on small screens.

## Accessibility Findings

Positive findings:

- Main navigation uses labels and active state.
- The main content area has `role="main"`.
- The transcript slideout uses `role="dialog"` and `aria-modal="true"`.
- The close button has an accessible label.
- Focus-visible styles are defined.
- Toasts use live regions.
- Score bars use meter semantics.

Issues to fix:

1. Transcript slideout focus trap and restoration.
2. Table row keyboard activation should support Space, not just Enter.
3. Tabs should include `aria-controls`, matching panel labels, and arrow-key behavior.
4. Decorative SVGs in generated controls should consistently use `aria-hidden="true"`.
5. Reduced-motion mode should also disable smooth scrolling.
6. Color-coded score meaning needs non-color reinforcement, especially for escalation risk.

## Technical UX Notes

### Console Error

During browser testing, a recurring console error was visible:

`Uncaught SyntaxError: Unexpected token '<'`

It did not block the tested flows, including launching and completing a simulation, but it is a technical health concern. This type of error often indicates that JavaScript tried to parse HTML as JavaScript or JSON, or that an asset/API request returned an unexpected HTML response.

Recommended investigation:

- Inspect network requests around app load and after simulation launch.
- Confirm all script URLs return JavaScript, not HTML.
- Confirm polling endpoints return JSON for success and error cases.
- Add user-facing recovery states for polling failures.

### Detector Findings

The deterministic detector flagged:

- Overused font: Inter.
- Single font for everything.

Assessment:

- In a dense product UI, Inter and a single family are not inherently wrong.
- This is a low-severity visual distinctiveness issue, not a usability blocker.
- If the team wants more brand character, consider a more distinctive heading or mono data treatment while preserving UI readability.

## Persona Red Flags

### First-Time Strategy Analyst

Goal: understand what to do first and produce a useful strategy recommendation.

Red flags:

- No start-here path.
- Too many navigation choices before workflow explanation.
- Profile and strategy selectors lack summaries.
- Score meanings are not defined in context.
- Matrix Runs may sound technical rather than task-oriented.

### Power User or Operations Analyst

Goal: run many simulations, compare results quickly, and export/share findings.

Red flags:

- No sortable table columns.
- No search.
- No export.
- No saved filters or presets.
- No multi-run compare.
- No job cancellation.

### Compliance or Risk Reviewer

Goal: defend exclusions and prove recommendations are safe.

Red flags:

- Compliance thresholds are hidden.
- Evidence counts are hidden.
- Exclusions do not link directly to transcripts.
- "All Clear" could imply certainty without showing coverage.
- Judge reasoning is not packaged as an audit trail.

### Accessibility-Dependent Keyboard User

Goal: navigate runs, inspect transcripts, and close overlays without losing context.

Red flags:

- Table rows need standard keyboard activation.
- Dialog focus trap/restoration is not clearly implemented.
- Tabs need standard arrow-key behavior.
- Reduced-motion support misses smooth scrolling.

## Priority Issues

The highest-impact issues are:

1. First-time users do not get a guided path through the product's core workflow.
2. The dashboard summarizes activity, but does not clearly prioritize strategic decisions.
3. Launch and matrix controls ask users to choose profiles, strategies, models, reps, and concurrency without enough context.
4. Transcript dialog, table row, tab, and reduced-motion behavior need accessibility hardening.
5. Runs analysis lacks the expected power-user tools: search, sort, export, saved filters, and comparison.
6. Compliance findings need stronger evidence, thresholds, and audit trail links.

## Severity-Ranked Recommendations

### P1: Add Guided First-Run Experience

Why it matters:

The product is useful but complex. A user should not have to infer whether to inspect profiles, launch one run, start a matrix, or read the playbook first.

Fix:

- Add a dashboard panel with three recommended actions:
  - Run recommended demo.
  - Compare all strategies for one profile.
  - Review compliance risks.
- Explain what each action produces.
- Hide or de-emphasize advanced model settings until needed.

Suggested implementation command:

`$impeccable onboard dashboard`

### P1: Reframe Dashboard Around Decisions

Why it matters:

The current dashboard summarizes activity well, but it does not strongly answer the product's core question: what strategy should we use, and what should we avoid?

Fix:

- Put best strategy by profile near the top.
- Put compliance exceptions near the top.
- Add confidence or evidence counts.
- Move tokens and cost to an operational details area.
- Clarify escalation risk direction.

Suggested implementation command:

`$impeccable layout dashboard`

### P1: Add Context to Launch and Matrix Controls

Why it matters:

Launching a run is the key action. Users need to understand the selected profile, strategy, model, risk, and expected cost before they start.

Fix:

- Add selected profile summary.
- Add selected strategy summary.
- Add estimated run count, runtime, and cost.
- Add risk hints for known problematic combinations.
- Add a large-matrix warning.
- Move model selection behind Advanced.

Suggested implementation command:

`$impeccable clarify launch and matrix`

### P2: Harden Accessibility for Dialogs, Rows, Tabs, and Motion

Why it matters:

The app is close to accessible, but a few standard interaction gaps can make it unreliable for keyboard and assistive technology users.

Fix:

- Add focus trap and restoration to transcript slideout.
- Support Space on table row activation or use proper button/link controls.
- Add complete ARIA tab semantics and keyboard handling.
- Disable smooth scrolling in reduced-motion mode.
- Mark decorative SVGs as hidden.

Suggested implementation command:

`$impeccable harden accessibility`

### P2: Upgrade Runs Table for Analysis Workflows

Why it matters:

The Runs page is where users validate evidence. Without search, sort, export, and compare, users hit a ceiling quickly.

Fix:

- Sortable columns.
- Search.
- Export CSV.
- Active filter chips.
- Saved filters.
- Compare selected runs.

Suggested implementation command:

`$impeccable polish runs table`

### P2: Strengthen Compliance Evidence

Why it matters:

Compliance users need defensible explanations, not just warnings.

Fix:

- Show thresholds.
- Show evidence counts.
- Link cards to supporting transcripts.
- Add coverage warnings.
- Include sample violation excerpts where available.

Suggested implementation command:

`$impeccable harden compliance monitor`

## Recommended Roadmap

Recommended order:

1. `onboard`: add dashboard first-run guidance and empty-state workflow prompts.
2. `layout`: reprioritize the dashboard around recommendations and risk.
3. `clarify`: rewrite launch, matrix, manual, and score copy.
4. `harden`: fix accessibility, motion, dialog, and error recovery gaps.
5. `polish`: add power-user affordances to the Runs page.

## Open Questions

1. Should Collection Swarm optimize for analysts who already understand collections strategy, or for non-technical stakeholders who need guided interpretation?
2. Should model selection be a primary control, or should it be advanced configuration?
3. Is Manual Run intended for internal QA users, or for broader product users? The answer determines whether implementation tokens like `[END_CONVERSATION]` are acceptable.
4. What level of compliance evidence is required for a recommendation to be trusted: threshold summary, transcript examples, judge reasoning, or exportable audit packet?
5. Should the product's visual identity remain a neutral analytics dashboard, or should it more strongly evoke a simulation lab or risk review workspace?

## Final Assessment

Collection Swarm is already usable and has several strong product moments, especially the live simulation feedback and transcript slideout. The highest-value UX work is to make the product more opinionated: guide the first run, expose why a strategy wins, show why a strategy is risky, and connect every recommendation back to evidence.

The interface should help users move from "I can run simulations" to "I know which strategy to use, which strategy to avoid, and why."
