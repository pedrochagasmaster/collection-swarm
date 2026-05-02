from __future__ import annotations

import pytest

from collection_swarm.adversarial import HardeningConfig, harden_profiles
from collection_swarm.backends.base import LLMResponse
from collection_swarm.models import LLMMessage, Profile, ProfileLineage
from collection_swarm.store import SimulationStore


class CannedRouter:
    async def complete(self, model_id: str, messages: list[LLMMessage]) -> LLMResponse:
        return LLMResponse(
            content="""
profiles:
  - id: hardened_cooperative
    archetype: cooperative
    financial_situation: hardship
    debt_amount: 850
    debt_age_days: 75
    debt_type: credito_pessoal_will
    prior_contact_count: 2
    emotional_state: anxious_but_guarded
    primary_objection: official_channel_request
    responsiveness: medium
    demographics: nordeste_classe_c_mae_provedora
    backstory: Needs official proof and tighter installment terms.
    constraints:
      - text: Só aceitará boleto oficial depois de receber confirmação por escrito.
""",
            model_id=model_id,
            backend="test",
        )


def _profile() -> Profile:
    return Profile(
        id="cooperative_hardship",
        archetype="cooperative",
        financial_situation="hardship",
        debt_amount=850,
        debt_age_days=75,
        debt_type="credito_pessoal_will",
        prior_contact_count=1,
        emotional_state="anxious",
        primary_objection="inability_to_pay",
        responsiveness="high",
        demographics="nordeste_classe_c_mae_provedora",
        backstory="Needs time.",
    )


@pytest.mark.asyncio
async def test_harden_profiles_produces_valid_profiles() -> None:
    profiles = await harden_profiles(
        [_profile()], [], HardeningConfig(hardener_model_id="local-scripted"), CannedRouter()
    )

    assert profiles[0].id == "hardened_cooperative"
    assert profiles[0].archetype == "cooperative"
    assert profiles[0].constraints


def test_store_saves_evolved_profile(tmp_path) -> None:
    store = SimulationStore(tmp_path / "runs.sqlite")
    lineage = ProfileLineage(
        profile_id="hardened_cooperative",
        parent_id="cooperative_hardship",
        generation=1,
        hardening_type="objection_addition",
        hardening_description="Added written proof requirement.",
    )

    store.save_evolved_profile(_profile().model_copy(update={"id": "hardened_cooperative"}), lineage)

    profiles = store.list_evolved_profiles()
    assert profiles[0][0].id == "hardened_cooperative"
    assert profiles[0][1].parent_id == "cooperative_hardship"
