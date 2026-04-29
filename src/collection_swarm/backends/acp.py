"""Cursor ACP backend placeholder.

The application is usable with the scripted backend out of the box and with NIM
when credentials are present. ACP process management is intentionally explicit so
users do not get a silent fallback to an unintended model.
"""

from __future__ import annotations

from collection_swarm.backends.base import LLMBackend, LLMResponse
from collection_swarm.models import LLMMessage, ModelConfig


class AcpBackend(LLMBackend):
    async def complete(self, model: ModelConfig, messages: list[LLMMessage]) -> LLMResponse:
        raise RuntimeError(
            "ACP backend is not implemented in this build. Use the scripted backend "
            "for local simulations or a nim model with NVIDIA_NIM_API_KEY."
        )
