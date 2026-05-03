# Configuration

> **Module:** `collection_swarm.config`
> **Source:** `src/collection_swarm/config.py`

The config module loads and validates all YAML configuration files into typed
Pydantic models. It provides a single entry point (`load_app_config`) that reads
profiles, strategies, models, prompts, and simulation settings from a config
directory.

---

## Overview

```
config/
├── debtor_profiles.yaml      → dict[str, Profile]
├── collector_strategies.yaml  → dict[str, Strategy]
├── models.yaml                → dict[str, ModelConfig]
├── prompts.yaml               → PromptConfig
└── simulation.yaml            → SimulationSettings
                                        │
                              ┌─────────▼──────────┐
                              │     AppConfig       │
                              │                     │
                              │  .profiles          │
                              │  .strategies        │
                              │  .models            │
                              │  .prompts           │
                              │  .simulation        │
                              └─────────────────────┘
```

---

## `load_app_config`

```python
def load_app_config(config_dir: Path | str = "config") -> AppConfig
```

The primary entry point. Loads all YAML files from the given directory and
returns a fully validated `AppConfig`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config_dir` | `Path` or `str` | `"config"` | Path to the configuration directory. |

**Returns:** `AppConfig`

**Raises:** `FileNotFoundError` if any required YAML file is missing.

### File Mapping

| YAML File | Loader Function | AppConfig Field |
|-----------|-----------------|-----------------|
| `debtor_profiles.yaml` | `load_profiles()` | `.profiles` |
| `collector_strategies.yaml` | `load_strategies()` | `.strategies` |
| `models.yaml` | `load_models()` | `.models` |
| `prompts.yaml` | `load_prompts()` | `.prompts` |
| `simulation.yaml` | `load_simulation_settings()` | `.simulation` |

### Example

```python
from collection_swarm.config import load_app_config

config = load_app_config("config")

print(f"Profiles:   {len(config.profiles)}")
print(f"Strategies: {len(config.strategies)}")
print(f"Models:     {len(config.models)}")
```

---

## `AppConfig`

```python
class AppConfig(BaseModel):
    profiles: dict[str, Profile]
    strategies: dict[str, Strategy]
    models: dict[str, ModelConfig]
    prompts: PromptConfig
    simulation: SimulationSettings
```

The central configuration object that all other modules depend on.

### Accessor Methods

These methods retrieve entities by ID and raise `KeyError` with a descriptive
message if the ID is not found.

#### `profile(profile_id: str) -> Profile`

```python
profile = config.profile("struggling_single_parent")
```

#### `strategy(strategy_id: str) -> Strategy`

```python
strategy = config.strategy("empathetic_negotiator")
```

#### `model(model_id: str) -> ModelConfig`

```python
model = config.model("gpt-4o")
```

!!! tip "Fail-fast validation"
    The runner module calls these accessors during matrix/tournament construction
    to validate all IDs before any simulations begin.

### Default Model Properties

#### `default_conversation_model -> str`

Returns the default model ID for collector/debtor agents.

**Selection logic:**

1. If any model has `backend == "scripted"`, return its ID.
2. Otherwise, return the first model in the configuration.

```python
model_id = config.default_conversation_model
```

#### `default_judge_model -> str`

Returns the default model ID for the judge.

**Selection logic:**

1. If any model has `backend == "heuristic"`, return its ID.
2. Else if any model has `backend == "scripted"`, return its ID.
3. Otherwise, return the first model in the configuration.

```python
judge_id = config.default_judge_model
```

---

## Individual Loaders

### `load_profiles`

```python
def load_profiles(path: Path) -> dict[str, Profile]
```

Loads debtor profiles from a YAML file. Supports both mapping and list formats.

**Mapping format** (keys become IDs automatically):

```yaml
struggling_single_parent:
  archetype: single_parent
  financial_situation: paycheck_to_paycheck
  debt_amount: 2500.00
  # ...

dispute_debtor:
  archetype: disputer
  # ...
```

**List format** (each item must include `id`):

```yaml
profiles:
  - id: struggling_single_parent
    archetype: single_parent
    # ...
  - id: dispute_debtor
    archetype: disputer
    # ...
```

---

### `load_strategies`

```python
def load_strategies(path: Path) -> dict[str, Strategy]
```

Loads collector strategies. Same format flexibility as profiles.

```yaml
empathetic_negotiator:
  tone: warm_and_understanding
  opening_approach: acknowledge_difficulty
  negotiation_tactic: find_middle_ground
  escalation_style: gentle_reminder
  concession_willingness: moderate
  compliance_adherence: strict
  follow_up_strategy: scheduled_callback
  # Optional fields
  payment_channel: pix_or_boleto
  primary_anchor: full_amount
  discovery_questions: open_ended
```

---

### `load_models`

```python
def load_models(path: Path) -> dict[str, ModelConfig]
```

Loads model configurations. Supports two YAML structures:

**Flat format:**

```yaml
models:
  - id: gpt-4o
    backend: litellm
    provider: openai
    input_cost_per_m: 2.50
    output_cost_per_m: 10.00
  - id: scripted-echo
    backend: scripted
