# `calibration.py` — Judge calibration pipeline

<span class="cs-kicker">collection_swarm/calibration.py</span>

The end-to-end Judge agreement pipeline: load human labels from JSON,
match them to stored Judgments, compute Pearson correlation and MAE per
metric, return a `CalibrationResult`.

The conceptual overview is in
[Judge calibration](../concepts/judge-calibration.md). This page is the
function-by-function reference.

<dl class="cs-summary">
  <dt>Imports</dt><dd><code>json</code>, <code>math</code>, Pydantic, the store</dd>
  <dt>Side effects</dt><dd>None directly; the store handles persistence</dd>
  <dt>Statistics</dt><dd>Pearson correlation + mean absolute error</dd>
</dl>

## Models

### `CalibrationLabel`

```python
class CalibrationLabel(BaseModel):
    transcript_id: str
    human_scores: dict[str, float]
    labeler_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

A field validator rejects any score outside `[0, 1]`. The label can
score any subset of `Judgment` metrics — sparse labels are normal.

### `CalibrationResult`

```python
class CalibrationResult(BaseModel):
    correlations: dict[str, float]
    mae: dict[str, float]
    overall_score: float
    label_count: int
```

`overall_score` is the unweighted mean of the per-metric correlations.
`label_count` is the number of labels whose `transcript_id` resolved to
a stored, judged run.

## Functions

### `load_calibration_labels(path)`

Reads a JSON file and validates each entry against `CalibrationLabel`.
Used by the CLI:

```bash
collection-swarm calibrate --labels path/to/labels.json --optimize
```

### `pearson_correlation(xs, ys)`

Standard Pearson r over two equal-length lists. Returns 0.0 when:

- The lists are different lengths or empty.
- Either list has zero variance.

The "0.0 on degenerate input" choice is deliberate: it's a useful
sentinel ("no signal") rather than a `NaN` that propagates through the
pipeline.

### `evaluate_judge(labels, store)`

The main entry point:

1. For each label, look up the run by `transcript_id`. Skip if the run
   is missing or has no `Judgment`.
2. For each metric in `human_scores` that maps to a numeric `Judgment`
   field, append the human and judge scores into a per-metric pair list.
3. After scanning every label, compute Pearson and MAE per metric.
4. Compute `overall_score` as the unweighted mean of per-metric
   correlations.

The function returns a `CalibrationResult` with the metrics, MAEs, the
overall score, and the actual label count used.

## How the CLI wires it together

```python
@cli.command("calibrate")
def calibrate(ctx, labels: Path, optimize: bool) -> None:
    config = load_app_config(ctx.obj["config_dir"])
    store = SimulationStore(ctx.obj["db_path"])
    loaded = load_calibration_labels(labels)
    store.save_calibration_labels(loaded)
    result = evaluate_judge(loaded, store)
    if optimize:
        store.save_judge_variant(
            config.prompts.judge.system,
            config.prompts.judge.transcript,
            calibration_score=result.overall_score,
        )
    console.print(f"Calibration labels: {result.label_count}; score: {result.overall_score:.2f}.")
```

`--optimize` doesn't *change* the prompts — it snapshots the current
prompts plus the score so you can compare prompt versions over time.
The dashboard exposes the same data via `GET /api/calibration/variants`.

## Why not weighted correlations

Each metric is treated equally because there is no obvious utility
function that would let you weight them. A team that cares most about
compliance can read `correlations["compliance_score"]` directly. The
overall score is a quick sanity check, not the SLA.
