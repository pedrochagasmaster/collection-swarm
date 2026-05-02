"""Adversarial debtor profile hardening."""

from __future__ import annotations

import re

import yaml
from uuid import uuid4

from pydantic import ValidationError

from collection_swarm.models import Constraint
from collection_swarm.models import HardeningConfig, LLMMessage, Profile


async def harden_profiles(
    easy_profiles: list[Profile],
    winning_transcripts: list[str],
    config: HardeningConfig,
    router,
) -> list[Profile]:
    model_id = config.hardener_model_id or "local-scripted"
    response = await router.complete(model_id, [LLMMessage(role="user", content=_build_hardener_prompt(easy_profiles, winning_transcripts))])
    profiles: list[Profile] = []
    for item in _parse_hardened_profiles(response.content):
        try:
            profile = Profile.model_validate(item)
        except ValidationError:
            continue
        profiles.append(profile)
    if profiles:
        return profiles
    return [_fallback_profile(easy_profiles)]


def _build_hardener_prompt(profiles: list[Profile], transcripts: list[str]) -> str:
    return (
        "Create harder but realistic debtor profile variants. Preserve each seed archetype unless a coherent reason is given.\n\n"
        f"SEED PROFILES:\n{[profile.model_dump(mode='json') for profile in profiles]}\n\n"
        f"WINNING TRANSCRIPTS:\n{transcripts[:5]}\n\n"
        "Return YAML as: profiles: [profile objects]."
    )


def _parse_hardened_profiles(output: str) -> list[dict]:
    match = re.search(r"```(?:yaml)?\s*(.*?)```", output, re.DOTALL)
    text = match.group(1) if match else output
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return []
    if isinstance(data, dict) and isinstance(data.get("profiles"), list):
        return [item for item in data["profiles"] if isinstance(item, dict)]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _fallback_profile(profiles: list[Profile]) -> Profile:
    if not profiles:
        raise ValueError("Cannot create fallback profile without at least one parent")
    parent = profiles[0]
    constraints = [*parent.constraints]
    constraints.append(Constraint(text="Só aceitará avançar após receber confirmação oficial por escrito."))
    return parent.model_copy(
        update={
            "id": f"hard_{parent.id}_{uuid4().hex[:6]}",
            "responsiveness": "medium",
            "primary_objection": "official_channel_request",
            "constraints": constraints,
        }
    )
