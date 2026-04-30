# Cursor Model Role Evaluation

Generated: 2026-04-30T14:16:08.827084+00:00

## Executive Recommendation

- **Collector**: `gpt-5.5`
- **Debtor**: `gpt-5.5`
- **Judge**: `gpt-5.5`

Use `gpt-5.5` as the safest default when the app uses one conversation model for both Participants. Treat `claude-opus-4-7` as the premium Judge challenger after broader calibration.

## Configuration Health

| Configured ID | model_name | Status | Action |
| --- | --- | --- | --- |
| `cursor-composer-2` | `composer-2` | works | Keep |
| `cursor-gpt-5.5-medium` | `gpt-5.5` | works | Keep |
| `cursor-gpt-5.4-high` | `gpt-5.4` | works | Keep |
| `cursor-gpt-5.4-high-fast` | `gpt-5.4-mini` | works | Keep |
| `cursor-gpt-5.3-codex-high` | `gpt-5.3-codex` | works | Keep |
| `cursor-gpt-5.3-codex-high-fast` | `gpt-5.3-codex-spark` | works | Keep |
| `cursor-claude-4.6-opus-high-thinking` | `claude-opus-4-6` | works | Keep |
| `cursor-claude-4.6-opus-high-thinking-fast` | `claude-sonnet-4-6` | works | Keep |
| `cursor-claude-opus-4-7-thinking-high` | `claude-opus-4-7` | works | Keep |

## Role Assessments

### Collector

| Model | Score | Fit | Evidence | Caution |
| --- | ---: | --- | --- | --- |
| `gemini-3.1-pro` | 8 | Strong candidate | identified account purpose; included account detail; used empathetic payment-plan framing | no major one-shot caution observed |
| `gpt-5.3-codex` | 8 | Strong candidate | identified account purpose; included account detail; used empathetic payment-plan framing | no major one-shot caution observed |
| `gpt-5.4` | 8 | Strong candidate | identified account purpose; included account detail; used empathetic payment-plan framing | no major one-shot caution observed |
| `gpt-5.4-mini` | 8 | Strong candidate | identified account purpose; included account detail; used empathetic payment-plan framing | no major one-shot caution observed |
| `gpt-5.5` | 8 | Strong candidate | identified account purpose; included account detail; used empathetic payment-plan framing | no major one-shot caution observed |
| `claude-sonnet-4-6` | 7 | Strong candidate | identified account purpose; used empathetic payment-plan framing | omitted concrete account detail |
| `claude-opus-4-7` | 6 | Usable with caution | identified account purpose; included account detail; used empathetic payment-plan framing | awkward caller identification |
| `composer-2` | 6 | Usable with caution | identified account purpose; included account detail; used empathetic payment-plan framing | leaked placeholders |
| `claude-haiku-4-5` | 4 | Avoid for now | identified account purpose | omitted concrete account detail; leaked placeholders |

### Debtor

| Model | Score | Fit | Evidence | Caution |
| --- | ---: | --- | --- | --- |
| `claude-haiku-4-5` | 9 | Primary recommendation | stayed in hardship persona; honored payment ceiling; sounded like a realistic consumer | needs broader profile coverage |
| `claude-opus-4-7` | 9 | Primary recommendation | stayed in hardship persona; honored payment ceiling; sounded like a realistic consumer | needs broader profile coverage |
| `claude-sonnet-4-6` | 9 | Primary recommendation | stayed in hardship persona; honored payment ceiling; sounded like a realistic consumer | needs broader profile coverage |
| `gemini-3.1-pro` | 9 | Primary recommendation | stayed in hardship persona; honored payment ceiling; sounded like a realistic consumer | needs broader profile coverage |
| `gpt-5.3-codex` | 9 | Primary recommendation | stayed in hardship persona; honored payment ceiling; sounded like a realistic consumer | needs broader profile coverage |
| `gpt-5.4` | 9 | Primary recommendation | stayed in hardship persona; honored payment ceiling; sounded like a realistic consumer | needs broader profile coverage |
| `gpt-5.4-mini` | 9 | Primary recommendation | stayed in hardship persona; honored payment ceiling; sounded like a realistic consumer | needs broader profile coverage |
| `gpt-5.5` | 9 | Primary recommendation | stayed in hardship persona; honored payment ceiling; sounded like a realistic consumer | needs broader profile coverage |
| `composer-2` | 8 | Strong candidate | stayed in hardship persona; honored payment ceiling | needs broader profile coverage |

### Judge

| Model | Score | Fit | Evidence | Caution |
| --- | ---: | --- | --- | --- |
| `claude-opus-4-7` | 10 | Primary recommendation | returned parseable Judgment; did not invent profile Constraint Violations; scores aligned with low-risk validation handling; did not overstate payment likelihood | calibrate across more transcripts before policy use |
| `gpt-5.5` | 10 | Primary recommendation | returned parseable Judgment; did not invent profile Constraint Violations; scores aligned with low-risk validation handling; did not overstate payment likelihood | calibrate across more transcripts before policy use |
| `gpt-5.3-codex` | 6 | Usable with caution | returned parseable Judgment; did not overstate payment likelihood | reported possible false Constraint Violations |
| `gpt-5.4` | 6 | Usable with caution | returned parseable Judgment; did not overstate payment likelihood | reported possible false Constraint Violations |
| `composer-2` | 5 | Usable with caution | returned parseable Judgment | reported possible false Constraint Violations |
| `claude-haiku-4-5` | 3 | Unsafe without parser hardening | underlying reasoning may be useful, but strict schema validation failed | parser fallback corrupts saved metrics |
| `claude-sonnet-4-6` | 3 | Unsafe without parser hardening | underlying reasoning may be useful, but strict schema validation failed | parser fallback corrupts saved metrics |
| `gemini-3.1-pro` | 3 | Unsafe without parser hardening | underlying reasoning may be useful, but strict schema validation failed | parser fallback corrupts saved metrics |
| `gpt-5.4-mini` | 3 | Unsafe without parser hardening | underlying reasoning may be useful, but strict schema validation failed | parser fallback corrupts saved metrics |

## Probe Scenario

- Profile: `cooperative_hardship`
- Strategy: `empathetic_payment_plan`
- Judge profile: `written_proof_disputer`

## Operational Notes

- Scores are deterministic interpretations of probe outputs, not a statistically complete benchmark.
- Judge reliability carries extra weight because parse fallback corrupts saved metrics and playbook rankings.
- Run live reports with `collection-swarm model-report --live-probes` when validating new SDK model IDs.
- Keep report outputs in `docs/` for checked-in snapshots or `output/` for disposable benchmark runs.
