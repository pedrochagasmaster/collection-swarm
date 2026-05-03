# `analysis/playbook.py` — Markdown report generator

<span class="cs-kicker">collection_swarm/analysis/playbook.py</span>

The end-to-end Playbook composer. Pulls strategy rankings, compliance
exclusions, objection counts, and the best-scoring transcript per
(Profile, Strategy) pair into one Markdown document.

<dl class="cs-summary">
  <dt>Imports</dt><dd>standard library, the analysis siblings, the store</dd>
  <dt>Side effects</dt><dd>None — returns a string</dd>
</dl>

## `generate_playbook(rankings, exclusions, store)`

```python
def generate_playbook(
    rankings: list[StrategyRanking],
    exclusions: list[ComplianceExclusion],
    store: SimulationStore,
) -> str: ...
```

The function builds the Playbook section by section:

1. **Header.** Generation timestamp and total simulations analyzed (from
   `store.list_runs(status="completed")`).
2. **Compliance Notice.** Lists every exclusion as
   `Exclude `strategy_id` for `profile_id`: compliance=…, escalation_risk=…`,
   or "No compliance exclusions detected." if the list is empty.
3. **Per-Profile sections.** For each `StrategyRanking`:
   - If the ranking has no strategies, write "No completed simulations."
     and continue.
   - Otherwise:
     - Recommended Strategy line with the top strategy and its mean
       payment probability.
     - Strategy Ranking table with one row per strategy.
     - Objection Playbook section (only if `extract_objections` returned
       any categories) listing each category with its transcript count.
     - Example Transcript section quoting the best-scoring transcript.

The result is one Markdown string with no trailing newline (the function
appends a final empty string then joins on `"\n"`).

## What the Playbook looks like

A skeleton:

```markdown
# Collection Playbook

Generated: 2026-05-03T10:39:00+00:00 | Simulations analyzed: 124

## Compliance Notice
- Exclude `assertive_settlement` for `hostile_avoidant`: compliance=0.71, escalation_risk=0.45

## Profile: cooperative_hardship
### Recommended Strategy: `empathetic_payment_plan`
**Payment Probability:** 78%

### Strategy Ranking
| Strategy | Simulations | Payment Probability | Compliance | Escalation Risk |
|---|---:|---:|---:|---:|
| `empathetic_payment_plan` | 12 | 78% | 95% | 8% |
| `problem_solving_callback` | 9 | 71% | 94% | 6% |
| ...

### Objection Playbook
- **inability_to_pay:** observed in 7 transcript(s).
- **wants_written_proof:** observed in 2 transcript(s).

### Example Transcript
> **Collector:** Olá, aqui é Alex falando em nome do liquidante…
> **Debtor:** Tô numa fase apertada…
> **Collector:** Combinado. Vou registrar o acordo por boleto oficial…
```

## How the dashboard renders it

The `/api/playbook` endpoint calls `generate_playbook(...)` and then
runs the result through `_render_safe_markdown(md_text)` (see
[`web/app.py`](../web/app.md)) which:

1. Renders Markdown with `markdown.markdown(md_text, extensions=["tables", "fenced_code"])`.
2. Sanitizes the resulting HTML with `bleach.clean`, allow-listing a
   tight set of tags (`p`, `h1`–`h6`, `ul`/`ol`/`li`, `table`/`tr`/`th`/`td`,
   `code`, `pre`, `blockquote`, `strong`, `em`, `a`, `br`, `hr`, `span`,
   `div`) and a tight set of attributes.

The sanitization step is load-bearing: the Markdown library does not
strip raw HTML by default, so a Strategy or transcript with embedded
`<script>` would otherwise execute when the dashboard injected the
HTML via `innerHTML`. Bleach removes any tag outside the allow-list
and any attribute outside the per-tag allow-list.

## Why a Markdown intermediate

Two reasons:

- The CLI writes Markdown to disk (`output/playbook.md`) and the
  dashboard renders Markdown to HTML; sharing a Markdown intermediate
  means both surfaces show the same content.
- Markdown round-trips cleanly through diff tools, code review, and
  LLM context windows. Generated Playbooks are easy to compare across
  runs.
