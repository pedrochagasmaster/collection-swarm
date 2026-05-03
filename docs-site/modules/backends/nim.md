# `backends/nim.py` — NVIDIA NIM via LiteLLM

<span class="cs-kicker">collection_swarm/backends/nim.py</span>

A 50-line wrapper around `litellm.acompletion` pointed at NVIDIA's
OpenAI-compatible inference endpoint at
`https://integrate.api.nvidia.com/v1`.

<dl class="cs-summary">
  <dt>Imports</dt><dd><code>litellm.acompletion</code>, <code>collection_swarm.env</code>, <code>collection_swarm.secrets.resolve_api_key</code>, domain models</dd>
  <dt>Network</dt><dd>Yes — needs <code>NVIDIA_NIM_API_KEY</code></dd>
  <dt>Cost accounting</dt><dd>Computed from <code>ModelConfig.input_cost_per_m</code> and <code>output_cost_per_m</code></dd>
</dl>

## `NimBackend.complete()`

```python
async def complete(self, model: ModelConfig, messages: list[LLMMessage]) -> LLMResponse:
    load_dotenv_if_present()
    api_key = resolve_api_key("NVIDIA_NIM_API_KEY")
    if not api_key:
        raise RuntimeError("NVIDIA_NIM_API_KEY is required for NIM models")

    response = await acompletion(
        model=model.litellm_model,
        messages=[message.model_dump() for message in messages],
        api_key=api_key,
        base_url=self.base_url,
    )
    choice = response.choices[0]
    content = choice.message.content or ""
    usage = getattr(response, "usage", None)
    input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    return LLMResponse(
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=_estimate_cost(model, input_tokens, output_tokens),
        model_id=model.id,
        backend="nim",
    )
```

The function resolves its API key on every call via `resolve_api_key()`,
which checks the database first, then environment variables. This means
keys stored through the dashboard or CLI are picked up immediately
without a process restart.

## `model.litellm_model`

```python
@property
def litellm_model(self) -> str:
    return self.model_name or self.id
```

LiteLLM expects an OpenAI-compatible model string. The shipped
`config/models.yaml` uses the `openai/...` prefix to tell LiteLLM to
treat NVIDIA's endpoint as OpenAI-compatible:

```yaml
- id: nim-mistral-large-3-675b
  backend: nim
  model_name: openai/mistralai/mistral-large-3-675b-instruct-2512
```

If `model_name` is omitted (typical for the `cursor-…` rows), the
backend would fall back to the user-facing ID, which would be wrong for
LiteLLM. Always set `model_name` for NIM rows.

## Cost estimation

```python
def _estimate_cost(model: ModelConfig, input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000 * model.input_cost_per_m) + (
        output_tokens / 1_000_000 * model.output_cost_per_m
    )
```

The shipped `models.yaml` uses zero costs for every entry — overwrite
them locally if you need cost reporting. The Playbook and dashboard sum
`estimated_cost_usd` across all runs, so accurate per-million pricing
gets you accurate totals.

## Error handling

There is no retry loop on purpose. A failure here propagates up to the
engine, the engine flips the result to `failed`, and the row lands in
SQLite with the error message attached. The matrix runner then has the
information it needs to backfill on the next pass without losing the
record of what failed.

If you need retries, wrap the backend rather than editing it — the
router accepts any `LLMBackend` Protocol implementer.

## Operational notes

- LiteLLM caches some metadata under `~/.cache/litellm`. Safe to
  delete; it'll rebuild on the next call.
- NIM occasionally returns empty `usage` payloads. The `getattr` chain
  defaults both counters to zero so the engine still records a
  successful turn.
- A 404 typically means the `model_name` is stale. Query NVIDIA's
  `/v1/models` and update the YAML.
