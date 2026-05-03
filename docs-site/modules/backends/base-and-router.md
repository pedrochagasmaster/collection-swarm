# `backends/base.py` and `backends/router.py`

<span class="cs-kicker">collection_swarm/backends/</span>

The contract layer. Every other backend implements `base.LLMBackend`,
and every agent talks to backends through `router.LLMRouter`.

## `base.py`

40 lines. Two definitions and a re-export.

### `LLMResponse`

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

A frozen dataclass so it can be passed around safely. `model_id` is the
*configured* ID (e.g., `nim-mistral-large-3-675b`), not the
provider-facing model name. `backend` is the `ModelConfig.backend` value
(`scripted`, `heuristic`, `nim`, `cursor_sdk`). The token counters and
cost are zero by default — backends fill them when they have provider
data.

### `LLMBackend` Protocol

```python
class LLMBackend(Protocol):
    async def complete(self, model: ModelConfig, messages: list[LLMMessage]) -> LLMResponse:
        """Return a completion for the configured model."""
```

`Backend = LLMBackend` is exported as an alias for documentation.

## `router.py`

60 lines. One class, one private dict subclass.

### `_BackendRegistry`

A dict subclass that lazy-imports the heavy backends on first access:

```python
def __missing__(self, backend_name: str) -> LLMBackend:
    if backend_name in {"cursor_sdk", "acp"}:
        from collection_swarm.backends.cursor_sdk import CursorSdkBackend
        ...
    if backend_name == "nim":
        from collection_swarm.backends.nim import NimBackend
        ...
    raise KeyError(backend_name)
```

Two important behaviors:

- **Lazy imports.** The Cursor SDK backend imports a Node-side bridge
  and the NIM backend imports `litellm`. Neither cost is paid unless a
  matching model ID is actually used. Tests for the offline path don't
  pull either dependency in.
- **`acp` alias.** The same `CursorSdkBackend` answers to the legacy
  `acp` (Anthropic Cursor Proxy) backend name. New configs should use
  `cursor_sdk`.

The registry needs the `CursorSdkPromptConfig` to construct the bridge
backend. The router accepts it via the `cursor_sdk_prompts` keyword and
passes it down.

### `LLMRouter`

```python
class LLMRouter:
    def __init__(
        self,
        models: dict[str, ModelConfig],
        backends: dict[str, LLMBackend] | None = None,
        cursor_sdk_prompts: CursorSdkPromptConfig | None = None,
    ) -> None: ...
```

If `backends` is not provided, the router instantiates a default
`_BackendRegistry` pre-loaded with the offline backends:

```python
{
    "scripted": ScriptedBackend(),
    "heuristic": ScriptedBackend(),
}
```

Both `scripted` and `heuristic` resolve to the same `ScriptedBackend`
instance — the heuristic Judge is just the scripted backend reading the
Judge prompt and answering with a heuristic JSON.

### `complete()`

```python
async def complete(self, model_id: str, messages: list[LLMMessage]) -> LLMResponse:
    try:
        model = self.models[model_id]
    except KeyError as exc:
        raise KeyError(f"unknown model '{model_id}'") from exc
    try:
        backend = self.backends[model.backend]
    except KeyError as exc:
        raise KeyError(f"no backend configured for '{model.backend}'") from exc
    return await backend.complete(model, messages)
```

Two `KeyError`s, two friendly messages. The first catches bad model IDs
(typo in CLI flag); the second catches missing backend support.

## Why the `LLMRouter` exists

The agents could in principle import a specific backend directly. They
don't, for three reasons:

- **Per-cell model swapping.** The matrix runner instantiates a single
  router and reuses it across every `MatrixCell`. Each call picks the
  right backend at dispatch time.
- **Test ergonomics.** The test suite injects a `dict` of stub
  backends. No monkeypatching needed.
- **Lazy heavyweight imports.** As above, neither LiteLLM nor the Cursor
  SDK is loaded unless someone actually uses them.
