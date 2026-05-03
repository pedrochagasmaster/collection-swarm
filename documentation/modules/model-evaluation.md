# `model_evaluation.py` — per-role model probes

<span class="cs-kicker">collection_swarm/model_evaluation.py</span>

The model-role evaluator. Lets you ask, for any candidate Cursor SDK
model: *is this good enough to play the Collector? The Debtor? The
Judge?* Produces a deterministic Markdown or JSON report with per-role
recommendations.

<dl class="cs-summary">
  <dt>Imports</dt><dd>asyncio, json, re, time, dataclasses, datetime, the agents, the router, the config, the domain models</dd>
  <dt>Side effects</dt><dd>Optionally network calls (live probes); writes a report to disk</dd>
  <dt>Determinism</dt><dd>Report assembly is pure; live probes obviously hit the network</dd>
</dl>

## The shape of the data

| Type                | Purpose                                                                |
| ------------------- | ---------------------------------------------------------------------- |
| `ProbeScenario`     | Inputs used to exercise a model in each role (profile, strategy, debtor prompt, judge transcript). |
| `RoleProbe`         | Raw output of a probe: model name, role, status, content / Judgment.   |
| `RoleAssessment`    | Opinionated 1–10 fit score derived from a probe.                       |
| `ConfigModelStatus` | Whether a configured Cursor SDK model name still resolves on the SDK.  |
| `ModelRoleReport`   | Top-level report aggregating probes, assessments, statuses, and per-role recommendations. |

`EvaluationRole = Literal["collector", "debtor", "judge"]`. `ReportFormat = Literal["markdown", "json"]`.

## Constants

- `DEFAULT_CURSOR_SDK_MODEL_IDS` — the canonical list of model IDs known
  to be available in the Cursor SDK at the time of the baseline run.
- `DEFAULT_CURSOR_PROBE_MODELS` — the subset of those that are worth
  probing (skips e.g. `default`, `composer-1.5`, `claude-opus-4-6`,
  `claude-opus-4-5`, `gpt-5.2`).
- `MODEL_NAME_REPLACEMENTS` — when the configured `model_name` doesn't
  resolve, which IDs to recommend as a replacement.
- `BASELINE_PROBES` — a checked-in baseline probe set captured 2026-04-30
  so the report can render without live calls.

## The probe scenario

```python
@dataclass(frozen=True)
class ProbeScenario:
    profile_id: str = "cooperative_hardship"
    strategy_id: str = "empathetic_payment_plan"
    judge_profile_id: str = "written_proof_disputer"
    debtor_prompt: str = "..."
    judge_transcript: tuple[Message, ...] = (...)
```

The defaults pick the toughest scenarios for each role:

- Collector: a cooperative hardship profile with the empathetic payment
  plan strategy — a well-behaved baseline so a model that struggles
  here is unlikely to do better elsewhere.
- Debtor: same profile, given a Collector turn that asks for a payment
  amount.
- Judge: a written-proof disputer scenario that exercises the parser and
  the constraint verifier (the Collector eventually agrees to send
  validation; a confused Judge invents Constraint Violations).

## Live probes

```python
async def run_live_role_probes(
    config,
    cursor_model_names=DEFAULT_CURSOR_PROBE_MODELS,
    roles=("collector", "debtor", "judge"),
    scenario=None,
    concurrency=1,
) -> tuple[RoleProbe, ...]: ...
```

The function copies the config, registers each requested model as a
`probe-<name>` `ModelConfig`, builds a router, and dispatches one task
per `(model, role)` pair under a semaphore. Each task ends up calling
`_run_role_probe(...)` which builds the appropriate agent
(`CollectorAgent`, `DebtorAgent`, `Judge`) and grabs the response.

The `concurrency` default is `1` to favor reproducibility — Cursor SDK
probes are expensive and ordering matters when comparing.

## Assessment heuristics

`assess_probe(probe)` returns a `RoleAssessment` with a 1–10 score, a
fit label, evidence, and a caution. The role-specific scoring lives in:

- `_assess_collector_probe(probe)` — checks for account-purpose
  identification, concrete account detail, empathetic framing,
  placeholder leakage (`[Collector name]`, `[Agency]`), and awkward
  caller identification.
- `_assess_debtor_probe(probe)` — checks for hardship persona markers
  (rent, hours, family), payment amounts under the constraint cap,
  realistic hedging language, and Markdown formatting leakage.
- `_assess_judge_probe(probe)` — penalizes the
  `judge_parse_failed` end_reason heavily, rewards parseable JSON,
  rewards correct (no false-positive) Constraint Violations, rewards
  scores aligned with the validation-handling scenario.

The 1–10 fit labels:

| Score | Fit label                       |
| ----- | ------------------------------- |
| ≥ 9   | Primary recommendation          |
| 7–8   | Strong candidate                |
| 5–6   | Usable with caution             |
| ≤ 4   | Avoid for now                   |

`recommend_models(assessments)` picks the top scorer per role with a
deliberate tie-breaker order favoring `gpt-5.5` for Collector / Debtor
and `gpt-5.5` / `claude-opus-4-7` for Judge.

## Configuration health

`configured_cursor_model_statuses(config, available_model_ids)` walks
every Cursor SDK model in the configuration and tags it as:

- **works** — `model_name` is in `available_model_ids`.
- **fails** — has a known replacement in `MODEL_NAME_REPLACEMENTS`.
- **unknown** — verify via `Cursor.models.list()` before live use.

The Markdown report renders this as a table so operators can see at a
glance which configured models still resolve.

## Building & writing the report

```python
def build_model_role_report(
    config,
    probes: tuple[RoleProbe, ...] | None = None,
    *,
    scenario: ProbeScenario | None = None,
    title: str = "Cursor Model Role Evaluation",
    generated_at: datetime | None = None,
    available_cursor_model_ids=DEFAULT_CURSOR_SDK_MODEL_IDS,
) -> ModelRoleReport: ...

def render_markdown_report(report: ModelRoleReport) -> str: ...
def report_to_dict(report: ModelRoleReport) -> dict[str, Any]: ...

def write_report(report, path: Path, *, report_format: ReportFormat = "markdown") -> None: ...
```

`build_model_role_report` is pure: it doesn't touch the network. Pass
your own `probes` (e.g., the result of `run_live_role_probes`) or omit
them to render against the checked-in baseline.

The CLI wires this together:

```bash
collection-swarm model-report --output docs/cursor-model-role-report.md
collection-swarm model-report --live-probes \
    --cursor-models gpt-5.5,gpt-5.4,claude-opus-4-7 \
    --output docs/cursor-model-role-report.md
```

The dashboard exposes a similar workflow via the `model-benchmarks`
endpoints.

## Why this lives outside the agents

The agents are the runtime; this module is meta-evaluation. By keeping
probe orchestration and report rendering separate, we can:

- Re-render the baseline report without touching any provider.
- Run live probes without changing the YAML configuration.
- Wire the same logic into the CLI, the dashboard, and a future CI job.
