# Cursor SDK Backend

**Module:** `src/collection_swarm/backends/cursor_sdk.py`

The `CursorSdkBackend` connects Collection Swarm to the **Cursor coding agent API** via the official [`@cursor/sdk`](https://github.com/cursor/cookbook) TypeScript package. Because the SDK is Node.js-only, Python communicates through a **subprocess bridge** — a small Node.js script that reads JSON from stdin and writes JSON to stdout.

---

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│ Python (CursorSdkBackend)                                │
│                                                          │
│  1. Build JSON payload (messages, modelId, cwd, preamble)│
│  2. Spawn Node subprocess: cursor_sdk_bridge/run.mjs     │
│  3. Write JSON to stdin                                  │
│  4. Read JSON from stdout                                │
│  5. Parse into LLMResponse                               │
└───────────────────────┬──────────────────────────────────┘
                        │ stdin/stdout (JSON)
┌───────────────────────▼──────────────────────────────────┐
│ Node.js (cursor_sdk_bridge/run.mjs)                      │
│                                                          │
│  1. Parse JSON from stdin                                │
│  2. Create Agent via @cursor/sdk                         │
│  3. Send formatted prompt                                │
│  4. Stream response and collect text                     │
│  5. Write JSON result to stdout                          │
└──────────────────────────────────────────────────────────┘
```

---

## Class: `CursorSdkBackend`

### Constructor

```python
class CursorSdkBackend(LLMBackend):
    def __init__(
        self,
        prompts: CursorSdkPromptConfig,
    ) -> None
```

| Parameter | Type | Description |
|---|---|---|
| `prompts` | `CursorSdkPromptConfig` | Contains the `preamble` string prepended to all prompts |

### `CursorSdkPromptConfig`

```python
class CursorSdkPromptConfig(BaseModel):
    preamble: str   # Context prepended to the formatted messages
```

---

## Prerequisites

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `CURSOR_API_KEY` | **Yes** | API key from the Cursor integrations dashboard |
| `CURSOR_SDK_WORKSPACE` | No | Override the workspace directory passed to the SDK agent (defaults to `cwd`) |

### System Requirements

| Requirement | Details |
|---|---|
| **Node.js** | Version 22+ must be available on `PATH` |
| **Bridge script** | `cursor_sdk_bridge/run.mjs` must exist in the repository root |
| **npm dependencies** | Run `npm install` in `cursor_sdk_bridge/` before first use |

!!! failure "Startup errors"
    The backend validates prerequisites before spawning the subprocess:

    | Condition | Error |
    |---|---|
    | `CURSOR_API_KEY` not set | `RuntimeError: CURSOR_API_KEY is required for Cursor SDK models.` |
    | Bridge script not found | `RuntimeError: Cursor SDK bridge not found at {path}.` |
    | Node.js not on PATH | `RuntimeError: Node.js is required on PATH for the Cursor SDK backend (Node 22+ recommended).` |

---

## Method: `complete`

```python
async def complete(
    self,
    model: ModelConfig,
    messages: list[LLMMessage],
) -> LLMResponse
```

### Request Flow

```
complete(model, messages)
    │
    ├── 1. Validate: CURSOR_API_KEY, bridge script, Node.js
    │
    ├── 2. Build JSON payload:
    │       {
    │           "messages": [{"role": "...", "content": "..."}],
    │           "modelId": "claude-sonnet-4-20250514",
    │           "cwd": "/workspace",
    │           "preamble": "You are evaluating..."
    │       }
    │
    ├── 3. Spawn: node cursor_sdk_bridge/run.mjs
    │       stdin  ← JSON payload
    │       stdout → JSON response
    │
    ├── 4. Parse stdout JSON
    │
    └── 5. Return LLMResponse
```

### Model ID Resolution

The backend uses `model.model_name` if set, falling back to `model.id`:

```python
model_id = model.model_name or model.id
```

This allows the YAML config to specify provider-specific model names separately from the internal identifier.

---

## Bridge Protocol

### Input (Python → Node.js via stdin)

```json
{
  "messages": [
    { "role": "system", "content": "You are a judge evaluating..." },
    { "role": "user", "content": "Transcript:\nCollector: Hello..." }
  ],
  "modelId": "claude-sonnet-4-20250514",
  "cwd": "/workspace",
  "preamble": "You are a specialized debt collection evaluation system."
}
```

| Field | Type | Description |
|---|---|---|
| `messages` | `array` | Chat messages with `role` and `content` |
| `modelId` | `string` | Model identifier passed to `Agent.create()` |
| `cwd` | `string` | Workspace directory for the Cursor agent |
| `preamble` | `string` | Context prepended to the formatted prompt |

### Output (Node.js → Python via stdout)

**Success:**

```json
{
  "content": "Based on the transcript analysis...",
  "inputTokens": 1523,
  "outputTokens": 487,
  "status": "completed"
}
```

**Error:**

```json
{
  "error": "CURSOR_API_KEY is not set"
}
```

| Field | Type | Description |
|---|---|---|
| `content` | `string` | Generated text from the agent |
| `inputTokens` | `number` | Token count for the prompt |
| `outputTokens` | `number` | Token count for the completion |
| `status` | `string` | Agent run status |
| `error` | `string` | Error message (only on failure) |

---

## Bridge Script: `run.mjs`

The bridge script (`cursor_sdk_bridge/run.mjs`) handles the Node.js side of the subprocess protocol.

### Message Formatting

Messages are converted into a markdown-formatted prompt:

```javascript
function formatMessages(messages, preamble) {
  const lines = [preamble.trim(), "", "## Messages"]
  for (const m of messages) {
    lines.push(`### ${m.role}`, m.content, "")
  }
  return lines.join("\n")
}
```

**Example formatted prompt:**

```markdown
You are a specialized debt collection evaluation system.

## Messages
### system
You are a judge evaluating a debt collection conversation...

### user
Transcript:
Collector: Hello, I'm calling about...
Debtor: What account?
```

### SDK Agent Lifecycle

```javascript
// 1. Create agent
const agent = await Agent.create({
  apiKey,
  name: "collection-swarm",
  model: { id: modelId },
  local: { cwd: workspace },
})

// 2. Send prompt and stream response
const run = await agent.send(prompt)
let content = ""
for await (const event of run.stream()) {
  if (event.type !== "assistant") continue
  for (const block of event.message.content) {
    if (block.type === "text") content += block.text
  }
}

// 3. Collect usage data
const result = await run.wait()
const usage = result.usage ?? {}

// 4. Cleanup
await agent[Symbol.asyncDispose]()
```

### Package Configuration

```json
{
  "name": "collection-swarm-cursor-sdk-bridge",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "engines": { "node": ">=22" },
  "dependencies": {
    "@cursor/sdk": "^1.0.7"
  }
}
```

---

## Error Handling

The Python backend handles multiple failure modes:

| Scenario | Detection | Error |
|---|---|---|
| Non-JSON stdout | `json.JSONDecodeError` on stdout parse | `RuntimeError: Cursor SDK bridge returned non-JSON stdout: {preview}` |
| Non-zero exit + non-JSON | Exit code ≠ 0 and JSON parse fails | `RuntimeError: Cursor SDK bridge exited with code {code} and returned non-JSON stdout: {preview}. stderr={stderr}` |
| Bridge reports error | `"error"` key in parsed JSON | `RuntimeError: Cursor SDK bridge: {error_message}` |
| Non-zero exit (after valid JSON) | Exit code ≠ 0 | `RuntimeError: Cursor SDK bridge exited with code {code}. stderr={stderr}` |

!!! tip "Debugging bridge errors"
    The stderr output from the Node.js subprocess is captured and included in error messages when available. Check for common issues:

    - Missing `npm install` in `cursor_sdk_bridge/`
    - Node.js version < 22
    - Expired or invalid `CURSOR_API_KEY`
    - Network connectivity issues

---

## Cost Estimation

Uses the same formula as the NIM backend:

```python
def _estimate_cost(model, input_tokens, output_tokens) -> float:
    return (
        (input_tokens / 1_000_000 * model.input_cost_per_m)
        + (output_tokens / 1_000_000 * model.output_cost_per_m)
    )
```

---

## Setup Guide

```bash
# 1. Install Node.js 22+
nvm install 22
nvm use 22

# 2. Install bridge dependencies
cd cursor_sdk_bridge/
npm install

# 3. Set API key
export CURSOR_API_KEY="your-key-here"

# 4. Configure a model in config/models.yaml
```

```yaml
# config/models.yaml
tiers:
  cloud:
    models:
      - id: cursor-claude-sonnet
        backend: cursor_sdk
        provider: cursor
        model_name: claude-sonnet-4-20250514
        input_cost_per_m: 3.00
        output_cost_per_m: 15.00
```

---

## Related

- [Backend Overview](overview.md) — the `LLMBackend` protocol and `LLMResponse` dataclass
- [LLM Router](router.md) — lazy-loading and `"cursor_sdk"` / `"acp"` aliasing
- [NIM Backend](nim.md) — alternative cloud backend via NVIDIA
