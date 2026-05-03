---
title: LLM Backends
layout: default
nav_order: 6
---

# LLM Backends
{: .no_toc }

Pluggable model backends: Scripted, NVIDIA NIM, and Cursor SDK.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Source:** `src/collection_swarm/backends/`

## Overview

The backends package provides a **pluggable model layer** that decouples agents from specific LLM providers. All backends implement the `LLMBackend` protocol and return `LLMResponse` dataclasses.

## LLMResponse

```python
@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model_id: str = ""
    backend: str = ""
```

Every backend returns this uniform response, allowing the engine and agents to track tokens and costs regardless of the provider.

## LLMBackend Protocol

```python
class LLMBackend(Protocol):
    async def complete(
        self,
        model: ModelConfig,
        messages: list[LLMMessage],
    ) -> LLMResponse: ...
```

Any class implementing `complete()` with this signature can serve as a backend.

---

## LLMRouter

**Source:** `src/collection_swarm/backends/router.py`

The `LLMRouter` dispatches completion requests to the correct backend based on the model's `backend` field in its configuration.

```python
class LLMRouter:
    def __init__(
        self,
        models: dict[str, ModelConfig],
        backends: dict[str, LLMBackend] | None = None,
        cursor_sdk_prompts: CursorSdkPromptConfig | None = None,
    )

    async def complete(
        self,
        model_id: str,
        messages: list[LLMMessage],
    ) -> LLMResponse
```

### Backend Resolution

1. Look up the `ModelConfig` by `model_id`.
2. Look up the backend by `model.backend` name.
3. If the backend hasn't been loaded yet, **lazy-load** it:
   - `"cursor_sdk"` or `"acp"` → `CursorSdkBackend`
   - `"nim"` → `NimBackend`
4. Call `backend.complete(model, messages)`.

### Pre-registered Backends

| Backend Name | Class | When Loaded |
|:-------------|:------|:------------|
| `scripted` | `ScriptedBackend` | Always (at router init) |
| `heuristic` | `ScriptedBackend` | Always (alias for scripted) |
| `nim` | `NimBackend` | Lazy (on first NIM model call) |
| `cursor_sdk` | `CursorSdkBackend` | Lazy (on first Cursor model call) |
| `acp` | `CursorSdkBackend` | Lazy (alias for cursor_sdk) |

---

## ScriptedBackend

**Source:** `src/collection_swarm/backends/scripted.py`

A **deterministic local backend** that makes the application fully functional without any API keys. It powers the `local-scripted` and `local-judge` model configurations.

### Role Detection

The scripted backend determines which role to emulate by inspecting the system prompt:

1. **Judge** — if the system prompt contains "judge", "evaluator", or "juiz avaliador"
2. **Debtor** — if the system prompt starts with "you are the debtor" or "você é o devedor"
3. **Collector** — default fallback

### Collector Logic

The scripted collector:

1. **Detects the strategy** from the system prompt (payment_plan, settlement, parcelamento, etc.) and adjusts the tactic description accordingly.
2. **Opening turn** (no debtor in history): introduces itself as representing the Will Bank liquidator, acknowledging the situation.
3. **Agreement detected**: if the debtor agreed to pay, closes with a boleto confirmation and `[END_CONVERSATION]`.
4. **Hardship/dispute detected**: offers documentation via official channels, proposes flexible terms.
5. **Default**: asks what amount or date works for the debtor.

### Debtor Logic

The scripted debtor responds based on profile characteristics detected in the system prompt:

| Profile Type | Behavior |
|:-------------|:---------|
| Disputer / wants written proof | Demands fatura detalhada before payment discussion |
| Scam suspicious | Asks for liquidator name and official channel |
| Hardship / can pay partial | Offers a small monthly payment via boleto |
| Blocked funds | Requests low-entry boleto with monthly cap |
| Hostile / avoidant | Demands everything in writing, ends conversation |
| Confused | Asks for explanation of post-liquidation obligations |
| Default cooperative | Offers to pay this week if sent written confirmation |

