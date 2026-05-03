# `analysis/compliance.py` — exclusion gate

<span class="cs-kicker">collection_swarm/analysis/compliance.py</span>

The post-hoc gate that decides which (Profile, Strategy) pairs are too
risky to recommend. Two thresholds, one function, one frozen dataclass.

<dl class="cs-summary">
  <dt>Imports</dt><dd>dataclasses, the store</dd>
  <dt>Configured by</dt><dd><code>config/simulation.yaml &gt; compliance</code></dd>
</dl>

## `ComplianceExclusion`

```python
@dataclass(frozen=True)
class ComplianceExclusion:
    profile_id: str
    strategy_id: str
    compliance_score: float
    escalation_risk: float
    reason: str
```

The `reason` is a human-readable string built by
`check_exclusions`. The Playbook formats it like:

> Exclude `assertive_settlement` for `hostile_avoidant`: compliance_score 0.71 below 0.80; escalation_risk 0.45 above 0.30

## `check_exclusions(...)`

```python
def check_exclusions(
    store: SimulationStore,
    profile_ids: list[str],
    strategy_ids: list[str],
    min_compliance_score: float = 0.8,
    max_escalation_risk: float = 0.3,
) -> list[ComplianceExclusion]:
    ...
```

For every `(profile_id, strategy_id)` pair, the function:

1. Calls `store.get_compliance_summary(profile_id, strategy_id)` to get
   the mean compliance score and escalation risk for that pair across
   completed runs.
2. If both are 0.0, the pair has no data — skip it (no exclusion, no
   recommendation either).
3. Otherwise, build a list of failure reasons:
   - `compliance_score < min_compliance_score`
   - `escalation_risk > max_escalation_risk`
4. If any reasons accrue, append a `ComplianceExclusion` with the
   semicolon-joined reason.

Exclusions are pair-scoped. The same Strategy can be excluded for one
Profile and recommended for another. That's intentional: a hard tactic
might be unsafe with a hostile debtor and fine with a cooperative one.

## How thresholds get there

The CLI and the dashboard both pull the thresholds from the configured
`SimulationSettings`:

```python
exclusions = check_exclusions(
    store,
    list(config.profiles),
    list(config.strategies),
    min_compliance_score=config.simulation.min_compliance_score,
    max_escalation_risk=config.simulation.max_escalation_risk,
)
```

`config/simulation.yaml > compliance` configures both, defaulting to
`0.8` and `0.3` respectively.

## What the API exposes

`GET /api/compliance/exclusions` returns:

```json
{
  "thresholds": {
    "min_compliance_score": 0.8,
    "max_escalation_risk": 0.3
  },
  "total_completed_runs": 124,
  "minimum_runs_per_combination": 3,
  "exclusions": [
    {
      "profile_id": "hostile_avoidant",
      "strategy_id": "assertive_settlement",
      "compliance_score": 0.71,
      "escalation_risk": 0.45,
      "reason": "compliance_score 0.71 below 0.80; escalation_risk 0.45 above 0.30",
      "simulation_count": 4,
      "run_ids": ["sim_a1b2c3d4e5", ...],
      "model_pairs": [
        {"conversation_model": "...", "judge_model": "..."}
      ]
    }
  ]
}
```

The dashboard renders the table on the Compliance page and links the
`run_ids` back to their transcripts so you can see *why* a pair is
risky.
