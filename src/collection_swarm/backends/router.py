"""Model router for all LLM backends."""

from __future__ import annotations

from collection_swarm.backends.base import LLMBackend, LLMResponse
from collection_swarm.backends.cursor_sdk import CursorSdkBackend
from collection_swarm.backends.nim import NimBackend
from collection_swarm.backends.scripted import ScriptedBackend
from collection_swarm.models import LLMMessage, ModelConfig


class LLMRouter:
    """Dispatch completions by model configuration."""

    def __init__(self, models: dict[str, ModelConfig], backends: dict[str, LLMBackend] | None = None) -> None:
        self.models = models
        cursor_sdk = CursorSdkBackend()
        self.backends = backends or {
            "scripted": ScriptedBackend(),
            "heuristic": ScriptedBackend(),
            "nim": NimBackend(),
            "cursor_sdk": cursor_sdk,
            "acp": cursor_sdk,
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
