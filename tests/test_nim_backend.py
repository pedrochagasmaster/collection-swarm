from __future__ import annotations

import pytest

from collection_swarm.backends.nim import NimBackend
from collection_swarm.credentials import ApiKeyProvider
from collection_swarm.models import ModelConfig


class StaticKeys(ApiKeyProvider):
    def __init__(self, value: str | None) -> None:
        self.value = value

    def get_api_key(self, provider: str) -> str | None:
        assert provider == "nvidia_nim"
        return self.value


async def test_nim_backend_uses_configured_key_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    captured: dict[str, str] = {}

    async def fake_acompletion(**kwargs):
        captured["api_key"] = kwargs["api_key"]

        class Usage:
            prompt_tokens = 3
            completion_tokens = 5

        class Message:
            content = "ok"

        class Choice:
            message = Message()

        class Response:
            choices = [Choice()]
            usage = Usage()

        return Response()

    monkeypatch.setattr("collection_swarm.backends.nim.acompletion", fake_acompletion)

    response = await NimBackend(api_keys=StaticKeys("nim-dashboard-key")).complete(
        ModelConfig(id="nim-test", backend="nim", litellm_model="openai/test"),
        [],
    )

    assert captured["api_key"] == "nim-dashboard-key"
    assert response.content == "ok"
