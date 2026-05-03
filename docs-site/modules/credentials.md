# `credentials.py` — dashboard-managed API keys

<span class="cs-kicker">collection_swarm/credentials.py</span>

The abstraction that lets operators store `CURSOR_API_KEY` and
`NVIDIA_NIM_API_KEY` in the dashboard database instead of managing
environment variables by hand. Every backend — CLI, web, runner, model
probes — consults a single `CredentialResolver` per application session
and never touches `os.environ` directly.

<dl class="cs-summary">
  <dt>Imports</dt><dd>Standard library only (<code>sqlite3</code>, <code>dataclasses</code>)</dd>
  <dt>Storage</dt><dd>Table <code>dashboard_credentials</code> inside the simulation SQLite database (<code>--db</code>)</dd>
  <dt>Resolution order</dt><dd>Dashboard store → environment variable → <code>RuntimeError</code></dd>
  <dt>Secret handling</dt><dd>Plain text on disk; previews are masked when served over the API</dd>
</dl>

## Why this module exists

The NIM and Cursor SDK backends historically read their keys via
`os.getenv(...)`. That forced every dashboard user to drop back to a
terminal to edit `.env` files just to run a live simulation. This module
lets them do it from the web UI (Settings page) or from the CLI
(`collection-swarm creds ...`), while keeping env vars as a fully
supported fallback for CI and scripted setups.

## Public surface

```python
from collection_swarm.credentials import (
    CREDENTIAL_PROVIDERS,      # tuple[CredentialProvider, ...]
    CredentialProvider,         # static metadata dataclass
    CredentialStore,            # SQLite-backed persistence
    CredentialResolver,         # store-first / env-fallback lookup
    StoredCredential,           # the record returned by store.get/set
    list_providers,             # -> tuple[CredentialProvider, ...]
    get_provider,               # id -> CredentialProvider (KeyError on miss)
    get_provider_by_env,        # env_var -> CredentialProvider | None
)
```

### Bundled providers

| ID           | Env var                | Used by                                   |
|--------------|------------------------|-------------------------------------------|
| `cursor`     | `CURSOR_API_KEY`       | Cursor SDK backend (collector, debtor, judge) |
| `nvidia_nim` | `NVIDIA_NIM_API_KEY`   | NVIDIA NIM backend                        |

Adding a new provider is one tuple entry in `CREDENTIAL_PROVIDERS` — the
store, resolver, CLI (`creds list/set/clear/providers`), web API, and
Settings page pick it up automatically.

## `CredentialStore`

```python
store = CredentialStore(Path("output/collection_swarm.sqlite"))
store.set("cursor", "key_abcd1234")
store.get("cursor")        # -> StoredCredential(provider_id, value, updated_at)
store.delete("cursor")     # -> bool (True if a row was removed)
store.all()                # -> dict[str, StoredCredential]
```

- The schema is created lazily on first access: a single table
  `dashboard_credentials(provider_id PRIMARY KEY, value TEXT, updated_at TEXT)`.
- `set` strips whitespace and raises `ValueError` on empty values.
- `all()` silently skips rows for unknown providers, so renaming a
  provider does not crash existing deployments.

## `CredentialResolver`

```python
resolver = CredentialResolver(
    store=CredentialStore(db_path),     # optional — pass None to disable the store
    env=os.environ,                     # any Mapping[str, str]; defaults to os.environ
)

resolver.get("cursor")                  # str | None
resolver.require("cursor")              # str — raises RuntimeError with a friendly hint
resolver.status("cursor")               # dict — provider metadata + source
resolver.statuses()                     # list of dicts for every known provider
resolver.env_overlay()                  # {"CURSOR_API_KEY": "..."} — stored values only
```

Precedence:

1. Value stored in the database (if any and non-empty).
2. Matching environment variable from the injected `env`.
3. `None` (or `RuntimeError` for `require`).

`env_overlay()` is the bridge that powers subprocess backends. The Cursor
SDK Node bridge needs `CURSOR_API_KEY` in its `process.env`, but we do
not want to mutate the parent process. `CursorSdkBackend` calls
`resolver.env_overlay()` and layers it into the subprocess environment
it passes to `asyncio.create_subprocess_exec`.

### `status(...)` shape

```json
{
  "id": "cursor",
  "label": "Cursor SDK",
  "env_var": "CURSOR_API_KEY",
  "description": "...",
  "docs_url": "https://cursor.com/dashboard?tab=integrations",
  "configured": true,
  "source": "store",      // "store" | "env" | null
  "stored": true,
  "env_set": false,
  "preview": "key_...1234",
  "updated_at": "2026-05-03T17:00:00+00:00"
}
```

`preview` masks the credential to 4-char head and 4-char tail; the raw
value is never included. The same shape is returned from the
[`/api/credentials`](../reference/api.md#credentials) endpoints and
consumed by the SPA Settings page.

## How it threads through the app

```
CLI invocation          ──► _credential_resolver(ctx) ──► LLMRouter ──► Backend
Web app (FastAPI)       ──► app.state.credential_store ──► LLMRouter ──► Backend
Runner / tournaments    ──► run_matrix(..., credentials=resolver)
Model evaluation probes ──► run_live_role_probes(..., credentials=resolver)
```

Every entry point builds exactly one resolver per session and hands it
down. Backends accept a resolver via constructor injection, keeping
them trivially testable:

```python
from collection_swarm.credentials import CredentialResolver, CredentialStore
from collection_swarm.backends.nim import NimBackend

resolver = CredentialResolver(store=CredentialStore(":memory:"), env={})
resolver.store.set("nvidia_nim", "test_key")
backend = NimBackend(credentials=resolver)
```

## Error handling

`resolver.require("cursor")` raises:

```
CURSOR_API_KEY is required for Cursor SDK. Add it from the dashboard
Settings page, run `collection-swarm creds set cursor`, or export the
env var.
```

The message names all three remediation paths so operators never have
to guess which surface they're missing.

## Operator interfaces

- **Web dashboard Settings page** — `/#settings` route; rendered by
  `renderSettings()` in [`web/static/app.js`](web/static.md).
- **Web API** — `GET`/`PUT`/`DELETE /api/credentials[/:id]`; see
  [reference/api.md § Credentials](../reference/api.md#credentials).
- **CLI** — `collection-swarm creds {list,set,clear,providers}`; see
  [reference/cli.md § `creds`](../reference/cli.md#creds).

## Security notes

- Values are persisted as plain text inside the operator-owned SQLite
  database. Treat the file like a `.env` — restrict permissions to
  trusted operators.
- The dashboard Settings page uses `<input type="password">` with a
  Show/Hide toggle so clipboard screenshots do not leak keys.
- Only previews are returned over the API; the raw value is never
  reflected in responses.
- The Cursor SDK bridge receives the key through a per-invocation
  `env` dict passed to `create_subprocess_exec`, so stored values never
  leak into the dashboard's own `os.environ`.
