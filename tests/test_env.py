from __future__ import annotations

import os

from collection_swarm.env import load_dotenv_if_present


def test_load_dotenv_if_present_loads_simple_values(tmp_path, monkeypatch) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("A_KEY=plain\nQUOTED_KEY='quoted value'\n# ignored\n", encoding="utf-8")
    monkeypatch.delenv("A_KEY", raising=False)
    monkeypatch.delenv("QUOTED_KEY", raising=False)

    load_dotenv_if_present(dotenv)

    assert os.environ["A_KEY"] == "plain"
    assert os.environ["QUOTED_KEY"] == "quoted value"


def test_load_dotenv_if_present_does_not_override_existing_values(tmp_path, monkeypatch) -> None:
    dotenv = tmp_path / ".env"
    dotenv.write_text("A_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("A_KEY", "from-env")

    load_dotenv_if_present(dotenv)

    assert os.environ["A_KEY"] == "from-env"
