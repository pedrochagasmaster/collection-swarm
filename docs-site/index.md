---
title: Collection Swarm
description: An AI-driven simulator that pits Collector, Debtor, and Judge agents against one another so debt-collection teams can stress-test strategies before they ever touch a real customer.
hide:
  - navigation
  - toc
---

<div class="cs-hero" markdown>

<span class="cs-hero__eyebrow">v0.1 · Synthetic collection research</span>

# Stress-test collection strategies before they touch a real customer.

<p class="cs-hero__lead">
A Python simulator that runs multi-turn negotiations between an AI
<em>Collector</em>, an AI <em>Debtor</em>, and an AI <em>Judge</em> — then ranks
what actually works across debtor archetypes, models, and tactics. Offline by
default, live-model-ready when you want it.
</p>

<div class="cs-hero__cta" markdown>
[:material-rocket-launch-outline: Quick start](getting-started/install.md){ .md-button .md-button--primary }
[:material-book-open-page-variant-outline: Read the concepts](concepts/index.md){ .md-button }
[:material-source-branch: Source on GitHub](https://github.com/pedrochagasmaster/collection-swarm){ .md-button }
</div>

<ol class="cs-hero__loop">
  <li><b>01</b><span>YAML config defines profiles, strategies, models, prompts.</span></li>
  <li><b>02</b><span>Engine alternates Collector and Debtor turns to a transcript.</span></li>
  <li><b>03</b><span>Router dispatches model calls to scripted, NIM, or Cursor SDK.</span></li>
  <li><b>04</b><span>Judge scores the transcript and verifies hard constraints.</span></li>
  <li><b>05</b><span>Store persists runs for the dashboard, arena, and playbook.</span></li>
</ol>

</div>

## What you can do with it { .no-rule }

<div class="cs-grid" markdown>

<div class="cs-card" markdown>
### [Run a single simulation](getting-started/install.md)
One Collector × Debtor × Judge conversation from one CLI call. No API keys
needed — the scripted backend is deterministic and offline.
</div>

<div class="cs-card" markdown>
### [Sweep a matrix](modules/runner.md)
Run every Profile × Strategy × Model combination under bounded concurrency
and fold the results into a single SQLite database.
</div>

<div class="cs-card" markdown>
### [Hold a tournament](modules/arena.md)
Elo-rate strategies against profiles across Swiss or round-robin rounds and
watch the leaderboard converge on what actually works.
</div>

<div class="cs-card" markdown>
### [Evolve new strategies](modules/evolution.md)
Let a strong model mutate and recombine the bottom of the leaderboard into
new candidate strategies, generation after generation.
</div>

<div class="cs-card" markdown>
### [Browse the dashboard](getting-started/dashboard.md)
A FastAPI + vanilla-JS SPA exposes runs, transcripts, leaderboards, playbooks,
and a live manual role-play sandbox.
</div>

<div class="cs-card" markdown>
### [Plug in real models](getting-started/live-models.md)
Native backends for NVIDIA NIM and the Cursor SDK. Bring your own keys, or
stay fully offline with the deterministic scripted backend.
</div>

</div>

## How the system thinks { .no-rule }

```mermaid
flowchart LR
    subgraph CFG[config/]
      P[debtor_profiles.yaml]
      S[collector_strategies.yaml]
      M[models.yaml]
      PR[prompts.yaml]
      SI[simulation.yaml]
    end

    CFG --> ENG[SimulationEngine]
    ENG --> COL[CollectorAgent]
    ENG --> DEB[DebtorAgent]
    ENG --> JUD[Judge]
    COL --> R[LLMRouter]
    DEB --> R
    JUD --> R
    R -->|scripted| SC[Scripted backend]
    R -->|nim| NIM[NVIDIA NIM]
    R -->|cursor_sdk| CSDK[Cursor SDK bridge]
    ENG --> RES[SimulationResult]
    RES --> DB[(SQLite store)]
    DB --> WEB[Web dashboard]
    DB --> AN[Analysis pipeline]
    AN --> PB[Markdown playbook]
```

A run flows left-to-right. Configuration drives the engine, the engine runs
three agents through one router, and the resulting `SimulationResult` is the
substrate every downstream report builds on.

## Read it like a book { .no-rule }

The docs are ordered the way a careful reader would explore the codebase —
from the surface, down through the architecture and concepts, into each
individual module, and back out to operator references.

<div class="cs-grid" markdown>

<div class="cs-card" markdown>
### [1 · Getting started](getting-started/index.md)
Install the package, run the first offline simulation, point it at a real
provider, open the dashboard.
</div>

<div class="cs-card" markdown>
### [2 · Architecture](architecture/overview.md)
A system-level view: components, data flow through every workflow, and the
full Pydantic domain model.
</div>

<div class="cs-card" markdown>
### [3 · Concepts](concepts/index.md)
Vocabulary, conversation lifecycle, compliance guardrails, and how the
arena and the judge think.
</div>

<div class="cs-card" markdown>
### [4 · Modules](modules/index.md)
A file-by-file walkthrough of every module under `src/collection_swarm/`,
with signatures, diagrams, and the gotchas worth knowing.
</div>

<div class="cs-card" markdown>
### [5 · Catalog](catalog/profiles.md)
The fourteen bundled debtor profiles and the collector strategies they
negotiate against — archetypes, constraints, and demographics.
</div>

<div class="cs-card" markdown>
### [6 · Reference](reference/index.md)
Operator-level reference for the CLI, the HTTP API, the YAML configuration
files, the SQLite schema, and the full glossary.
</div>

</div>

!!! warning "Synthetic data only"
    Every profile, debtor, and transcript in this repository is generated for
    research. Do not ingest real consumer records, do not treat Judge output
    as legal advice, and do not deploy a strategy without human review. See
    [Compliance & guardrails](concepts/compliance.md) for the full stance.