```

**Tiered format:**

```yaml
tiers:
  premium:
    models:
      - id: gpt-4o
        backend: litellm
        provider: openai
        input_cost_per_m: 2.50
        output_cost_per_m: 10.00
  budget:
    models:
      - id: gpt-4o-mini
        backend: litellm
        provider: openai
        input_cost_per_m: 0.15
        output_cost_per_m: 0.60
```

!!! warning "At least one model required"
    `load_models` raises `ValueError` if the resulting model list is empty.

---

### `load_prompts`

```python
def load_prompts(path: Path) -> PromptConfig
```

Loads prompt templates for all agents. The YAML structure must match
`PromptConfig`:

```yaml
collector:
  system: "You are a professional debt collector..."
  history_empty: "This is the first contact."
  history: "Previous conversation:\n{history}"

debtor:
  system: "You are role-playing as a debtor..."
  constraints_empty: "- None"
  history_message: "Conversation so far:\n{history}"

judge:
  system: "You are an impartial judge..."
  transcript: "Evaluate the following transcript:\n{transcript}"

cursor_sdk:
  preamble: "You are a debt collection simulation assistant..."
```

---

### `load_simulation_settings`

```python
def load_simulation_settings(path: Path) -> SimulationSettings
```

Loads simulation parameters with normalization of nested YAML keys.

**Expected YAML structure:**

```yaml
conversation:
  max_turns: 20
  end_signal: "[END_CONVERSATION]"
  stalemate:
    window: 3
    similarity_threshold: 0.6

matrix:
  default_repetitions: 1

compliance:
  min_compliance_score: 0.8
  max_escalation_risk: 0.3

objection_taxonomy:
  - financial_hardship
  - dispute
  - avoidance

arena:
  default_format: swiss
  default_rounds: 4
  k_factor_initial: 32.0
  k_factor_stable: 16.0
  k_factor_threshold: 30
  scoring: payment_x_compliance
```

#### Normalization Details

The loader handles two styles of stalemate configuration:

**Nested style** (preferred):

```yaml
conversation:
  stalemate:
    window: 3
    similarity_threshold: 0.6
```

**Flat style** (also supported):

```yaml
conversation:
  stalemate_window: 3
  stalemate_similarity_threshold: 0.6
```

The `default_repetitions` field can appear either at the top level or under
`matrix`:

```yaml
# Either of these:
default_repetitions: 3
matrix:
  default_repetitions: 3
```

---

## YAML Normalization: `_items_by_id`

```python
def _items_by_id(raw: Any, key: str) -> list[dict[str, Any]]
```

A private helper that normalizes YAML data into a list of dictionaries with `id`
fields, regardless of the input format.

### Supported Input Formats

**1. Dict-of-dicts** (keys become `id` fields):

```python
raw = {
    "strat_a": {"tone": "warm"},
    "strat_b": {"tone": "firm"},
}
# Returns: [{"id": "strat_a", "tone": "warm"}, {"id": "strat_b", "tone": "firm"}]
```

**2. Wrapped dict-of-dicts** (unwrapped by key):

```python
raw = {
    "strategies": {
        "strat_a": {"tone": "warm"},
    }
}
# _items_by_id(raw, "strategies") → same as above
```

**3. List of dicts** (passed through):

```python
raw = [{"id": "strat_a", "tone": "warm"}]
# Returns: [{"id": "strat_a", "tone": "warm"}]
```

Raises `ValueError` if the data is neither a dict nor a list.

---

## `load_yaml`

```python
def load_yaml(path: Path) -> Any
```

Low-level YAML loader used by all other loaders.

- Raises `FileNotFoundError` if the file does not exist.
- Uses `yaml.safe_load` for security (no arbitrary Python object
  deserialization).
- Returns an empty dict for empty files.

---

## Complete Usage Example

```python
from collection_swarm.config import load_app_config

config = load_app_config("config")

# Access all profiles
for pid, profile in config.profiles.items():
    print(f"{pid}: {profile.archetype} (${profile.debt_amount:,.2f})")

# Access a specific strategy
strategy = config.strategy("empathetic_negotiator")
print(f"Tone: {strategy.tone}")
print(f"Tactic: {strategy.negotiation_tactic}")

# Check simulation settings
settings = config.simulation
print(f"Max turns: {settings.conversation.max_turns}")
print(f"Stalemate window: {settings.conversation.stalemate_window}")
print(f"Min compliance: {settings.min_compliance_score}")

# Model info
for mid, model in config.models.items():
    print(f"{mid}: backend={model.backend}, "
          f"cost=${model.input_cost_per_m}/{model.output_cost_per_m} per M tokens")

# Default models
print(f"Default conversation model: {config.default_conversation_model}")
print(f"Default judge model: {config.default_judge_model}")
```
