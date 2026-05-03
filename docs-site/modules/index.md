# Modules

This is the deep dive. Every module under `src/collection_swarm/` gets
its own page, with file-level intent, public surface, and the
implementation notes that won't be obvious from the source alone.

## Map of the package

```
src/collection_swarm/
├── __init__.py                     # Package version
├── models.py                       # Pydantic domain types
├── config.py                       # YAML loaders → AppConfig
├── env.py                          # Lightweight .env loader
├── engine.py                       # SimulationEngine + stalemate detector
├── agents/
│   ├── collector.py                # CollectorAgent
│   ├── debtor.py                   # DebtorAgent
│   └── judge.py                    # Judge + deterministic verifier
├── backends/
│   ├── base.py                     # LLMBackend protocol & LLMResponse
│   ├── router.py                   # LLMRouter + lazy backend registry
│   ├── scripted.py                 # Deterministic offline backend
│   ├── nim.py                      # NVIDIA NIM backend (LiteLLM)
│   └── cursor_sdk.py               # Cursor SDK subprocess backend
├── store.py                        # SQLite persistence + analytics
├── runner.py                       # build_matrix, run_matrix, tournament, evolution
├── arena.py                        # Elo math & pairings
├── evolution.py                    # LLM-driven Strategy mutations
├── adversarial.py                  # LLM-driven Profile hardening
├── calibration.py                  # Judge calibration pipeline
├── model_evaluation.py             # Per-role Cursor SDK probes & report
├── analysis/
│   ├── statistics.py               # StrategyRanking
│   ├── compliance.py               # ComplianceExclusion
│   ├── objections.py               # Objection extraction
│   └── playbook.py                 # Markdown Playbook generator
├── web/
│   ├── app.py                      # FastAPI dashboard
│   ├── seed.py                     # Demo data generator
│   └── static/                     # Vanilla SPA (HTML, CSS, JS, fonts)
└── cli.py                          # Click entry point
```

## Reading order

If you're reading the modules cold, this is the order that minimizes
forward references:

1. [`models.py`](models.md) — every other module imports from here.
2. [`config.py`](config.md) — how the YAML files become typed objects.
3. [`env.py`](env.md) — the tiny dotenv helper.
4. [`backends/`](backends/index.md) — the bottom of the model stack.
5. [`agents/`](agents/index.md) — the three roles built on top of the
   backends.
6. [`engine.py`](engine.md) — the loop that ties the agents together.
7. [`store.py`](store.md) — the SQLite persistence layer.
8. [`runner.py`](runner.md) — the matrix and tournament orchestrator.
9. [`arena.py`](arena.md), [`evolution.py`](evolution.md),
   [`adversarial.py`](adversarial.md) — the optional adversarial loop.
10. [`calibration.py`](calibration.md) and
    [`model_evaluation.py`](model-evaluation.md) — the meta-evaluation.
11. [`analysis/`](analysis/index.md) — the read-side reports.
12. [`web/`](web/index.md) — the dashboard.
13. [`cli.py`](cli.md) — the operator surface.

Or, if you'd rather skim by topic, head straight to whichever module page
matches what you're trying to do.
