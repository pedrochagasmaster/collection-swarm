# Live model setup

Collection Swarm ships with three backends:

| Backend     | Module                                                | Needs                            |
| ----------- | ----------------------------------------------------- | -------------------------------- |
| Scripted    | [`backends/scripted.py`](../modules/backends/scripted.md) | Nothing — runs offline          |
| NVIDIA NIM  | [`backends/nim.py`](../modules/backends/nim.md)           | `NVIDIA_NIM_API_KEY`            |
| Cursor SDK  | [`backends/cursor_sdk.py`](../modules/backends/cursor-sdk.md) | `CURSOR_API_KEY`, Node.js 22+, the bridge under `cursor_sdk_bridge/` |

The router in [`backends/router.py`](../modules/backends/base-and-router.md)
dispatches each model ID to the correct backend based on its `backend`
field in `config/models.yaml`.

## Configure your secrets

Create a `.env` file in the repo root. All backends call
[`env.load_dotenv_if_present`](../modules/env.md), which loads
simple `KEY=VALUE` lines without overriding variables already exported in
your shell.

```bash title=".env"
NVIDIA_NIM_API_KEY=...
CURSOR_API_KEY=...
# Optional: tell Cursor SDK which workspace to operate in. Defaults to cwd.
CURSOR_SDK_WORKSPACE=/absolute/path/to/your/workspace
```

!!! tip "Secrets on Cursor Cloud"
    If you're running this from a Cursor Cloud Agent, add the same keys
    in **Cursor Dashboard → Cloud Agents → Secrets** so they're injected
    automatically into every new VM.

## NVIDIA NIM

The NIM backend is a thin wrapper around `litellm.acompletion` pointed at
`https://integrate.api.nvidia.com/v1`. NIM exposes its model catalogue with
LiteLLM's OpenAI-compatible prefix, so the entries in `config/models.yaml`
look like:

```yaml
- id: nim-mistral-large-3-675b
  backend: nim
  provider: mistral
  model_name: openai/mistralai/mistral-large-3-675b-instruct-2512
```

The `id` is what you pass to the CLI; the `model_name` is the exact string
sent to LiteLLM. Try a single live simulation:

```bash
collection-swarm simulate \
  --profile cooperative_hardship \
  --strategy empathetic_payment_plan \
  --conversation-model nim-mistral-large-3-675b \
  --no-save
```

If NIM rejects the model (most often a 404 because the model name is
stale), update `config/models.yaml` against the live `/v1/models` listing.

## Cursor SDK

The Cursor SDK backend talks to the official `@cursor/sdk` package through
a Node subprocess defined at `cursor_sdk_bridge/run.mjs`. The Python side
ships JSON in over stdin and reads JSON back from stdout — see
[`cursor_sdk.py` docs](../modules/backends/cursor-sdk.md) for the wire
contract.

### One-time setup

```bash
cd cursor_sdk_bridge
npm install
cd ..
```

`npm install` pulls `@cursor/sdk` into `cursor_sdk_bridge/node_modules/`,
which is gitignored. The bridge directory and the lockfile **are**
committed so installs are reproducible.

### Run a live simulation with Cursor + Anthropic

```bash
collection-swarm simulate \
  --profile cooperative_hardship \
  --strategy empathetic_payment_plan \
  --conversation-model cursor-gpt-5.5-medium \
  --judge-model cursor-claude-4.6-opus-high-thinking \
  --no-save
```

The router instantiates a single `CursorSdkBackend` and reuses it across
every Cursor SDK model ID. Each `complete()` call spawns one Node
subprocess, sends the JSON payload, and parses the JSON reply.

### Verify with `test-connection`

```bash
collection-swarm test-connection
```

This runs a degenerate completion against the configured default
conversation model. For NIM and Cursor SDK backends, it prints a hint that
you should run a real simulation rather than the no-op probe — those
backends require credentials and a live network round-trip.

## Pin recommended model combos

The model-role evaluation pipeline at
[`model_evaluation.py`](../modules/model-evaluation.md) ships a baseline
report (`docs/cursor-model-role-report.md`) and the `model-report` CLI to
re-run it. The current recommendations from the baseline probes:

| Role      | Recommended Cursor SDK model |
| --------- | ----------------------------- |
| Collector | `gpt-5.5`                     |
| Debtor    | `gpt-5.5`                     |
| Judge     | `claude-opus-4-7`             |

Use `gpt-5.5` as the safest default when one conversation model serves both
Participants. Treat `claude-opus-4-7` as the premium Judge challenger after
broader calibration. Re-run the report with live probes to refresh:

```bash
collection-swarm model-report \
  --live-probes \
  --cursor-models gpt-5.5,gpt-5.4,claude-opus-4-7 \
  --output docs/cursor-model-role-report.md
```

See the [model evaluation module](../modules/model-evaluation.md) for the
scoring rubric.
