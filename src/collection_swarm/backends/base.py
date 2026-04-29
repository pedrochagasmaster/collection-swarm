"""Shared backend interfaces."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from collection_swarm.models import LLMMessage, ModelConfig


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model_id: str = ""
    backend: str = ""


class LLMBackend(Protocol):
    async def complete(self, model: ModelConfig, messages: list[LLMMessage]) -> LLMResponse:
        """Return a completion for the configured model."""


Backend = LLMBackend
