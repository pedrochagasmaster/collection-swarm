# `adversarial.py` — Profile hardening

<span class="cs-kicker">collection_swarm/adversarial.py</span>

The Profile-side counterpart to [`evolution.py`](evolution.md). Where
the evolver mutates Strategies based on tournament losses, the hardener
mutates Profiles to be more difficult based on transcripts where the
Collector won easily.

<dl class="cs-summary">
  <dt>Imports</dt><dd><code>re</code>, <code>yaml</code>, <code>uuid</code>, Pydantic, domain models</dd>
  <dt>Side effects</dt><dd>None directly; the runner persists results</dd>
  <dt>External dependency</dt><dd>An LLM (provided by the router)</dd>
</dl>

## `harden_profiles(easy_profiles, winning_transcripts, config, router)`

```python
async def harden_profiles(
    easy_profiles: list[Profile],
    winning_transcripts: list[str],
    config: HardeningConfig,
    router,
) -> list[Profile]: ...
```

Runs only when `config.enabled` is `True` (defaults to `False`). The
runner gates this on `hardening_config and hardening_config.enabled`, so
the most common case is "evolution loop without Profile hardening".

The function:

1. Picks the model — `config.hardener_model_id` if set, otherwise
   `local-scripted`.
2. Sends a single user message containing the seed Profiles and up to
   five winning transcripts.
3. Parses the response with `_parse_hardened_profiles()` into a list of
   dicts.
4. Validates each dict against `Profile.model_validate`. Skips any that
   fail validation.
5. Returns the validated Profiles, or `[_fallback_profile(easy_profiles)]`
   if nothing parsed.

## The hardener prompt

```python
def _build_hardener_prompt(profiles, transcripts) -> str:
    return (
        "Create harder but realistic debtor profile variants. Preserve each seed archetype unless a coherent reason is given.\n\n"
        f"SEED PROFILES:\n{[profile.model_dump(mode='json') for profile in profiles]}\n\n"
        f"WINNING TRANSCRIPTS:\n{transcripts[:5]}\n\n"
        "Return YAML as: profiles: [profile objects]."
    )
```

The "preserve archetype" instruction is load-bearing: without it, the
hardener tends to drift Profiles into archetypes that already exist,
which produces no new signal in the tournament.

## Parsing

```python
def _parse_hardened_profiles(output: str) -> list[dict]:
    match = re.search(r"```(?:yaml)?\s*(.*?)```", output, re.DOTALL)
    text = match.group(1) if match else output
    data = yaml.safe_load(text) or {}
    if isinstance(data, dict) and isinstance(data.get("profiles"), list):
        return [item for item in data["profiles"] if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []
```

Same forgiving shape as the evolver: fenced or bare, dict or list, only
keep dict items.

## Fallback profile

```python
def _fallback_profile(profiles: list[Profile]) -> Profile:
    parent = profiles[0]
    constraints = [*parent.constraints]
    constraints.append(Constraint(text="Só aceitará avançar após receber confirmação oficial por escrito."))
    return parent.model_copy(update={
        "id": f"hard_{parent.id}_{uuid4().hex[:6]}",
        "responsiveness": "medium",
        "primary_objection": "official_channel_request",
        "constraints": constraints,
    })
```

A clone of the easiest parent with one extra Constraint and a
`responsiveness` downgrade. The `hard_` prefix marks the lineage.

## Configuration

```python
class HardeningConfig(BaseModel):
    enabled: bool = False
    hardener_model_id: str | None = None
    max_drift: float = 200.0
    realism_check: bool = False
```

`max_drift` and `realism_check` are advisory fields reserved for future
use; the current hardener doesn't enforce drift bounds or realism
checks. PRs welcome.
