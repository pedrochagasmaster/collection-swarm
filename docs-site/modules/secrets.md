# `secrets.py` — encrypted key storage

<span class="cs-kicker">collection_swarm/secrets.py</span>

Encrypted API key storage backed by SQLite. Keys are encrypted at rest
with Fernet (AES-128-CBC + HMAC-SHA256). A per-installation encryption
key is auto-generated on first use.

<dl class="cs-summary">
  <dt>Imports</dt><dd><code>cryptography.fernet</code>, <code>sqlite3</code>, standard library</dd>
  <dt>Side effects</dt><dd>Creates <code>api_keys</code> table in the SQLite database, generates encryption key file</dd>
  <dt>Encryption</dt><dd>Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256)</dd>
</dl>

## `SecretsStore`

The main class for managing encrypted API keys.

```python
class SecretsStore:
    def __init__(self, db_path: Path) -> None: ...
```

The constructor opens (or creates) the SQLite database at `db_path` and
ensures the `api_keys` table exists. The Fernet encryption key is loaded
from `<db_dir>/.collection_swarm.key`, or auto-generated if the file
does not exist.

### `set_key(name, value)`

Encrypt and store (or update) an API key.

```python
def set_key(self, name: str, value: str) -> None: ...
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Key name — must be in `KNOWN_KEY_NAMES` |
| `value` | `str` | The plaintext key value |

Raises `ValueError` if `name` is not in `KNOWN_KEY_NAMES`.

### `get_key(name)`

Retrieve and decrypt a stored key, or return `None`.

```python
def get_key(self, name: str) -> str | None: ...
```

### `delete_key(name)`

Remove a key from the database.

```python
def delete_key(self, name: str) -> bool: ...
```

Returns `True` if a row was deleted, `False` if the key was not stored.

### `list_keys()`

List all known keys with their status, source, and last-updated timestamp.

```python
def list_keys(self) -> list[dict]: ...
```

Returns a list of dicts with keys: `name`, `source` (`"database"`,
`"environment"`, or `"not_set"`), `is_set` (`bool`), and `updated_at`
(`str | None`).

### `has_key(name)`

Check whether a key exists in the database.

```python
def has_key(self, name: str) -> bool: ...
```

## `resolve_api_key()`

Top-level helper that resolves an API key by priority:

```python
def resolve_api_key(name: str) -> str | None: ...
```

Resolution order:

1. **Database** — encrypted value from `SecretsStore`.
2. **Environment variable** — `os.getenv(name)`.
3. Returns `None` if the key is not available from any source.

The database path is determined by `env.get_db_path()`, which the CLI
sets at startup via `env.set_db_path()`.

## `KNOWN_KEY_NAMES`

```python
KNOWN_KEY_NAMES: frozenset[str] = frozenset({"NVIDIA_NIM_API_KEY", "CURSOR_API_KEY"})
```

The canonical set of API key names the system recognizes. Used for
validation in `SecretsStore.set_key()` and the REST API.

## Encryption

The encryption key file is located at `<db_dir>/.collection_swarm.key`,
where `<db_dir>` is the parent directory of the SQLite database file.

- On first use, `SecretsStore` generates a new Fernet key and writes it
  to the key file with `0o600` permissions (owner-only read/write).
- The key file is gitignored and should never be committed.
- Losing the key file means stored API keys cannot be decrypted. The
  user must re-enter them.
- Fernet guarantees both confidentiality (AES-128-CBC) and integrity
  (HMAC-SHA256). Tampered ciphertext raises an `InvalidToken` exception.
