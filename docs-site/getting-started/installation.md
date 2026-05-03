# Installation

## Prerequisites

| Requirement | Minimum Version | Purpose |
|---|---|---|
| **Python** | 3.12+ | Core runtime — simulation engine, CLI, analysis, web dashboard |
| **Node.js** | 22+ | *Optional* — only needed for the Cursor SDK bridge backend |
| **pip** | Latest | Package installation (ships with Python) |
| **Git** | Any recent | Cloning the repository |

!!! tip "Check your versions"
    ```bash
    python --version   # Python 3.12.x or higher
    node --version     # v22.x or higher (optional)
    ```

---

## 1. Clone the Repository

```bash
git clone https://github.com/your-org/collection-swarm.git
cd collection-swarm
```

---

## 2. Install the Python Package

Install in editable mode with development dependencies:

```bash
pip install -e ".[dev]"
```

This installs the `collection-swarm` CLI entry point and all runtime dependencies:

| Package | Role |
|---|---|
| `click` | CLI framework |
| `pydantic` | Configuration and domain model validation |
| `pyyaml` | YAML config loading |
| `litellm` | Unified LLM API layer |
| `rich` | Terminal output formatting |
| `pandas` | Statistical analysis |
| `aiosqlite` | Async SQLite persistence |
| `fastapi` + `uvicorn` | Web dashboard server |
| `jinja2` + `markdown` + `bleach` | Template rendering |

Dev extras add `pytest`, `pytest-asyncio`, and `httpx` for testing.

!!! success "Verify the install"
    ```bash
    collection-swarm --help
    ```
    You should see the top-level help with all available commands.

---

## 3. Cursor SDK Bridge (Optional)

The Cursor SDK bridge allows Collection Swarm to route conversations through Cursor-hosted models (GPT-5.x, Claude Opus 4.x, etc.) via a local Node.js process.

```bash
cd cursor_sdk_bridge
npm install
```

!!! note "When do you need this?"
    Only if you plan to use `cursor_sdk` backend models — for example `cursor-gpt-5.5-medium` or `cursor-claude-4.6-opus-high-thinking`. The scripted and NIM backends work without Node.js.

---

## 4. Environment Variables

Create a `.env` file in the project root (or export the variables in your shell):

```dotenv
# NVIDIA NIM backend (required for nim-* models)
NVIDIA_NIM_API_KEY=nvapi-xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Cursor SDK backend (required for cursor-* models)
CURSOR_API_KEY=cur_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

!!! warning "Keep secrets out of version control"
    The `.env` file is listed in `.gitignore` by default. Never commit API keys to the repository.

### Variable Reference

| Variable | Required For | Description |
|---|---|---|
| `NVIDIA_NIM_API_KEY` | NIM backend models | API key from [NVIDIA NGC](https://build.nvidia.com/) |
| `CURSOR_API_KEY` | Cursor SDK backend models | API key from Cursor settings |

!!! info "No keys needed for offline work"
    The `local-scripted` conversation backend and `local-judge` heuristic backend run entirely offline — no API keys required. This is the default when no model flags are passed to the CLI.

---

## 5. Verify Everything Works

Run the built-in connection test:

```bash
collection-swarm test-connection
```

For a full end-to-end check, run a single offline simulation:

```bash
collection-swarm simulate \
  --profile cooperative_hardship \
  --strategy empathetic_payment_plan \
  --no-save
```

You should see a multi-turn conversation transcript followed by a judgment table.

---

## What's Next?

- **[Quick Start](quickstart.md)** — Run your first matrix of simulations and explore the results.
- **[Configuration](configuration.md)** — Customize profiles, strategies, models, and prompts.
