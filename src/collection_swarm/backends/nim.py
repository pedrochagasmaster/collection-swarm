"""NVIDIA NIM backend using LiteLLM."""

from __future__ import annotations

import os

from litellm import acompletion

from collection_swarm.backends.base import LLMResponse
from collection_swarm.credentials import ApiKeyProvider
from collection_swarm.env import load_dotenv_if_present
from collection_swarm.models import LLMMessage, ModelConfig


class NimBackend:
    def __init__(
        self,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        api_keys: ApiKeyProvider | None = None,
    ) -> None:
        self.base_url = base_url
        self.api_keys = api_keys

    async def complete(self, model: ModelConfig, messages: list[LLMMessage]) -> LLMResponse:
        load_dotenv_if_present()
        api_key = self.api_keys.get_api_key("nvidia_nim") if self.api_keys else os.getenv("NVIDIA_NIM_API_KEY")
        if not api_key:
            raise RuntimeError("NVIDIA_NIM_API_KEY is required for NIM models")

        response = await acompletion(
            model=model.litellm_model,
            messages=[message.model_dump() for message in messages],
            api_key=api_key,
            base_url=self.base_url,
        )
        choice = response.choices[0]
        content = choice.message.content or ""
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=_estimate_cost(model, input_tokens, output_tokens),
            model_id=model.id,
            backend="nim",
        )


def _estimate_cost(model: ModelConfig, input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000 * model.input_cost_per_m) + (
        output_tokens / 1_000_000 * model.output_cost_per_m
    )
