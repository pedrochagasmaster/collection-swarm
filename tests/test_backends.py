from __future__ import annotations

import pytest

from collection_swarm.backends.acp import AcpBackend
from collection_swarm.models import LLMMessage, ModelConfig


def test_model_config_accepts_legacy_mode_alias() -> None:
    model = ModelConfig.model_validate({"id": "cursor-auto", "backend": "acp", "provider": "cursor", "mode": "ask"})

    assert model.acp_mode == "ask"


@pytest.mark.asyncio
async def test_acp_backend_reports_missing_agent_binary() -> None:
    backend = AcpBackend(command="definitely-not-agent-binary")
    model = ModelConfig(id="cursor-test", backend="acp", provider="cursor")

    with pytest.raises(RuntimeError, match="Cursor ACP command .* was not found"):
        await backend.complete(model, [LLMMessage(role="user", content="hello")])
