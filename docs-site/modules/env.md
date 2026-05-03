# `env.py` — dotenv loader

<span class="cs-kicker">collection_swarm/env.py</span>

A 25-line helper that loads `KEY=VALUE` lines from a `.env` file without
overriding variables already set in the shell. Used by the NIM and
Cursor SDK backends; nothing else cares about it.

<dl class="cs-summary">
  <dt>Imports</dt><dd>standard library only</dd>
  <dt>Side effects</dt><dd>Mutates <code>os.environ</code> for keys not already set</dd>
  <dt>Why not python-dotenv?</dt><dd>This file is too small to take a dependency for</dd>
</dl>

## Public surface

```python
def load_dotenv_if_present(path: Path | None = None) -> None: ...
```

Resolution rules:

1. Use the `path` argument if provided.
2. Else, try `<cwd>/.env`.
3. Else, try `<repo_root>/.env` (computed as `Path(__file__).resolve().parents[2]`).

If no file exists at the resolved path, the function returns silently.

For each non-blank, non-comment line containing `=`:

- Split on the first `=`.
- Trim whitespace from key and value.
- Skip if the key is blank or already in `os.environ`.
- Strip a single matching pair of `'` or `"` around the value.
- Set `os.environ[key]`.

## Why "if not already set"

Several CI / Cursor Cloud environments inject secrets directly into the
process environment. If `.env` overrode them, you would shadow the real
key with whatever stale value sits in your local file. The whole-shell
guard ensures `.env` is *additive*, never *overriding*.

## Practical contract

| Behavior                  | Yes / No |
| ------------------------- | -------- |
| Multi-line values          | No       |
| Variable substitution      | No       |
| Quoted values              | Yes (single layer) |
| Comments (`# ...`)         | Yes      |
| `export KEY=VALUE` syntax  | No (the `export ` prefix would become part of the key name) |

If you need any of the missing features, switch to `python-dotenv`.

!!! note "Settings store takes priority"
    Since the addition of the [settings store](../reference/api.md#settings),
    backends now resolve credentials via `settings.resolve()` which checks
    the stored database value first (set via the dashboard **API Keys** page
    or `collection-swarm config-set`), then falls back to the environment
    variable loaded by this module. The `.env` loader still runs first so
    the env var is available as a fallback.

The backends call the loader and then resolve through the settings store:

```python
from collection_swarm.env import load_dotenv_if_present
from collection_swarm.settings import get_settings_store
load_dotenv_if_present()
api_key = get_settings_store().resolve("cursor_api_key", "CURSOR_API_KEY")
```
