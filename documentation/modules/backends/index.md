# Backends

<span class="cs-kicker">collection_swarm/backends/</span>

Five small files that together form the LLM transport layer.

| File                                          | Role                                                            |
| --------------------------------------------- | ---------------------------------------------------------------- |
| [`base.py`](base-and-router.md#basepy)        | The `LLMBackend` Protocol and the `LLMResponse` dataclass.       |
| [`router.py`](base-and-router.md#routerpy)    | The `LLMRouter` class and the lazy `_BackendRegistry`.          |
| [`scripted.py`](scripted.md)                  | Deterministic offline backend with role-aware canned responses. |
| [`nim.py`](nim.md)                            | NVIDIA NIM through `litellm.acompletion`.                        |
| [`cursor_sdk.py`](cursor-sdk.md)              | Cursor SDK via a Node.js subprocess bridge.                     |

The contract every backend implements:

```python
class LLMBackend(Protocol):
    async def complete(self, model: ModelConfig, messages: list[LLMMessage]) -> LLMResponse: ...
```

Three things to remember:

1. **One method, one shape.** The router calls `complete(model,
   messages)` and gets an `LLMResponse` back. No streaming, no
   tool-calling, no chat-completion shapes leaking up.
2. **The router decides the backend, the backend doesn't decide
   anything.** A backend is a leaf — it doesn't read configuration
   beyond the `ModelConfig` it's given.
3. **Token & cost accounting is always per-response.** Backends populate
   `input_tokens`, `output_tokens`, and `estimated_cost_usd` so the
   engine can sum across turns without any backend-specific code.
