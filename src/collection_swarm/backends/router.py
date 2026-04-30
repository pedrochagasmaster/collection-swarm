"""Model router for all LLM backends."""

from __future__ import annotations

from collection_swarm.backends.base import LLMBackend, LLMResponse
from collection_swarm.backends.scripted import ScriptedBackend
from collection_swarm.models import CursorSdkPromptConfig, LLMMessage, ModelConfig


class _BackendRegistry(dict[str, LLMBackend]):
    def __init__(self, *args: object, cursor_sdk_prompts: CursorSdkPromptConfig | None = None) -> None:
        super().__init__(*args)
        self.cursor_sdk_prompts = cursor_sdk_prompts

    def __missing__(self, backend_name: str) -> LLMBackend:
        if backend_name in {"cursor_sdk", "acp"}:
            from collection_swarm.backends.cursor_sdk import CursorSdkBackend

            if self.cursor_sdk_prompts is None:
                raise KeyError(backend_name)
            backend = CursorSdkBackend(self.cursor_sdk_prompts)
            self["cursor_sdk"] = backend
            self["acp"] = backend
            return backend
        if backend_name == "nim":
            from collection_swarm.backends.nim import NimBackend

            backend = NimBackend()
            self[backend_name] = backend
            return backend
        raise KeyError(backend_name)


class LLMRouter:
    """Dispatch completions by model configuration."""

    def __init__(
        self,
        models: dict[str, ModelConfig],
        backends: dict[str, LLMBackend] | None = None,
        cursor_sdk_prompts: CursorSdkPromptConfig | None = None,
    ) -> None:
        self.models = models
        self.backends = backends or _BackendRegistry(
            {
                "scripted": ScriptedBackend(),
                "heuristic": ScriptedBackend(),
            },
            cursor_sdk_prompts=cursor_sdk_prompts,
        )

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
