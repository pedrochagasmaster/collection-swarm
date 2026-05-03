from pathlib import Path


SITE_ROOT = Path("site")
INDEX = SITE_ROOT / "index.html"
STYLES = SITE_ROOT / "styles.css"
SCRIPT = SITE_ROOT / "app.js"
PAGES_WORKFLOW = Path(".github/workflows/pages.yml")

EXPECTED_MODULES = [
    "config.py",
    "models.py",
    "cli.py",
    "engine.py",
    "runner.py",
    "store.py",
    "arena.py",
    "evolution.py",
    "adversarial.py",
    "calibration.py",
    "model_evaluation.py",
    "env.py",
    "agents/collector.py",
    "agents/debtor.py",
    "agents/judge.py",
    "backends/base.py",
    "backends/router.py",
    "backends/scripted.py",
    "backends/nim.py",
    "backends/cursor_sdk.py",
    "analysis/statistics.py",
    "analysis/compliance.py",
    "analysis/objections.py",
    "analysis/playbook.py",
    "web/app.py",
    "web/seed.py",
    "web/static/index.html",
    "web/static/styles.css",
    "web/static/app.js",
    "cursor_sdk_bridge/run.mjs",
]

REQUIRED_CONCEPTS = [
    "Functional documentation",
    "Conceptual documentation",
    "Sequential module walkthrough",
    "Configuration layer",
    "Domain model layer",
    "Simulation runtime",
    "LLM backend layer",
    "Persistence layer",
    "Analysis layer",
    "Arena and evolution layer",
    "Web dashboard layer",
    "CLI surface",
    "Testing map",
]


def test_documentation_site_covers_every_project_module() -> None:
    html = INDEX.read_text(encoding="utf-8")

    missing_modules = [module for module in EXPECTED_MODULES if module not in html]
    missing_concepts = [concept for concept in REQUIRED_CONCEPTS if concept not in html]

    assert not missing_modules
    assert not missing_concepts


def test_documentation_site_has_assets_and_github_pages_workflow() -> None:
    assert INDEX.exists()
    assert STYLES.exists()
    assert SCRIPT.exists()
    assert PAGES_WORKFLOW.exists()

    workflow = PAGES_WORKFLOW.read_text(encoding="utf-8")
    assert "actions/upload-pages-artifact" in workflow
    assert "actions/deploy-pages" in workflow
    assert "path: site" in workflow
