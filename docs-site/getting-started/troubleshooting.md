# Troubleshooting

## `CURSOR_API_KEY is required`

Save the key in the dashboard under **Settings → Live model API keys**,
or use:

```bash
collection-swarm api-keys set cursor --key ...
```

The Cursor SDK backend also falls back to `CURSOR_API_KEY` from `.env` or
your shell. The `.env` loader does **not** override variables already set
in your shell.

## `NVIDIA_NIM_API_KEY is required for NIM models`

Save the key in **Settings → Live model API keys**, or use:

```bash
collection-swarm api-keys set nvidia_nim --key ...
```

The NIM backend also falls back to `NVIDIA_NIM_API_KEY` from `.env` or
your shell.

## `Cursor SDK bridge not found at .../cursor_sdk_bridge/run.mjs`

The bridge directory must live next to the `src/` tree. If you've
relocated the package, set `CURSOR_SDK_WORKSPACE` so the bridge resolves
correctly, and verify `cursor_sdk_bridge/run.mjs` exists. The path is
computed from the module location at
[`backends/cursor_sdk.py`](../modules/backends/cursor-sdk.md).

## `Node.js is required on PATH for the Cursor SDK backend`

Install Node 22+ and verify with `node --version`. On Cursor Cloud Agents,
add the install step to your environment setup script.

## `Cursor SDK bridge exited with code 1` with non-JSON stdout

The bridge returns plain JSON on success, including for handled errors.
A non-zero exit code with non-JSON stdout means the Node process crashed
before printing the JSON envelope. Check stderr in the raised error
message — it often points at a missing `npm install`, a missing stored
Cursor key, an unset `CURSOR_API_KEY`, or an unknown model ID.

## NIM returns 404

The NIM `model_name` in `config/models.yaml` is probably stale. Hit
`https://integrate.api.nvidia.com/v1/models` with your key, copy the live
model ID, and update the YAML.

## Live simulations are slow

Live runs make multiple sequential model calls per simulation:

```
n_collector + n_debtor turns + 1 judge = up to (max_turns + 1) calls
```

Cursor SDK calls have higher per-call latency than NIM. Mitigations:

- Lower `--reps`.
- Lower `--concurrency`.
- Stay on the deterministic scripted backend while iterating on prompts
  and config.

## `judge_parse_failed` end_reason in saved runs

The Judge expects the model to return a JSON object. If a model wraps it
in Markdown fences or explains itself in prose, the parser at
[`agents/judge.py`](../modules/agents/judge.md) falls back to a heuristic
`Judgment` and stamps `end_reason="judge_parse_failed"`. Switch to a
better Judge model — the baseline report recommends
`cursor-claude-opus-4-7-thinking-high`.

## `unknown model 'xyz'` from the router

The model ID isn't in `config/models.yaml` or wasn't loaded. Run
`collection-swarm list-strategies` and `collection-swarm list-profiles`
to confirm the config dir Click resolved (defaults to `./config`).

## Dashboard shows "No runs yet"

The dashboard reads `output/collection_swarm.sqlite` by default. If your
runs landed in a different DB path (set with `--db`), pass the same path
when starting the server, or seed:

```bash
collection-swarm seed --count 24
```

## Tests fail with `aiosqlite` import errors

`pip install -e ".[dev]"` was probably skipped. The `[dev]` extra pulls
`pytest`, `pytest-asyncio`, and `httpx`, all of which the test suite
imports.

## Repository hygiene reminders

These paths are gitignored and should never be committed:

- `.env` — API keys
- `output/` — SQLite databases and generated playbooks
- `cursor_sdk_bridge/node_modules/`
- Python build artifacts (`*.egg-info`, `__pycache__`, `dist/`)
