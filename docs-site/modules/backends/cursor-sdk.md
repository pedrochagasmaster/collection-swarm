# `backends/cursor_sdk.py` and the Node.js bridge

<span class="cs-kicker">collection_swarm/backends/cursor_sdk.py · cursor_sdk_bridge/run.mjs</span>

The Cursor SDK is a TypeScript-first package. To talk to it from Python,
Collection Swarm spawns a Node subprocess on every call and exchanges a
JSON envelope on stdin / stdout. The Python side lives at
`backends/cursor_sdk.py`; the Node side lives at
`cursor_sdk_bridge/run.mjs`.

<dl class="cs-summary">
  <dt>Python imports</dt><dd>standard library, <code>collection_swarm.env</code>, domain models</dd>
  <dt>Node bridge</dt><dd><code>@cursor/sdk</code> (installed via <code>npm install</code> inside <code>cursor_sdk_bridge/</code>)</dd>
  <dt>Network</dt><dd>Yes — needs <code>CURSOR_API_KEY</code></dd>
  <dt>Process model</dt><dd>One subprocess per <code>complete()</code> call</dd>
</dl>

## Python: `CursorSdkBackend.complete()`

```python
async def complete(self, model: ModelConfig, messages: list[LLMMessage]) -> LLMResponse:
    load_dotenv_if_present()
    store = get_settings_store()
    api_key = store.resolve("cursor_api_key", "CURSOR_API_KEY")
    if not api_key:
        raise RuntimeError("CURSOR_API_KEY is required for Cursor SDK models. ...")

    script = _bridge_script()
    if not script.is_file():
        raise RuntimeError(f"Cursor SDK bridge not found at {script}. ...")

    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js is required on PATH for the Cursor SDK backend (Node 22+ recommended).")

    cwd = store.resolve("cursor_sdk_workspace", "CURSOR_SDK_WORKSPACE") or str(Path.cwd().resolve())
    model_id = model.model_name or model.id
    payload = json.dumps(
        {
            "messages": [m.model_dump() for m in messages],
            "modelId": model_id,
            "cwd": cwd,
            "preamble": self.prompts.preamble,
        },
        ensure_ascii=False,
    )

    proc = await asyncio.create_subprocess_exec(
        node,
        str(script),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=os.environ.copy(),
    )
    stdout_b, stderr_b = await proc.communicate(payload.encode("utf-8"))
```

The function resolves `CURSOR_API_KEY` and `CURSOR_SDK_WORKSPACE` via
`settings.resolve()`, which checks the stored database value first
(set via dashboard or CLI), then falls back to the corresponding
environment variable. It validates the key, the script, and Node
availability *before* spawning anything, so the error messages are the
diagnostic, not a "Node 1: command not found" leak.

After the subprocess exits, the backend:

1. Decodes stdout as JSON.
2. If the JSON contains an `"error"` key, raises with that message.
3. If the process exited non-zero, raises with the exit code and stderr.
4. Returns an `LLMResponse` populated from `content`, `inputTokens`,
   `outputTokens`, and the standard cost estimator.

Wire failures (subprocess crashes, malformed JSON) raise `RuntimeError`
with the first 500 bytes of stdout for context.

## Bridge: `cursor_sdk_bridge/run.mjs`

```javascript
import fs from "node:fs"
import { Agent } from "@cursor/sdk"

function formatMessages(messages, preamble) {
  const lines = [preamble.trim(), "", "## Messages"]
  for (const m of messages) {
    lines.push(`### ${m.role}`, m.content, "")
  }
  return lines.join("\n")
}

async function main() {
  const raw = fs.readFileSync(0, "utf8")
  let payload = JSON.parse(raw)
  const apiKey = process.env.CURSOR_API_KEY
  // ... validation ...
  const { messages, modelId, cwd, preamble } = payload
  const workspace = typeof cwd === "string" && cwd.length > 0 ? cwd : process.cwd()
  const prompt = formatMessages(messages, preamble)
  const agent = await Agent.create({
    apiKey,
    name: "collection-swarm",
    model: { id: modelId },
    local: { cwd: workspace },
  })
  const run = await agent.send(prompt)
  let content = ""
  for await (const event of run.stream()) {
    if (event.type !== "assistant") continue
    for (const block of event.message.content) {
      if (block.type === "text") content += block.text
    }
  }
  const result = await run.wait()
  const usage = result.usage ?? {}
  console.log(JSON.stringify({
    content,
    inputTokens: Number(usage.inputTokens ?? 0),
    outputTokens: Number(usage.outputTokens ?? 0),
    status: result.status,
  }))
}
```

Key behaviors:

- Reads stdin once, parses JSON.
- Uses `Agent.create({...})` with the requested `modelId`. The Cursor
  SDK manages credentials and provider routing.
- Streams the agent's `assistant` events, concatenating only `text`
  blocks. Tool-call blocks are dropped — the
  [`prompts.cursor_sdk.preamble`](../../reference/configuration.md)
  asks the agent not to use tools.
- After the stream completes, calls `run.wait()` to grab the final
  status and usage.
- Writes a single JSON envelope to stdout.
- On any error, writes `{"error": "..."}` to stdout and sets a non-zero
  exit code. Python promotes this to a `RuntimeError`.

## Wire contract

**Stdin:**

```json
{
  "messages": [{"role": "system", "content": "..."}, ...],
  "modelId": "gpt-5.5",
  "cwd": "/abs/path/to/workspace",
  "preamble": "Você é o assistente em uma simulação..."
}
```

**Stdout (success):**

```json
{
  "content": "Olá, aqui é Alex...",
  "inputTokens": 542,
  "outputTokens": 87,
  "status": "completed"
}
```

**Stdout (error):**

```json
{ "error": "CURSOR_API_KEY is not set" }
```

## Why subprocess instead of HTTP

The Cursor SDK manages auth, retries, and provider routing on the Node
side. Exposing it via subprocess lets us reuse the official SDK without
re-implementing the protocol in Python. The downside is per-call process
startup latency — the JSON envelope is tiny but Node startup is real
overhead. For high-throughput sweeps, this is the dominant cost.

## Operational notes

- `CURSOR_SDK_WORKSPACE` defaults to the current working directory. The
  Cursor agent is told this is the workspace it operates in. For
  Collection Swarm we don't actually want the agent to read or write
  files, so the preamble explicitly instructs it not to use tools.
- The `npm install` step is required exactly once per environment.
  `cursor_sdk_bridge/node_modules/` is gitignored.
- Cursor model availability changes; the `model_evaluation.py` baseline
  report tracks which `model_name` values still resolve. Re-run with
  `--live-probes` after upgrading the SDK.
