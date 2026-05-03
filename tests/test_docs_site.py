"""Contract test for the Collection Swarm documentation site.

This test verifies the structure of the MkDocs documentation source — not the
built HTML — so it runs cheaply in CI without requiring a MkDocs install.
It keeps the docs in sync with the codebase: every module mentioned below
must be documented in ``docs-site/modules/``.
"""

from __future__ import annotations

from pathlib import Path

DOCS_ROOT = Path("docs-site")
MKDOCS_CONFIG = Path("mkdocs.yml")
PAGES_WORKFLOW = Path(".github/workflows/docs.yml")

REQUIRED_PAGES = [
    "index.md",
    "getting-started/index.md",
    "getting-started/install.md",
    "getting-started/live-models.md",
    "getting-started/dashboard.md",
    "getting-started/troubleshooting.md",
    "concepts/index.md",
    "concepts/vocabulary.md",
    "concepts/domain-model.md",
    "concepts/conversation-lifecycle.md",
    "concepts/compliance.md",
    "concepts/arena-and-evolution.md",
    "concepts/judge-calibration.md",
    "modules/index.md",
    "modules/models.md",
    "modules/config.md",
    "modules/env.md",
    "modules/engine.md",
    "modules/store.md",
    "modules/runner.md",
    "modules/arena.md",
    "modules/evolution.md",
    "modules/adversarial.md",
    "modules/calibration.md",
    "modules/model-evaluation.md",
    "modules/cli.md",
    "modules/agents/collector.md",
    "modules/agents/debtor.md",
    "modules/agents/judge.md",
    "modules/backends/base-and-router.md",
    "modules/backends/scripted.md",
    "modules/backends/nim.md",
    "modules/backends/cursor-sdk.md",
    "modules/analysis/statistics.md",
    "modules/analysis/compliance.md",
    "modules/analysis/objections.md",
    "modules/analysis/playbook.md",
    "modules/web/app.md",
    "modules/web/seed.md",
    "modules/web/static.md",
    "catalog/profiles.md",
    "catalog/strategies.md",
    "reference/cli.md",
    "reference/api.md",
    "reference/configuration.md",
    "reference/database.md",
    "reference/glossary.md",
]

REQUIRED_THEME_ASSETS = [
    "stylesheets/theme.css",
]


def test_every_required_doc_page_exists() -> None:
    missing = [p for p in REQUIRED_PAGES if not (DOCS_ROOT / p).is_file()]
    assert not missing, f"Missing doc pages: {missing}"


def test_theme_assets_exist() -> None:
    missing = [a for a in REQUIRED_THEME_ASSETS if not (DOCS_ROOT / a).is_file()]
    assert not missing, f"Missing theme assets: {missing}"


def test_mkdocs_config_and_workflow_are_wired_correctly() -> None:
    assert MKDOCS_CONFIG.exists(), "mkdocs.yml is missing"
    assert PAGES_WORKFLOW.exists(), "Pages deploy workflow is missing"

    config = MKDOCS_CONFIG.read_text(encoding="utf-8")
    assert "docs_dir: docs-site" in config
    assert "name: material" in config
    assert "extra_css:" in config
    assert "stylesheets/theme.css" in config

    workflow = PAGES_WORKFLOW.read_text(encoding="utf-8")
    assert "mkdocs build --strict" in workflow
    assert "actions/upload-pages-artifact" in workflow
    assert "actions/deploy-pages" in workflow


def test_home_page_links_to_core_sections() -> None:
    home = (DOCS_ROOT / "index.md").read_text(encoding="utf-8")
    for required_link in [
        "getting-started/install.md",
        "concepts/index.md",
        "modules/index.md",
        "catalog/profiles.md",
        "reference/index.md",
    ]:
        assert required_link in home, f"Home page missing link to {required_link}"
