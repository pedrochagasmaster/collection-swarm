# PR #5 — Production UI Polish: Implementation Plan

This plan addresses the 14 issues identified during deep review of PR #5 (`cursor/production-ui-polish-da92`). Work is organized into logical groups, ordered by priority.

---

## Group A: Accessibility Fixes (Critical)

### A1. Respect `@prefers-reduced-motion` for page transitions

**File:** `styles.css`

Add the new `page-fade-in` animation to the existing `prefers-reduced-motion` media query so it is suppressed for users who prefer reduced motion.

### A2. Add ARIA live region to toast notifications

**File:** `app.js`

Set `role="status"` and `aria-live="polite"` on the toast container so screen readers announce new toasts. Error toasts should use `aria-live="assertive"`.

### A3. Mobile sidebar: focus trap + escape key

**Files:** `app.js`, `styles.css`

- Add a `keydown` listener for `Escape` to close the sidebar when open.
- Trap focus within the sidebar while it is open (cycle focus between first and last focusable element).
- Restore focus to the hamburger button when the sidebar closes.

### A4. Restore screen-reader labels for filter selects

**File:** `app.js`

The PR removed `<label class="sr-only">` elements from the filter selects. While `aria-label` is present, the hidden `<label>` elements provide better compatibility with some assistive tech. Re-add them.

---

## Group B: UX Gaps (High)

### B1. Add overlay/backdrop for mobile sidebar

**Files:** `index.html`, `styles.css`, `app.js`

- Add a `<div class="sidebar-overlay">` element in the DOM.
- Show it (with a semi-transparent background) when the sidebar is open on mobile.
- Clicking the overlay closes the sidebar.
- Transition opacity for smooth open/close.

### B2. Limit toast stacking

**File:** `app.js`

Cap visible toasts at 3–5. When a new toast arrives and the cap is reached, dismiss the oldest toast before adding the new one. This prevents toast floods during matrix runs where many jobs complete at once.

### B3. Resilient polling with connection-lost feedback

**File:** `app.js`

Instead of silently swallowing all polling errors, track consecutive failures. After 3+ consecutive failures, show a single warning toast ("Connection interrupted — retrying..."). Clear the counter on success. This surfaces persistent issues without spamming on transient blips.

---

## Group C: CSS Fixes (Medium)

### C1. Fix disabled button cursor conflict

**File:** `styles.css`

Remove `pointer-events: none` from `.btn:disabled` so that `cursor: not-allowed` is actually visible to users. The button is already `disabled` at the HTML level, so click events are already suppressed.

### C2. Remove dead `.kbd` styles

**File:** `styles.css`

The `.kbd` class is defined but never referenced in HTML or JS. Remove it to avoid dead CSS. If keyboard shortcut hints are planned for a future PR, add the styles then.

### C3. Make spinner color adaptive

**File:** `styles.css`

Replace the hardcoded `oklch(99% 0 0)` spinner color with `currentColor` (with appropriate opacity), or scope the white spinner to `.btn-primary.btn-loading::after` only. This prevents invisible spinners if `btn-loading` is ever used on non-primary buttons.

---

## Group D: Code Cleanup (Low)

### D1. Remove dead sidebar overlay reference

**File:** `app.js`

In `toggleMobileSidebar()`, the line `const overlay = $('#slideout-overlay')` fetches an element but never uses it. Remove this dead code. (This becomes moot if B1 is implemented, since the function will then use the new sidebar overlay element.)

### D2. Remove unused `MAX_STAGGER` deletion note

No action needed — PR #5 already removes the unused `MAX_STAGGER` constant. Just noting for completeness.

---

## Group E: Structural / Process (Recommendation)

### E1. Split into smaller commits

The current PR is a single monolithic commit with ~15 distinct features. Before marking as ready for review, consider splitting into logical commits:

1. Page transitions + reduced-motion
2. Toast notification system
3. Mobile sidebar + overlay
4. Filter UX (clear button, count, highlight)
5. Button loading states
6. Config card icons
7. Compliance card restructure
8. Spacing, contrast, and copy refinements

This makes individual features easier to revert and review. Can be done via interactive rebase or by cherry-picking changes into fresh commits.

### E2. Verify WCAG contrast ratios

The dark mode contrast bumps (`--text-secondary` 64% → 66%, `--text-tertiary` 48% → 50%) should be verified against their background colors for WCAG AA compliance (4.5:1 for normal text, 3:1 for large text). Same for light mode adjustments.

---

## Implementation Order

| Step | Group | Items | Estimated Complexity |
|------|-------|-------|---------------------|
| 1 | B1 | Sidebar overlay | Small — new element + CSS + toggle logic |
| 2 | A1–A4 | All accessibility fixes | Small — mostly additive attributes and listeners |
| 3 | B2–B3 | Toast cap + poll resilience | Small — logic changes in existing functions |
| 4 | C1–C3 | CSS fixes | Trivial — single-line changes |
| 5 | D1 | Dead code cleanup | Trivial |
| 6 | E1 | Commit splitting (optional) | Medium — interactive rebase |
| 7 | E2 | Contrast verification | Small — manual check |

---

## Files Modified

All changes are scoped to 3 files:

- `src/collection_swarm/web/static/app.js`
- `src/collection_swarm/web/static/styles.css`
- `src/collection_swarm/web/static/index.html`

No backend or test files are affected.
