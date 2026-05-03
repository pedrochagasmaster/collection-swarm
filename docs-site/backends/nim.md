# NIM Backend

**Module:** `src/collection_swarm/backends/nim.py`

The `NimBackend` connects Collection Swarm to **NVIDIA NIM** (NVIDIA Inference Microservices) for production-grade LLM inference. It uses [LiteLLM](https://github.com/BerriAI/litellm) as the HTTP client, providing access to NVIDIA-hosted models via an OpenAI-compatible API.

---

## Class: `NimBackend`

### Constructor

```python
class NimBackend:
    def __init__(
        self,
        base_url: str = "https://integrate.api.nvidia.com/v1",
    ) -> None
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `base_url` | `str` | `https://integrate.api.nvidia.com/v1` | NVIDIA NIM API endpoint |

---

## Prerequisites

### Environment Variable

| Variable | Required | Description |
|---|---|---|
| `NVIDIA_NIM_API_KEY` | **Yes** | API key for NVIDIA NIM. Obtain from [build.nvidia.com](https://build.nvidia.com/) |

The backend calls `load_dotenv_if_present()` before checking the environment variable, so keys can be placed in a `.env` file.

!!! failure "Missing API key"
    If `NVIDIA_NIM_API_KEY` is not set, the backend raises:

    ```
    RuntimeError: NVIDIA_NIM_API_KEY is required for NIM models
    ```

### Python Dependencies

| Package | Purpose |
|---|---|
| `litellm` | OpenAI-compatible async HTTP client for LLM APIs |

---

## Method: `complete`

```python
async def complete(
    self,
    model: ModelConfig,
    messages: list[LLMMessage],
) -> LLMResponse
```

Sends a chat completion request to NVIDIA NIM via LiteLLM.

### Request Flow

```
complete(model, messages)
    │
    ├── 1. Load .env if present
    │
    ├── 2. Check NVIDIA_NIM_API_KEY
    │
    ├── 3. Call litellm.acompletion(
    │       model=model.litellm_model,
    │       messages=[...],
    │       api_key=api_key,
    │       base_url=self.base_url,
    │   )
    │
    ├── 4. Extract content, token counts
    │
    └── 5. Return LLMResponse
```

### LiteLLM Integration

The backend uses `litellm.acompletion` (async completion):

```python
response = await acompletion(
    model=model.litellm_model,      # e.g., "nvidia/llama-3.1-70b-instruct"
    messages=[m.model_dump() for m in messages],
    api_key=api_key,
    base_url=self.base_url,
)
```

The `model.litellm_model` property returns the `model_name` field from `ModelConfig` if set, otherwise the `id`. NVIDIA NIM models typically use the `nvidia/` prefix convention (e.g., `nvidia/llama-3.1-70b-instruct`).

### Response Mapping

| LiteLLM Field | `LLMResponse` Field | Handling |
|---|---|---|
| `response.choices[0].message.content` | `content` | Falls back to `""` if `None` |
| `response.usage.prompt_tokens` | `input_tokens` | Coerced to `int`, defaults to `0` |
| `response.usage.completion_tokens` | `output_tokens` | Coerced to `int`, defaults to `0` |
| _(computed)_ | `estimated_cost_usd` | Calculated from `ModelConfig` rates |
| `model.id` | `model_id` | From the config, not the API response |
| `"nim"` | `backend` | Hardcoded identifier |

---

## Cost Estimation

```python
def _estimate_cost(model, input_tokens, output_tokens) -> float:
    return (
        (input_tokens / 1_000_000 * model.input_cost_per_m)
        + (output_tokens / 1_000_000 * model.output_cost_per_m)
    )
```

Costs are calculated using the per-million-token rates defined in `ModelConfig`:

| Field | Unit | Example |
|---|---|---|
| `input_cost_per_m` | USD per 1M input tokens | `0.35` |
| `output_cost_per_m` | USD per 1M output tokens | `0.40` |

!!! example "Cost calculation"
    For a request with 2,000 input tokens and 500 output tokens using a model with rates `0.35` / `0.40`:

    ```
    cost = (2000 / 1_000_000 × 0.35) + (500 / 1_000_000 × 0.40)
         = 0.0007 + 0.0002
         = $0.0009
    ```

---

## Model Configuration Example

```yaml
# config/models.yaml
tiers:
  cloud:
    models:
      - id: nim-llama-3.1-70b
        backend: nim
        provider: nvidia
        model_name: nvidia/llama-3.1-70b-instruct
        input_cost_per_m: 0.35
        output_cost_per_m: 0.40

      - id: nim-nemotron-70b
        backend: nim
        provider: nvidia
        model_name: nvidia/nemotron-4-340b-instruct
        input_cost_per_m: 4.20
        output_cost_per_m: 4.20
```

---

## Lazy Loading

The `NimBackend` is **lazy-loaded** by the router's `_BackendRegistry`. It is only imported and instantiated when a model with `backend: nim` is first used:

```python
# In _BackendRegistry.__missing__
if backend_name == "nim":
    from collection_swarm.backends.nim import NimBackend
    backend = NimBackend()
    self[backend_name] = backend
    return backend
```

This means `litellm` does not need to be installed unless NIM models are actually used.

---

## Related

- [Backend Overview](overview.md) — the `LLMBackend` protocol and `LLMResponse` dataclass
- [LLM Router](router.md) — how backends are lazily loaded and dispatched
- [Cursor SDK Backend](cursor-sdk.md) — alternative cloud backend
