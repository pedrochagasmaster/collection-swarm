"""Model router for all LLM backends."""

from __future__ import annotations

from collection_swarm.backends.acp import AcpBackend
from collection_swarm.backends.base import LLMBackend, LLMResponse
from collection_swarm.backends.nim import NimBackend
from collection_swarm.backends.scripted import ScriptedBackend
from collection_swarm.models import LLMMessage, ModelConfig


class LLMRouter:
    """Dispatch completions by model configuration."""

    def __init__(self, models: dict[str, ModelConfig], backends: dict[str, LLMBackend] | None = None) -> None:
        self.models = models
        self.backends = backends or {
            "scripted": ScriptedBackend(),
            "heuristic": ScriptedBackend(),
            "nim": NimBackend(),
            "acp": AcpBackend(),
        }

    async def complete(self, model_id: str, messages: list[LLMMessage]) -> LLMResponse:
        try:
            model = self.models[model_id]
        except KeyError as exc:
            raise KeyError(f"unknown model '{model_id}'") from exc
        try:
            backend = self.backends[model.backend]
        except KeyError as exc:
            raise KeyError(f"no backend configured for '{model.backend}'") from exc
        return await backend.complete(model, messages)
