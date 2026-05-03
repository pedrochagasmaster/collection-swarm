from __future__ import annotations

import pytest

from collection_swarm.credentials import CredentialStore
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


async def test_cursor_sdk_backend_reads_api_key_from_credential_store(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    store = CredentialStore(tmp_path / "credentials.sqlite")
    store.set_api_key("cursor", "stored-cursor-key")
    captured_env = {}

    async def fake_subprocess_exec(*args, **kwargs):
        captured_env.update(kwargs["env"])

        class Proc:
            returncode = 0

            async def communicate(self, payload):
                return (
                    b'{"content":"ok","inputTokens":1,"outputTokens":2}',
                    b"",
                )

        return Proc()

    monkeypatch.setattr("collection_swarm.backends.cursor_sdk._bridge_script", lambda: tmp_path / "run.mjs")
    (tmp_path / "run.mjs").write_text("console.log('ok')", encoding="utf-8")
    monkeypatch.setattr("collection_swarm.backends.cursor_sdk.shutil.which", lambda _: "/usr/bin/node")
    monkeypatch.setattr("collection_swarm.backends.cursor_sdk.asyncio.create_subprocess_exec", fake_subprocess_exec)

    response = await CursorSdkBackend(_cursor_prompts(), credential_store=store).complete(
        ModelConfig(id="cursor-gpt-5.5-medium", backend="cursor_sdk", model_name="gpt-5.5-medium"),
        [],
    )

    assert response.content == "ok"
    assert captured_env["CURSOR_API_KEY"] == "stored-cursor-key"
