# Model Evaluation Module

`collection_swarm.model_evaluation` turns Cursor SDK model probes into a repeatable role-fit report for Collection Swarm.

The module evaluates models separately for the three production roles:

- **Collector**: generates compliant, account-aware collection turns.
- **Debtor**: stays in Profile persona and respects hard Constraints.
- **Judge**: returns parseable, calibrated Judgments without inventing Constraint Violations.

## Quick Start

Generate the checked-in baseline report:

```bash
collection-swarm model-report --output docs/cursor-model-role-report.md
```

Generate JSON instead of Markdown:

```bash
collection-swarm model-report \
  --format json \
  --output output/cursor-model-role-report.json
```

Run live Cursor SDK probes:

```bash
collection-swarm model-report \
  --live-probes \
  --cursor-models gpt-5.5,claude-opus-4-7,claude-sonnet-4-6 \
  --roles collector,debtor,judge \
  --profile cooperative_hardship \
  --strategy empathetic_payment_plan \
  --judge-profile written_proof_disputer \
  --concurrency 1 \
  --output output/live-model-role-report.md
```

Live probes require:

- `CURSOR_API_KEY`
- Node.js 22+
- `npm install` in `cursor_sdk_bridge/`

## Python API

```python
from pathlib import Path

from collection_swarm.config import load_app_config
from collection_swarm.model_evaluation import (
    ProbeScenario,
    build_model_role_report,
    run_live_role_probes,
    write_report,
)

config = load_app_config("config")
scenario = ProbeScenario(
    profile_id="cooperative_hardship",
    strategy_id="empathetic_payment_plan",
    judge_profile_id="written_proof_disputer",
)

# Deterministic baseline report.
report = build_model_role_report(config, scenario=scenario)
write_report(report, Path("docs/cursor-model-role-report.md"))
```

Live probe usage:

```python
import asyncio
from pathlib import Path

from collection_swarm.config import load_app_config
from collection_swarm.model_evaluation import build_model_role_report, run_live_role_probes, write_report

config = load_app_config("config")
probes = asyncio.run(
    run_live_role_probes(
        config,
        cursor_model_names=("gpt-5.5", "claude-opus-4-7"),
        roles=("collector", "debtor", "judge"),
        concurrency=1,
    )
)
report = build_model_role_report(config, probes=probes)
write_report(report, Path("output/live-model-role-report.md"))
```

## Parameters

`ProbeScenario` controls the evaluation prompts:

- `profile_id`: Profile used by Collector and Debtor probes.
- `strategy_id`: Strategy used by Collector probes.
- `judge_profile_id`: Profile used by Judge probes.
- `debtor_prompt`: Collector message used to start a Debtor probe.
- `judge_transcript`: Transcript used to test Judge output quality.

`run_live_role_probes` controls model execution:

- `cursor_model_names`: provider-facing Cursor SDK model IDs, such as `gpt-5.5`.
- `roles`: subset of `collector`, `debtor`, and `judge`.
- `concurrency`: maximum concurrent SDK probes.

## Interpretation

The baseline report is a snapshot from one-shot live probes. It is useful for:

- catching stale Cursor SDK model names;
- choosing a safe default model;
- identifying Judge schema failures before they pollute saved metrics;
- deciding which models deserve a larger matrix run.

It is not a statistically complete benchmark. Before making policy decisions, run a matrix across all Profiles and Strategies with repetitions.

## Production Guidance

Use `gpt-5.5` as the safe default while Collection Swarm has a single `conversation_model` for both Participants. It had the strongest combined behavior across Collector, Debtor, and Judge probes.

Use `claude-opus-4-7` as the premium Judge challenger once broader calibration is available.

Treat Judge reliability as the highest-risk dimension. A malformed Judge response falls back to `judge_parse_failed`, which corrupts payment probability, compliance, escalation, and Playbook ranking data.

Keep generated operational reports in `output/`. Commit curated snapshots under `docs/`.
