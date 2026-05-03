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

def set_db_path(path: Path) -> None: ...

def get_db_path() -> Path: ...
```

### `set_db_path()` / `get_db_path()`

Configure and retrieve the database path used by backends for secret
resolution via `SecretsStore`. The CLI group calls `set_db_path()` early
so that `resolve_api_key()` in the backends can locate the encrypted key
store without an explicit path argument.

### `load_dotenv_if_present()`

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

If you need any of the missing features, switch to `python-dotenv`. The
backends both call this loader the same way:

```python
from collection_swarm.env import load_dotenv_if_present
load_dotenv_if_present()
api_key = os.getenv("CURSOR_API_KEY")
```
