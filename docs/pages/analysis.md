---
title: Analysis Pipeline
layout: default
nav_order: 10
---

# Analysis Pipeline
{: .no_toc }

Statistics, compliance checks, objection extraction, and playbook generation.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Source:** `src/collection_swarm/analysis/`

## Overview

The analysis package processes simulation results into actionable insights. It has four modules that work together to produce the final playbook:

```
SimulationStore
      │
      ├── statistics.py  →  StrategyRanking (per profile)
      ├── compliance.py  →  ComplianceExclusion list
      ├── objections.py  →  ObjectionReport
      └── playbook.py    →  Markdown playbook output
```

---

## Statistics Module

**Source:** `src/collection_swarm/analysis/statistics.py`

### StrategyRanking

```python
@dataclass(frozen=True)
class StrategyRanking:
    profile_id: str
    strategies: list[StrategyStats]

    @property
    def recommended_strategy_id(self) -> str | None
```

The recommended strategy is the first in the list (ordered by mean payment probability descending).

### compare_strategies

```python
def compare_strategies(profile_id: str, store: SimulationStore) -> StrategyRanking
```

Queries the store for aggregated strategy performance for a specific profile. Returns a `StrategyRanking` with strategies sorted by mean payment probability (highest first).

The underlying SQL query groups completed runs by `(profile_id, strategy_id)` and computes:
- `simulation_count` — number of completed simulations
- `mean_payment_probability` — average across all runs
- `mean_compliance_score` — average compliance
- `mean_escalation_risk` — average escalation risk

---

## Compliance Module

**Source:** `src/collection_swarm/analysis/compliance.py`

### ComplianceExclusion

```python
@dataclass(frozen=True)
class ComplianceExclusion:
    profile_id: str
    strategy_id: str
    compliance_score: float
    escalation_risk: float
    reason: str
```

### check_exclusions

```python
def check_exclusions(
    store: SimulationStore,
    profile_ids: list[str],
    strategy_ids: list[str],
    min_compliance_score: float = 0.8,
    max_escalation_risk: float = 0.3,
) -> list[ComplianceExclusion]
```

Iterates over every profile-strategy combination and checks average metrics against thresholds:

1. Query `get_compliance_summary()` for average `compliance_score` and `escalation_risk`.
2. Skip combinations with no data (both values are 0.0).
3. Flag combinations where:
   - `compliance_score < min_compliance_score` (default: 0.8)
   - `escalation_risk > max_escalation_risk` (default: 0.3)

Each exclusion includes a human-readable reason explaining which threshold was violated.

### Usage in Production

Compliance exclusions serve as **guardrails**: strategies that fail compliance checks should not be deployed for those profile types. The playbook prominently lists all exclusions at the top.

---

## Objections Module

**Source:** `src/collection_swarm/analysis/objections.py`

### ObjectionReport

```python
class ObjectionReport(BaseModel):
    objections: dict[str, int]
```

Maps objection category names to their occurrence count across transcripts.

### extract_objections

```python
def extract_objections(
    transcripts: list[list[Message]],
    taxonomy: list[str] | None = None,
) -> ObjectionReport
```

Scans debtor messages across all transcripts for keyword matches against a predefined objection taxonomy:

| Category | Keywords |
|:---------|:---------|
| `inability_to_pay` | "can't afford", "cannot pay", "hardship", "tough spot" |
| `disputes_debt` | "not mine", "dispute", "don't owe" |
| `wants_written_proof` | "written proof", "written validation", "validate" |
| `avoidance` | "call back", "not now", "later" |
| `emotional_distress` | "tired", "angry", "stress" |

The `taxonomy` parameter can filter to a subset of categories (defaults to all).

**Counting logic:** Each transcript is counted at most once per category. If any keyword for a category appears in the debtor's combined text, that category gets +1.

---

## Playbook Module

**Source:** `src/collection_swarm/analysis/playbook.py`

### generate_playbook

```python
def generate_playbook(
    rankings: list[StrategyRanking],
    exclusions: list[ComplianceExclusion],
    store: SimulationStore,
) -> str
```

Generates a comprehensive Markdown document with the following sections:

#### 1. Header

```markdown
# Collection Playbook
Generated: 2026-05-03T10:30:00+00:00 | Simulations analyzed: 142
```

#### 2. Compliance Notice

Lists all compliance exclusions. If none, states "No compliance exclusions detected."

```markdown
## Compliance Notice
- Exclude `assertive_settlement` for `hostile_avoidant`: compliance=0.65, escalation_risk=0.45
```

#### 3. Per-Profile Sections

For each profile with simulation data:

**Recommended strategy** — The top-ranked strategy with its mean payment probability.

**Strategy ranking table** — All strategies sorted by performance:

```markdown
| Strategy | Simulations | Payment Probability | Compliance | Escalation Risk |
|---|---:|---:|---:|---:|
| `empathetic_payment_plan` | 12 | 72% | 95% | 8% |
```

**Objection playbook** — Objection categories observed in transcripts for the recommended strategy:

```markdown
### Objection Playbook
- **inability_to_pay:** observed in 8 transcript(s).
- **wants_written_proof:** observed in 3 transcript(s).
```

**Example transcript** — The best-performing transcript (highest payment probability, then compliance) formatted as blockquotes:

```markdown
### Example Transcript
> **Collector:** Olá, aqui é Alex falando em nome do liquidante...
> **Debtor:** Tô numa fase apertada, mas consigo segurar uma parcela...
```

### Integration with Web Dashboard

The web dashboard renders playbooks using `_render_safe_markdown()`, which converts Markdown to HTML and sanitizes it with Bleach to prevent XSS attacks from YAML-injected content.
