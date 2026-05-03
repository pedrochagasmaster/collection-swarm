# LLM Router

**Module:** `src/collection_swarm/backends/router.py`

The `LLMRouter` is the central dispatch layer between agents and backends. It looks up the `ModelConfig` for a given model ID, resolves the appropriate backend, and forwards the completion request.

---

## Class: `LLMRouter`

### Constructor

```python
class LLMRouter:
    def __init__(
        self,
        models: dict[str, ModelConfig],
        backends: dict[str, LLMBackend] | None = None,
        cursor_sdk_prompts: CursorSdkPromptConfig | None = None,
    ) -> None
```

| Parameter | Type | Description |
|---|---|---|
| `models` | `dict[str, ModelConfig]` | Registry of all configured models, keyed by model ID |
| `backends` | `dict[str, LLMBackend] | None` | Optional pre-built backend mapping. If `None`, a `_BackendRegistry` is created with defaults |
| `cursor_sdk_prompts` | `CursorSdkPromptConfig | None` | Preamble config for the Cursor SDK backend (required if any model uses `cursor_sdk`) |

### Default Backend Registration

When `backends` is `None` (the typical case), the router creates a `_BackendRegistry` with two pre-loaded backends:

| Backend Key | Class | Notes |
|---|---|---|
| `"scripted"` | `ScriptedBackend` | Deterministic offline backend |
| `"heuristic"` | `ScriptedBackend` | Alias — same instance as `"scripted"` |

All other backends are lazily loaded on first access.

---

## Method: `complete`

```python
async def complete(
    self,
    model_id: str,
    messages: list[LLMMessage],
) -> LLMResponse
```

Dispatches a completion request to the appropriate backend.

| Parameter | Type | Description |
|---|---|---|
| `model_id` | `str` | Identifier for the model (must exist in `self.models`) |
| `messages` | `list[LLMMessage]` | Chat messages to send to the model |

**Returns:** `LLMResponse` from the resolved backend.

### Dispatch Flow

```
complete("nim-llama-3.1-70b", messages)
    │
    ├── 1. Look up ModelConfig by model_id
    │       models["nim-llama-3.1-70b"]
    │       → ModelConfig(backend="nim", ...)
    │
    ├── 2. Look up backend by ModelConfig.backend
    │       backends["nim"]
    │       → NimBackend (lazy-loaded)
    │
    └── 3. Call backend.complete(model, messages)
            → LLMResponse
```

### Error Handling

| Error | Condition | Message |
|---|---|---|
| `KeyError` | Unknown `model_id` | `"unknown model '{model_id}'"` |
| `KeyError` | No backend for `model.backend` | `"no backend configured for '{model.backend}'"` |

---

## `_BackendRegistry`

The `_BackendRegistry` is a specialized `dict` subclass that provides **lazy loading** for backends that require external dependencies or credentials.

```python
class _BackendRegistry(dict[str, LLMBackend]):
    def __init__(self, *args, cursor_sdk_prompts=None):
        super().__init__(*args)
        self.cursor_sdk_prompts = cursor_sdk_prompts

    def __missing__(self, backend_name: str) -> LLMBackend:
        # Lazy-load backends on first access
        ...
```

### Lazy Loading Behavior

| Backend Name | Import | Notes |
|---|---|---|
| `"cursor_sdk"` or `"acp"` | `from collection_swarm.backends.cursor_sdk import CursorSdkBackend` | Requires `cursor_sdk_prompts` to be set; registers under both `"cursor_sdk"` and `"acp"` keys |
| `"nim"` | `from collection_swarm.backends.nim import NimBackend` | Created with default NIM base URL |
| Anything else | — | Raises `KeyError` |

!!! tip "Why lazy loading?"
    The `NimBackend` depends on `litellm` and the `CursorSdkBackend` requires Node.js and the `@cursor/sdk` package. By deferring imports until the backend is actually needed, the application starts cleanly even when these dependencies aren't installed — useful for offline/scripted-only workflows.

### Backend Aliasing

The `"cursor_sdk"` and `"acp"` keys point to the **same** `CursorSdkBackend` instance. This supports legacy configurations that used `"acp"` as the backend name:

```python
if backend_name in {"cursor_sdk", "acp"}:
    backend = CursorSdkBackend(self.cursor_sdk_prompts)
    self["cursor_sdk"] = backend
    self["acp"] = backend
    return backend
```

---

## Usage in the Application

The router is typically created once in `runner.py` and shared across all agents:

```python
router = LLMRouter(
    config.models,
    cursor_sdk_prompts=config.prompts.cursor_sdk,
)

collector = CollectorAgent(router, cell.conversation_model, config.prompts.collector)
debtor = DebtorAgent(router, cell.conversation_model, config.prompts.debtor)
judge = Judge(router, cell.judge_model, config.prompts.judge)
```

!!! note "Model flexibility"
    The Collector and Debtor typically use the same `conversation_model`, while the Judge uses a separate `judge_model`. This allows using different models (or even different backends) for participants vs. evaluation.

---

## Related

- [Backend Overview](overview.md) — the `LLMBackend` protocol and `LLMResponse` dataclass
- [Scripted Backend](scripted.md) — default offline backend
- [NIM Backend](nim.md) — lazy-loaded NVIDIA backend
- [Cursor SDK Backend](cursor-sdk.md) — lazy-loaded Cursor SDK backend