### Judge Logic

The scripted judge produces a JSON `Judgment` based on keywords in the transcript:

| Keywords Detected | Outcome | Probability |
|:------------------|:--------|:------------|
| "payment plan", "per month", "parcela" | `payment_plan` | 0.72 |
| "will pay", "payment this week" | `promise_to_pay` | 0.65 |
| "not committing", "manda tudo por escrito" | `no_commitment` | 0.25 |
| Default | `no_commitment` | 0.35 |

All scripted judge responses have `compliance_score: 0.95` and `escalation_risk: 0.08`.

---

## NimBackend

**Source:** `src/collection_swarm/backends/nim.py`

Uses **LiteLLM** to call NVIDIA NIM models via the OpenAI-compatible API at `https://integrate.api.nvidia.com/v1`.

### Requirements

- `NVIDIA_NIM_API_KEY` environment variable (loaded from `.env` if present)

### Implementation

```python
class NimBackend:
    def __init__(self, base_url: str = "https://integrate.api.nvidia.com/v1")

    async def complete(self, model: ModelConfig, messages: list[LLMMessage]) -> LLMResponse
```

1. Loads the API key from the environment.
2. Calls `litellm.acompletion()` with the model's `litellm_model` name and formatted messages.
3. Extracts content, token counts, and estimates cost from the model's configured rates.

### Model Name Resolution

The `ModelConfig.litellm_model` property returns `model_name` if set, otherwise falls back to `id`. NIM models use the `openai/` prefix for LiteLLM's OpenAI-compatible routing:

```yaml
model_name: openai/mistralai/mistral-large-3-675b-instruct-2512
```

---

## CursorSdkBackend

**Source:** `src/collection_swarm/backends/cursor_sdk.py`

Calls the **Cursor SDK** via a Node.js subprocess bridge. The bridge script (`cursor_sdk_bridge/run.mjs`) uses the official `@cursor/sdk` TypeScript package.

### Requirements

- `CURSOR_API_KEY` environment variable
- Node.js 22+ on PATH
- `npm install` run in `cursor_sdk_bridge/`

### Architecture

```
Python Process                  Node.js Subprocess
┌──────────────┐               ┌──────────────────┐
│ CursorSdk    │──── stdin ───►│ run.mjs          │
│ Backend      │               │                  │
│              │◄── stdout ────│ Agent.create()   │
│              │               │ agent.send()     │
└──────────────┘               └──────────────────┘
```

### Implementation Flow

1. Load `CURSOR_API_KEY` from the environment.
2. Verify the bridge script exists at `cursor_sdk_bridge/run.mjs`.
3. Verify Node.js is available on PATH.
4. Build a JSON payload with messages, model ID, workspace path, and preamble.
5. Spawn `node run.mjs` as a subprocess.
6. Write the JSON payload to stdin.
7. Read JSON output from stdout.
8. Parse content, token counts, and calculate estimated cost.

### Bridge Payload Format

```json
{
  "messages": [{"role": "system", "content": "..."}, ...],
  "modelId": "gpt-5.5",
  "cwd": "/path/to/workspace",
  "preamble": "Cursor SDK preamble text..."
}
```

### Error Handling

The backend handles several failure modes:

| Scenario | Error |
|:---------|:------|
| `CURSOR_API_KEY` not set | `RuntimeError` with setup instructions |
| Bridge script not found | `RuntimeError` with path information |
| Node.js not on PATH | `RuntimeError` with version requirement |
| Non-JSON stdout | `RuntimeError` with output preview |
| Non-zero exit code | `RuntimeError` with stderr |
| `error` key in response | `RuntimeError` with bridge error message |

---

## Cost Estimation

Both NIM and Cursor SDK backends calculate cost using the same formula:

```python
cost = (input_tokens / 1_000_000 * model.input_cost_per_m) + (
    output_tokens / 1_000_000 * model.output_cost_per_m
)
```

Cost rates are configured per model in `config/models.yaml`. Current configurations have all rates set to 0, which is appropriate for subscription-based access.
