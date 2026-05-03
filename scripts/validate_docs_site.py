from __future__ import annotations

from pathlib import Path


SITE_ROOT = Path("site")
INDEX = SITE_ROOT / "index.html"
STYLES = SITE_ROOT / "styles.css"
SCRIPT = SITE_ROOT / "app.js"
PAGES_WORKFLOW = Path(".github/workflows/pages.yml")

EXPECTED_MODULES = [
    "config.py",
    "models.py",
    "engine.py",
    "cli.py",
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


def main() -> int:
    missing_files = [str(path) for path in [INDEX, STYLES, SCRIPT, PAGES_WORKFLOW] if not path.exists()]
    if missing_files:
        raise SystemExit(f"missing documentation assets: {', '.join(missing_files)}")

    html = INDEX.read_text(encoding="utf-8")
    workflow = PAGES_WORKFLOW.read_text(encoding="utf-8")

    missing_modules = [module for module in EXPECTED_MODULES if module not in html]
    missing_concepts = [concept for concept in REQUIRED_CONCEPTS if concept not in html]
    missing_workflow = [
        marker
        for marker in ["python3 scripts/validate_docs_site.py", "actions/upload-pages-artifact", "actions/deploy-pages", "path: site"]
        if marker not in workflow
    ]

    if missing_modules or missing_concepts or missing_workflow:
        messages: list[str] = []
        if missing_modules:
            messages.append(f"missing modules: {', '.join(missing_modules)}")
        if missing_concepts:
            messages.append(f"missing concepts: {', '.join(missing_concepts)}")
        if missing_workflow:
            messages.append(f"missing workflow markers: {', '.join(missing_workflow)}")
        raise SystemExit("; ".join(messages))

    print(
        f"Docs site validation passed: {len(EXPECTED_MODULES)} modules, "
        f"{len(REQUIRED_CONCEPTS)} concepts, GitHub Pages workflow."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
