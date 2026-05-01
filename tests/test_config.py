from pathlib import Path

from collection_swarm.config import load_app_config


def test_load_default_config() -> None:
    config = load_app_config(Path("config"))

    assert "cooperative_hardship" in config.profiles
    assert "empathetic_payment_plan" in config.strategies
    assert config.default_conversation_model == "local-scripted"
    # Prompts are Brazilian-Portuguese and Will-Bank-aware after the
    # liquidation context redesign (see docs/willbank-research-dossier.md).
    assert "agente de cobran\u00e7a profissional" in config.prompts.collector.system
    assert "Will Bank" in config.prompts.collector.system
    assert "simula\u00e7\u00e3o sint\u00e9tica de cobran\u00e7a" in config.prompts.debtor.system
    assert "Juiz avaliador" in config.prompts.judge.system
    assert "simula\u00e7\u00e3o estruturada" in config.prompts.cursor_sdk.preamble
    assert config.simulation.conversation.max_turns >= 2
