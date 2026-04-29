from pathlib import Path

from collection_swarm.config import load_app_config


def test_load_default_config() -> None:
    config = load_app_config(Path("config"))

    assert "cooperative_hardship" in config.profiles
    assert "empathetic_payment_plan" in config.strategies
    assert len(config.profiles) >= 15
    assert len(config.strategies) >= 6
    assert config.default_conversation_model == "local-scripted"
    assert config.model("cursor-auto").backend == "acp"
    assert config.model("mistral-large-3-675b").backend == "nim"
    assert config.simulation.conversation.max_turns >= 2
    assert config.simulation.retry.max_retries >= 0
