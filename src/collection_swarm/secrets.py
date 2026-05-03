"""Encrypted API key storage backed by SQLite.

Keys are encrypted at rest with Fernet (AES-128-CBC + HMAC-SHA256).
A per-installation encryption key is auto-generated on first use and
stored as ``<db_dir>/.collection_swarm.key``.  The same SQLite database
used for simulation results hosts the ``api_keys`` table.
"""

from __future__ import annotations

import base64
import os
import sqlite3
from pathlib import Path

from cryptography.fernet import Fernet

# Canonical names recognised by the rest of the application.
KNOWN_KEY_NAMES = frozenset({"NVIDIA_NIM_API_KEY", "CURSOR_API_KEY"})


class SecretsStore:
    """CRUD operations for encrypted API keys."""

    def __init__(self, db_path: Path | str = "output/collection_swarm.sqlite") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = _load_or_create_fernet(self.db_path.parent)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    name TEXT PRIMARY KEY,
                    encrypted_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def set_key(self, name: str, value: str) -> None:
        """Store (or update) an API key."""
        from collection_swarm.models import utc_now

        encrypted = self._fernet.encrypt(value.encode("utf-8")).decode("ascii")
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO api_keys (name, encrypted_value, updated_at) VALUES (?, ?, ?)",
                (name, encrypted, utc_now().isoformat()),
            )

    def get_key(self, name: str) -> str | None:
        """Return the decrypted value, or ``None`` if not stored."""
        with self._connect() as conn:
            row = conn.execute("SELECT encrypted_value FROM api_keys WHERE name = ?", (name,)).fetchone()
        if row is None:
            return None
        return self._fernet.decrypt(row["encrypted_value"].encode("ascii")).decode("utf-8")

    def delete_key(self, name: str) -> bool:
        """Delete a key. Returns ``True`` if the key existed."""
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM api_keys WHERE name = ?", (name,))
        return cursor.rowcount > 0

    def list_keys(self) -> list[dict[str, str]]:
        """Return metadata (name, updated_at) for all stored keys."""
        with self._connect() as conn:
            rows = conn.execute("SELECT name, updated_at FROM api_keys ORDER BY name").fetchall()
        return [{"name": row["name"], "updated_at": row["updated_at"]} for row in rows]

    def has_key(self, name: str) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM api_keys WHERE name = ?", (name,)).fetchone()
        return row is not None


def resolve_api_key(name: str, db_path: Path | str = "output/collection_swarm.sqlite") -> str | None:
    """Return an API key from the DB store, falling back to env vars.

    Priority:
      1. Value stored in the ``api_keys`` table (user-provided via dashboard / CLI).
      2. Environment variable with the same name.
      3. ``None``.
    """
    try:
        store = SecretsStore(db_path)
        value = store.get_key(name)
        if value:
            return value
    except Exception:
        pass
    return os.getenv(name)


# ── Encryption helpers ──────────────────────────────────────────


_KEY_FILENAME = ".collection_swarm.key"


def _load_or_create_fernet(directory: Path) -> Fernet:
    key_path = directory / _KEY_FILENAME
    if key_path.is_file():
        raw = key_path.read_bytes().strip()
    else:
        raw = Fernet.generate_key()
        directory.mkdir(parents=True, exist_ok=True)
        key_path.write_bytes(raw)
        try:
            key_path.chmod(0o600)
        except OSError:
            pass
    return Fernet(base64.urlsafe_b64encode(base64.urlsafe_b64decode(raw)))
