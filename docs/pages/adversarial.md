---
title: Adversarial Hardening
layout: default
nav_order: 13
---

# Adversarial Profile Hardening
{: .no_toc }

LLM-driven generation of tougher debtor profiles to stress-test collection strategies.
{: .fs-6 .fw-300 }

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
1. TOC
{:toc}
</details>

---

**Source:** `src/collection_swarm/adversarial.py`

## Overview

Adversarial hardening creates **tougher but realistic** debtor profile variants. The goal is to stress-test collection strategies against edge cases that manual profile design might miss. A hardened profile should be harder to collect from while remaining a plausible real-world consumer.

## How It Works

### harden_profiles

```python
async def harden_profiles(
    easy_profiles: list[Profile],
    winning_transcripts: list[str],
    config: HardeningConfig,
    router,
) -> list[Profile]
```

1. Takes "easy" profiles (those that strategies handle well) and winning transcript examples.
2. Sends a prompt to the LLM asking for harder variants.
3. Parses the YAML response for profile objects.
4. Validates each against the `Profile` model.
5. Returns valid profiles, or a fallback if parsing fails.

### Hardener Prompt

```
Create harder but realistic debtor profile variants.
Preserve each seed archetype unless a coherent reason is given.

SEED PROFILES:
[JSON dump of profiles]

WINNING TRANSCRIPTS:
[transcript excerpts]

Return YAML as: profiles: [profile objects].
```

The instruction to "preserve each seed archetype" ensures the LLM doesn't radically change the character of a profile — it should make a cooperative debtor harder to convert, not transform them into a hostile one.

## Fallback Profile

If the LLM fails to produce valid YAML, a deterministic fallback is generated:

```python
def _fallback_profile(profiles: list[Profile]) -> Profile:
    parent = profiles[0]
    constraints = [*parent.constraints]
    constraints.append(Constraint(
        text="Só aceitará avançar após receber confirmação oficial por escrito."
    ))
    return parent.model_copy(
        update={
            "id": f"hard_{parent.id}_{uuid4().hex[:6]}",
            "responsiveness": "medium",
            "primary_objection": "official_channel_request",
            "constraints": constraints,
        }
    )
```

The fallback:
- Adds a constraint requiring written confirmation before proceeding.
- Reduces responsiveness to "medium".
- Changes the primary objection to requiring official channels.
- Generates an ID with the `hard_` prefix.

## HardeningConfig

| Parameter | Default | Description |
|:----------|:--------|:------------|
| `enabled` | False | Whether hardening is active |
| `hardener_model_id` | None | LLM model for generating profiles |
| `max_drift` | 200.0 | Maximum Elo drift from parent (reserved) |
| `realism_check` | False | Whether to validate realism (reserved) |

## Integration with Evolution

Profile hardening is optionally integrated into the evolution cycle. When `hardening_config.enabled` is True, the runner:

1. Selects the easiest profiles (bottom-k by Elo).
2. Calls `harden_profiles()` with those profiles.
3. Saves the hardened profiles with `ProfileLineage` tracking.
4. Adds hardened profiles to the active pool for subsequent tournament rounds.

## Profile Lineage

Each hardened profile has a `ProfileLineage` record:

```python
lineage = ProfileLineage(
    profile_id=profile.id,
    parent_id=parent_id,
    generation=generation,
    hardening_type="llm",
    hardening_description="Generated from successful collection transcripts.",
)
```

This enables tracing hardened profiles back to their seed parents and understanding how the profile pool evolved.
