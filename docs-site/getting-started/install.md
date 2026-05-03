# Install & first simulation

## Requirements

| Dependency         | Version | Required for                 |
| ------------------ | ------- | ---------------------------- |
| Python             | 3.12+   | All modes                    |
| pip                | recent  | Editable install             |
| Node.js            | 22+     | Cursor SDK backend (optional)|
| NVIDIA NIM API key | —       | NIM backend (optional)       |
| Cursor API key     | —       | Cursor SDK backend (optional)|

The offline path needs only Python 3.12 and pip.

## Install in editable mode

```bash
git clone https://github.com/pedrochagasmaster/collection-swarm.git
cd collection-swarm
pip install -e ".[dev]"
```

This pulls the runtime stack — `litellm`, `click`, `pydantic`, `pyyaml`,
`pandas`, `rich`, `aiosqlite`, `fastapi`, `uvicorn`, `jinja2`, `markdown`,
and `bleach` — plus the dev extras `pytest`, `pytest-asyncio`, and `httpx`.

Verify the install:

```bash
collection-swarm --help
```

You should see the Click command group with `simulate`, `run`, `analyze`,
`tournament`, `evolve`, `serve`, `seed`, and friends.

## Run your first offline simulation

The bundled `scripted` backend is a deterministic, no-API-key responder that
produces realistic Brazilian-Portuguese transcripts for the canonical
Profiles and Strategies. It is the engine the test suite uses, so it is
guaranteed to produce a valid `SimulationResult`.

```bash
collection-swarm simulate \
  --profile cooperative_hardship \
  --strategy empathetic_payment_plan \
  --no-save
```

`--no-save` keeps the run out of the SQLite store; remove it to persist.

You'll see something like:

```
─────────── Simulation sim_… [completed] ───────────
Collector: Olá, aqui é Alex falando em nome do liquidante do Will Bank…
Debtor:    Tô numa fase apertada, mas consigo segurar uma parcela pequena…
Collector: Combinado. Vou registrar o acordo por boleto oficial…

Ended by: collector; turns: 4
                  Judgment
┏━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ Metric              ┃ Value               ┃
┃─────────────────────┼─────────────────────┃
┃ Payment outcome     │ payment_plan        │
┃ Payment probability │ 72%                 │
┃ Compliance score    │ 95%                 │
┗━━━━━━━━━━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━━━━━┛
```

That's the full pipeline:

1. The **Collector** opens with the configured tone and tactic, citing the
   liquidante (the post-liquidation actor for Will Bank).
2. The **Debtor** answers under the constraints baked into the
   `cooperative_hardship` Profile (R$ 80/mês ceiling, no Pix, no card data
   on the call).
3. The **Judge** scores the transcript against the regulatory backdrop and
   emits a structured JSON Judgment that the engine parses and persists.

## Browse what's in the box

```bash
collection-swarm list-profiles
collection-swarm list-strategies
```

Both commands print a Rich table plus a plain-text mirror of all IDs so
they're parseable from automation contexts where Rich may truncate.

## Run a small matrix

Once you have the offline path working, try a 4-cell sweep:

```bash
collection-swarm run \
  --profiles cooperative_hardship,written_proof_disputer \
  --strategies empathetic_payment_plan,problem_solving_callback \
  --reps 1 \
  --concurrency 2
```

This creates an `output/collection_swarm.sqlite` database with four runs.
Generate a Playbook from it:

```bash
collection-swarm analyze --output output/playbook.md
```

The Playbook ranks Strategies per Profile by mean payment probability,
filters out compliance-risky combos, and embeds the best transcripts as
worked examples.

## Run the test suite

```bash
pytest -q
```

The 17-file suite covers config loading, the engine, every backend, the
Judge parser, the SQLite store, the matrix runner, the analysis pipeline,
the CLI, the model evaluation pipeline, and the FastAPI dashboard.

## Where to go next

- Need real models? Continue to [Live model setup](live-models.md).
- Prefer a UI? Skip ahead to [The web dashboard](getting-started/../dashboard.md).
- Want to understand the vocabulary first? Start with the
  [Concepts overview](../concepts/index.md).
