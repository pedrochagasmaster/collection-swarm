from __future__ import annotations

import pytest

from collection_swarm.backends.cursor_sdk import CursorSdkBackend
from collection_swarm.backends.router import LLMRouter
from collection_swarm.models import CursorSdkPromptConfig, ModelConfig


def _cursor_prompts() -> CursorSdkPromptConfig:
    return CursorSdkPromptConfig(preamble="Reply with only your next assistant message text.")


def test_router_registers_cursor_sdk_backend() -> None:
    router = LLMRouter(
        {"cursor-test": ModelConfig(id="cursor-test", backend="cursor_sdk")},
        cursor_sdk_prompts=_cursor_prompts(),
    )

    assert isinstance(router.backends["cursor_sdk"], CursorSdkBackend)
    assert router.backends["acp"] is router.backends["cursor_sdk"]


async def test_cursor_sdk_backend_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CURSOR_API_KEY", "")

    with pytest.raises(RuntimeError, match="CURSOR_API_KEY is required"):
        await CursorSdkBackend(_cursor_prompts()).complete(
            ModelConfig(id="cursor-gpt-5.5-medium", backend="cursor_sdk", model_name="gpt-5.5-medium"),
            [],
        )
