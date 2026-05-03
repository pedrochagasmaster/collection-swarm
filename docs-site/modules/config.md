# `config.py` — YAML loading

<span class="cs-kicker">collection_swarm/config.py</span>

A small layer over PyYAML that turns the five files under `config/` into
typed Pydantic objects. Everything is eager — `load_app_config()` either
returns a fully validated `AppConfig` or raises.

<dl class="cs-summary">
  <dt>Imports</dt><dd>standard library, PyYAML, Pydantic, <code>collection_swarm.models</code></dd>
  <dt>Side effects</dt><dd>Filesystem reads only</dd>
  <dt>Default config dir</dt><dd><code>./config</code></dd>
</dl>

## `AppConfig`

```python
class AppConfig(BaseModel):
    profiles: dict[str, Profile]
    strategies: dict[str, Strategy]
    models: dict[str, ModelConfig]
    prompts: PromptConfig
    simulation: SimulationSettings = Field(default_factory=SimulationSettings)
```

Helper methods:

| Method                     | What it does                                                            |
| -------------------------- | ----------------------------------------------------------------------- |
| `profile(profile_id)`      | Returns the `Profile`, raises `KeyError` with a friendly message.       |
| `strategy(strategy_id)`    | Same for Strategies.                                                    |
| `model(model_id)`          | Same for Models.                                                        |
| `default_conversation_model` | First `scripted` backend, else first model in insertion order.       |
| `default_judge_model`        | First `heuristic` backend, else first `scripted`, else first model.   |

The defaults are intentionally deterministic so a freshly cloned repo
runs end-to-end with no API keys.

## File loaders

### `load_yaml(path)`

Resolves the path, raises `FileNotFoundError` if missing, returns the
parsed YAML or an empty dict for empty files.

### `_items_by_id(raw, key)`

Internal helper. Accepts:

- A mapping under `key` (e.g., `{ "profiles": [...] }` or
  `{ "profiles": { "id1": {...}, "id2": {...} } }`).
- A bare list of items.
- A bare mapping `{ id1: {...}, id2: {...} }`.

Returns a list of dicts ready for `Profile.model_validate`. Lifts the
mapping key into the item as `id` if the inner dict doesn't already have
one — that's why both the dict-style and list-style YAML layouts work.

### `load_profiles(path) -> dict[str, Profile]`
### `load_strategies(path) -> dict[str, Strategy]`

Validate every item, then index by `id`. Validation errors propagate.

### `load_models(path) -> dict[str, ModelConfig]`

Special-cases the tiered layout used by `config/models.yaml`:

```yaml
tiers:
  conversation:
    models:
      - id: local-scripted
        backend: scripted
  judge:
    models:
      - id: local-judge
        backend: heuristic
```

If `tiers` is present, the loader flattens every tier into one list. If
not, it falls back to `_items_by_id`. Either way, an empty model
dictionary raises `ValueError("at least one model must be configured")`.

### `load_prompts(path) -> PromptConfig`

Single `PromptConfig.model_validate` over the YAML root. Pydantic ensures
all four prompt subsections (`collector`, `debtor`, `judge`, `cursor_sdk`)
are present and well-formed.

### `load_simulation_settings(path) -> SimulationSettings`

The most permissive loader. Accepts either:

```yaml
conversation:
  max_turns: 12
  stalemate:
    window: 3
    similarity_threshold: 0.86
matrix:
  default_repetitions: 1
compliance:
  min_compliance_score: 0.8
  max_escalation_risk: 0.3
arena: {...}
objection_taxonomy: [...]
```

…or the older flat layout (`stalemate_window`, `stalemate_similarity_threshold`
under `conversation`). Both are normalized into a `SimulationSettings`
shape before validation.

## Composing it

```python
def load_app_config(config_dir: Path | str = DEFAULT_CONFIG_DIR) -> AppConfig:
    base = Path(config_dir)
    return AppConfig(
        profiles=load_profiles(base / "debtor_profiles.yaml"),
        strategies=load_strategies(base / "collector_strategies.yaml"),
        models=load_models(base / "models.yaml"),
        prompts=load_prompts(base / "prompts.yaml"),
        simulation=load_simulation_settings(base / "simulation.yaml"),
    )
```

Every CLI command, every API route, and every test that needs a real
config calls this exactly once. The resulting `AppConfig` is treated as
immutable for the lifetime of the call.

## Failure modes worth knowing

| Symptom                                              | Most common cause                                       |
| ---------------------------------------------------- | ------------------------------------------------------- |
| `expected profiles to be a list or mapping`         | Top-level YAML key is wrong, or a Profile is a string. |
| `at least one model must be configured`             | `models.yaml` is empty or only has empty tiers.        |
| `value is not a valid enumeration member`            | A `payment_outcome` literal doesn't match `PaymentOutcome`. |
| `unknown profile 'xyz'`                              | CLI `--profile` ID isn't in the loaded YAML.           |
| `Field required ... transcript`                      | A prompt section is missing the `transcript` template. |

All of these surface at config-load time — that's the design goal. A bad
YAML file should never produce a half-broken Simulation.
