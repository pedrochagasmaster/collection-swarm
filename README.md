# Collection Swarm

Collection Swarm runs synthetic debt-collection conversations between a Collector
participant, a Profile-driven Debtor participant, and a Judge evaluator. It stores
Simulations in SQLite and can generate a Markdown playbook from completed results.

The app is usable offline out of the box through deterministic local models, and
can also run real model paths through Cursor ACP and NVIDIA NIM when the required
CLIs/credentials are configured.

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

- `local-scripted` / `local-judge`: deterministic local backends for demos,
  tests, and offline use.
- Cursor ACP judge models such as `cursor-auto`, `cursor-gpt-4.1`, and
  `cursor-claude-4-sonnet`. These require the Cursor CLI `agent` binary and
  authentication (`agent login`, `CURSOR_API_KEY`, or `CURSOR_AUTH_TOKEN`).
- NVIDIA NIM conversation/mechanical models such as `mistral-large-3-675b`,
  `llama-4-maverick`, and `nemotron-mini-4b`. These require
  `NVIDIA_NIM_API_KEY`.

Example live mixed run:

```bash
collection-swarm test-connection --models mistral-large-3-675b,cursor-auto

collection-swarm simulate \
  --profile cooperative_hardship \
  --strategy empathetic_payment_plan \
  --conversation-model mistral-large-3-675b \
  --judge-model cursor-auto
```

Cursor ACP uses `agent acp` over stdio. If your `agent` binary is not on `PATH`,
set `CURSOR_AGENT_COMMAND=/path/to/agent`. You may pass extra startup arguments
with `CURSOR_AGENT_ARGS`, for example `CURSOR_AGENT_ARGS="--api-key $CURSOR_API_KEY acp"`.

## Development

```bash
pytest
```
