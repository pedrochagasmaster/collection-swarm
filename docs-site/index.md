# Collection Swarm

**AI-driven simulator for testing debt-collection strategies before they ever touch a real customer.**

---

<div class="grid cards" markdown>

-   :material-robot-outline:{ .lg .middle } **Synthetic Conversations**

    ---

    Three AI roles — Collector, Debtor, and Judge — run multi-turn negotiations end-to-end so you can iterate on strategy without touching real customers.

-   :material-chart-bar:{ .lg .middle } **Quantified Results**

    ---

    Every conversation produces structured scores for payment probability, compliance, rapport, satisfaction, and escalation risk — all persisted to SQLite.

-   :material-trophy-outline:{ .lg .middle } **Elo Tournament Arena**

    ---

    Pit strategies and debtor profiles against each other in Swiss or round-robin tournaments with an Elo rating system that surfaces what actually works.

-   :material-dna:{ .lg .middle } **Strategy Evolution**

    ---

    An evolutionary loop mutates, recombines, and selects strategies across generations — letting the simulator discover tactics a human designer might miss.

</div>

---

## Why It Exists

Designing a debt-collection conversation is high-stakes work. A poorly worded opener can trigger regulatory violations, destroy rapport, or push vulnerable consumers deeper into financial distress. Traditional A/B testing requires live customer contact — expensive, slow, and ethically fraught.

Collection Swarm replaces that feedback loop with a **synthetic arena**. You define debtor archetypes (anxious hardship, hostile avoidant, scam-suspicious, serial renegotiator, etc.), pair them with collector strategies (empathetic payment plan, assertive settlement, WhatsApp self-service, etc.), and let AI models play out the conversations. A third AI role — the Judge — scores every exchange on payment outcome, compliance, rapport, and risk.

The result: **data-driven playbooks** built from hundreds of simulated conversations, not gut instinct.

---

## Key Features

!!! success "Multi-Provider Model Support"
    Run conversations through **NVIDIA NIM**, **Cursor SDK** (GPT-5.x, Claude Opus 4.x), or a **local scripted backend** for offline development. Swap models per role — use a fast model for conversation, a reasoning model for judging.

!!! info "Rich Debtor Profiles"
    Fourteen ready-made profiles model real-world archetypes: cooperative hardship, written-proof disputer, hostile avoidant, liquidation-confused, scam-suspicious, serial renegotiator, super-indebted, and more — each with backstory, constraints, and financial context.

!!! tip "Compliance Guardrails"
    Every prompt enforces Brazilian consumer-protection law (CDC art. 42/71, Lei 14.181/2021, SARB nº 27/2023). The Judge flags violations, and the analysis pipeline auto-excludes strategies that breach compliance thresholds.

!!! abstract "Playbook Generation"
    After a matrix run or tournament, the `analyze` command distills results into a Markdown playbook: best strategy per archetype, compliance exclusions, and statistical rankings.

---

## How It Works

``` mermaid
graph LR
    A[YAML Config] --> B[Simulation Engine]
    B --> C{Collector Agent}
    B --> D{Debtor Agent}
    C <-->|multi-turn| D
    D --> E[Transcript]
    E --> F{Judge Agent}
    F --> G[Judgment Scores]
    G --> H[(SQLite Store)]
    H --> I[Dashboard]
    H --> J[Playbook]
    H --> K[Elo Leaderboard]
```

1. **Configure** — Define debtor profiles, collector strategies, model backends, and prompts in YAML.
2. **Simulate** — The engine orchestrates multi-turn conversations between the Collector and Debtor agents.
3. **Judge** — A third AI (or heuristic) evaluates the transcript and produces structured scores.
4. **Persist** — Results flow into SQLite for querying, dashboarding, and downstream analysis.
5. **Analyze** — Generate playbooks, run Elo tournaments, evolve strategies, or explore results in the web dashboard.

---

## Quick Links

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } **Installation**

    ---

    Get up and running in under five minutes.

    [:octicons-arrow-right-24: Installation Guide](getting-started/installation.md)

-   :material-rocket-launch:{ .lg .middle } **Quick Start**

    ---

    Run your first simulation and view the results.

    [:octicons-arrow-right-24: Quick Start](getting-started/quickstart.md)

-   :material-cog:{ .lg .middle } **Configuration**

    ---

    Customize profiles, strategies, models, and prompts.

    [:octicons-arrow-right-24: Configuration Reference](getting-started/configuration.md)

-   :material-console:{ .lg .middle } **CLI Reference**

    ---

    Every command, option, and flag — with examples.

    [:octicons-arrow-right-24: CLI Reference](cli.md)

-   :material-view-dashboard:{ .lg .middle } **Web Dashboard**

    ---

    Explore results, transcripts, and analytics in the browser.

    [:octicons-arrow-right-24: Dashboard](web/overview.md)

-   :material-book-open-variant:{ .lg .middle } **Architecture**

    ---

    Understand the engine, agents, backends, and data flow.

    [:octicons-arrow-right-24: Architecture Overview](architecture/overview.md)

</div>
