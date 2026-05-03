---
title: Model Evaluation
layout: default
nav_order: 15
---

# Model-Role Evaluation
{: .no_toc }

Probing multiple LLMs for role fitness across collector, debtor, and judge.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Source:** `src/collection_swarm/model_evaluation.py`

## Overview

The model evaluation module answers the question: **which LLM works best for each role?** It probes multiple models as collector, debtor, and judge, then scores their fitness using deterministic rubrics.

The module is intentionally separate from the web UI so the same logic powers CLI reports, CI checks, and future dashboard views.

## Key Data Structures

### ProbeScenario

Defines the inputs used to exercise each model:

```python
@dataclass(frozen=True)
class ProbeScenario:
    profile_id: str = "cooperative_hardship"
    strategy_id: str = "empathetic_payment_plan"
    judge_profile_id: str = "written_proof_disputer"
    debtor_prompt: str = "..."
    judge_transcript: tuple[Message, ...] = (...)
```

### RoleProbe

Raw output from a single model-role test:

| Field | Description |
|:------|:------------|
| `model_name` | Provider-facing model identifier |
| `role` | collector, debtor, or judge |
| `status` | "ok" or "error" |
| `elapsed_s` | Time taken |
| `content` | Generated text (collector/debtor) |
| `judgment` | Parsed Judgment (judge only) |
| `error` | Error message if failed |

### RoleAssessment

Scored fit evaluation derived from a probe:

| Field | Description |
|:------|:------------|
| `model_name` | Model identifier |
| `role` | Role tested |
| `score` | 1–10 fit score |
| `fit` | Human-readable fit label |
| `evidence` | What the model did well |
| `caution` | Concerns or issues |

### ModelRoleReport

Complete evaluation report containing probes, assessments, config health checks, and recommendations.

## Scoring Rubrics

### Collector Scoring (base: 5)

| Criterion | Score Change | Detection |
|:----------|:-------------|:----------|
| Identified account purpose | +1 | Keywords: "attempt to collect", "balance", etc. |
| Included account detail | +1 | Contains "$" or "balance" |
| Used empathetic framing | +1 | Keywords: "stress", "understand", "manageable" |
| Leaked placeholders | -2 | Contains "[agency" or "[collector" |
| Awkward identification | -2 | Contains "this is calling" |

### Debtor Scoring (base: 6)

| Criterion | Score Change | Detection |
|:----------|:-------------|:----------|
| Stayed in hardship persona | +1 | Keywords: "rent", "hours", "family", "tight" |
| Honored payment ceiling | +1 | Payment amount ≤ $150 |
| Realistic consumer voice | +1 | Words: "maybe", "probably", "honestly" |
| Markdown formatting leaked | -1 | Contains "**" |

### Judge Scoring

| Criterion | Score | Description |
|:----------|:------|:------------|
| No judgment produced | 1 | Probe failed |
| Parse fallback triggered | 3 | Judge returned unparseable JSON |
| Parseable + false violations | 6-1 = 5 | Invented constraint violations |
| Parseable + no false violations | 6+2 = 8 | Clean judgment |
| Aligned scores | +1 | High compliance, low escalation |
| Reasonable payment probability | +1 | 0–0.5 range for this scenario |

### Fit Labels

| Score Range | Label |
|:-----------|:------|
| 9–10 | Primary recommendation |
| 7–8 | Strong candidate |
| 5–6 | Usable with caution |
| 1–4 | Avoid for now |

## Live Probing

### run_live_role_probes

```python
async def run_live_role_probes(
    config: AppConfig,
    cursor_model_names: tuple[str, ...] = DEFAULT_CURSOR_PROBE_MODELS,
    roles: tuple[EvaluationRole, ...] = ("collector", "debtor", "judge"),
    scenario: ProbeScenario | None = None,
    concurrency: int = 1,
) -> tuple[RoleProbe, ...]
```

1. Creates temporary `ModelConfig` entries for each Cursor SDK model being probed.
2. Builds a probe-specific router with these models registered.
3. For each `(model, role)` combination, runs the appropriate agent/judge.
4. Respects concurrency limits via asyncio semaphore.

### What Each Role Probe Does

| Role | Agent Used | Input |
|:-----|:-----------|:------|
| Collector | `CollectorAgent.generate_turn()` | Strategy + empty history |
| Debtor | `DebtorAgent.generate_turn()` | Profile + one collector prompt |
| Judge | `Judge.evaluate()` | Fixed 4-turn transcript |

## Baseline Probes

The module includes **checked-in baseline probe data** from April 30, 2026 covering 9 models × 3 roles = 27 probes. These baselines are used when `--live-probes` is not specified.

## Configuration Health

### configured_cursor_model_statuses

Compares configured Cursor SDK model names against known valid model IDs:

| Status | Meaning | Action |
|:-------|:--------|:-------|
| `works` | Model name is in the known-valid list | Keep |
| `fails` | Model name has a known replacement | Replace with suggested ID |
| `unknown` | Model name not recognized | Verify manually |

### Model Name Replacements

The module maps deprecated model names to their current equivalents:

| Old Name | Replacement |
|:---------|:------------|
| `gpt-5.5-medium` | `gpt-5.5` |
| `gpt-5.4-high` | `gpt-5.4` |
| `gpt-5.4-high-fast` | `gpt-5.4-mini` |
| `claude-4.6-opus-high-thinking` | `claude-opus-4-6` |
| `claude-opus-4-7-thinking-high` | `claude-opus-4-7` |

## Report Output

### Markdown Report

Generated by `render_markdown_report()`:

1. **Executive Recommendation** — Best model per role.
2. **Configuration Health** — Table of configured model statuses.
3. **Role Assessments** — Per-role tables with scores, fit labels, evidence, and cautions.
4. **Probe Scenario** — Input parameters used.
5. **Operational Notes** — Caveats and usage guidance.

### JSON Report

Generated by `report_to_dict()` — structured data suitable for CI/CD processing.

## CLI Usage

```bash
# Offline report using baseline probes
collection-swarm model-report

# Live probes against Cursor SDK models
collection-swarm model-report --live-probes

# Specific models and roles
collection-swarm model-report \
  --live-probes \
  --cursor-models gpt-5.5,claude-opus-4-7 \
  --roles collector,judge

# JSON output for automation
collection-swarm model-report --format json --output output/report.json
```
