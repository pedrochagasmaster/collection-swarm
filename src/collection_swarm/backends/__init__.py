"""LLM backend implementations."""

from collection_swarm.backends.base import LLMResponse
from collection_swarm.backends.router import LLMRouter

__all__ = ["LLMResponse", "LLMRouter"]
