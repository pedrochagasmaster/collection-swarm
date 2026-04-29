# Collection Swarm

Collection Swarm runs synthetic debt-collection conversations between a Collector
participant, a Profile-driven Debtor participant, and a Judge evaluator. It stores
Simulations in SQLite and can generate a Markdown playbook from completed results.

The app is usable offline out of the box through a deterministic `scripted-local`
model, and can also call NVIDIA NIM models when `NVIDIA_NIM_API_KEY` is configured.

## Install

```bash
pip install -e .
```

## Quick start

```bash
collection-swarm list-profiles
collection-swarm list-strategies

collection-swarm simulate \
  --profile cooperative_hardship \
  --strategy empathetic_payment_plan

collection-swarm run --reps 1 --concurrency 2
collection-swarm analyze --output output/playbook.md
```

By default results are saved to `output/collection_swarm.sqlite`.

## Models

`config/models.yaml` includes:

- `scripted-local`: deterministic local backend for demos, tests, and offline use.
- NIM model definitions for live runs. Select them with `--conversation-model` and
  `--judge-model` after setting `NVIDIA_NIM_API_KEY`.

## Development

```bash
pytest
```
