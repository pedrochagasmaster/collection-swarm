from pathlib import Path

from collection_swarm.config import load_app_config


def test_load_default_config() -> None:
    config = load_app_config(Path("config"))

    assert "cooperative_hardship" in config.profiles
    assert "empathetic_payment_plan" in config.strategies
    assert config.default_conversation_model == "local-scripted"
    assert "professional debt collector" in config.prompts.collector.system
    assert "synthetic debt collection simulation" in config.prompts.debtor.system
    assert "Judge evaluator" in config.prompts.judge.system
    assert "structured simulation" in config.prompts.cursor_sdk.preamble
    assert config.simulation.conversation.max_turns >= 2
