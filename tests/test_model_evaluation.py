from __future__ import annotations

import json

from collection_swarm.config import load_app_config
from collection_swarm.model_evaluation import (
    build_model_role_report,
    configured_cursor_model_statuses,
    render_markdown_report,
    write_report,
)
from collection_swarm.models import ModelConfig


def test_configured_cursor_status_flags_stale_model_name() -> None:
    config = load_app_config("config")
    stale = ModelConfig(
        id="cursor-stale",
        backend="cursor_sdk",
        provider="openai",
        model_name="gpt-5.5-medium",
    )
    test_config = config.model_copy(update={"models": {"cursor-stale": stale}})

    statuses = configured_cursor_model_statuses(test_config, available_model_ids=("gpt-5.5",))

    assert statuses[0].live_status == "fails"
    assert "gpt-5.5" in statuses[0].action


def test_baseline_report_recommends_gpt_55_for_all_roles() -> None:
    report = build_model_role_report(load_app_config("config"))

    assert report.recommendations == {
        "collector": "gpt-5.5",
        "debtor": "gpt-5.5",
        "judge": "gpt-5.5",
    }


def test_render_markdown_report_includes_config_health() -> None:
    report = build_model_role_report(load_app_config("config"))

    markdown = render_markdown_report(report)

    assert "# Cursor Model Role Evaluation" in markdown
    assert "## Configuration Health" in markdown
    assert "`cursor-composer-2`" in markdown


def test_write_json_report(tmp_path) -> None:
    report = build_model_role_report(load_app_config("config"))
    path = tmp_path / "model-report.json"

    write_report(report, path, report_format="json")

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["recommendations"]["judge"] == "gpt-5.5"
    assert data["assessments"]
