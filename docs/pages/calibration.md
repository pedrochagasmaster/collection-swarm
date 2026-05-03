---
title: Judge Calibration
layout: default
nav_order: 14
---

# Judge Calibration
{: .no_toc }

Evaluating judge accuracy against human-provided scores.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Source:** `src/collection_swarm/calibration.py`

## Overview

The calibration module measures how well the Judge's automated scores align with human evaluator scores. This is critical for validating that simulation results are trustworthy and that the Judge model is producing meaningful assessments.

## Calibration Labels

### CalibrationLabel

```python
class CalibrationLabel(BaseModel):
    transcript_id: str
    human_scores: dict[str, float]
    labeler_id: str
    timestamp: datetime
```

Each label links a simulation transcript to human-assigned scores for one or more metrics. Scores must be in the range [0, 1].

### Label Format (JSON)

Calibration labels are stored as JSON files:

```json
[
  {
    "transcript_id": "sim_abc123",
    "human_scores": {
      "payment_probability": 0.7,
      "compliance_score": 0.9,
      "escalation_risk": 0.1
    },
    "labeler_id": "reviewer_1",
    "timestamp": "2026-05-01T10:00:00Z"
  }
]
```

## Evaluation Process

### evaluate_judge

```python
def evaluate_judge(
    labels: list[CalibrationLabel],
    store: SimulationStore,
) -> CalibrationResult
```

1. For each calibration label:
   - Look up the corresponding simulation run in the store.
   - Skip labels where the run doesn't exist or has no judgment.
   - For each metric in the human scores, collect the human score and the judge's score.
2. Compute per-metric statistics:
   - **Pearson correlation** — how well the judge's ranking tracks the human ranking.
   - **Mean Absolute Error (MAE)** — average magnitude of scoring disagreement.
3. Compute an **overall score** — the mean of all per-metric correlations.

### CalibrationResult

```python
class CalibrationResult(BaseModel):
    correlations: dict[str, float]
    mae: dict[str, float]
    overall_score: float
    label_count: int
```

## Pearson Correlation

```python
def pearson_correlation(xs: list[float], ys: list[float]) -> float
```

A standard implementation of Pearson's correlation coefficient:

- Returns 0.0 for empty inputs or zero variance.
- Ranges from -1.0 (perfect negative correlation) to 1.0 (perfect positive correlation).
- A score of 0.8+ indicates the judge is reliably tracking human assessments.

## Judge Prompt Variants

The calibration workflow supports **prompt optimization**:

1. Run simulations with the current judge prompt.
2. Collect human calibration labels.
3. Evaluate the judge's accuracy.
4. Use `--optimize` to save the current prompt as a scored variant.
5. Modify the judge prompt and repeat.
6. Compare variant scores to find the best prompt.

Variants are stored in the `judge_prompt_variants` table with their calibration scores.

## CLI Usage

```bash
# Evaluate judge accuracy
collection-swarm calibrate --labels calibration_labels.json

# Evaluate and save the prompt as a variant
collection-swarm calibrate --labels calibration_labels.json --optimize
```
