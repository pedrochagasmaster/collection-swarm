"""Persisted application settings with optional encryption for secrets.

Settings are stored in the ``app_settings`` table of the existing SQLite
database.  Values flagged as *secret* are symmetrically encrypted at rest
using Fernet (from the ``cryptography`` package when available) or a simple
base-64 obfuscation fallback when the package is not installed.

The encryption key is derived deterministically from the database path so
that each deployment gets a unique key without requiring the operator to
manage yet another secret.  This protects against casual file-system reads
but is **not** a substitute for full-disk encryption in production.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

# Known setting keys and whether they hold secrets.
SETTING_KEYS: dict[str, bool] = {
    "nvidia_nim_api_key": True,
    "cursor_api_key": True,
    "cursor_sdk_workspace": False,
}

SECRET_KEYS = frozenset(k for k, secret in SETTING_KEYS.items() if secret)

_FERNET_AVAILABLE = False
try:
    from cryptography.fernet import Fernet

    _FERNET_AVAILABLE = True
except ImportError:
    pass


def _derive_key(db_path: Path) -> bytes:
    """Derive a 32-byte key from the canonical database path."""
    seed = f"collection-swarm-settings:{db_path.resolve()}"
    raw = hashlib.sha256(seed.encode()).digest()
    return base64.urlsafe_b64encode(raw)


def _encrypt(value: str, key: bytes) -> str:
    if _FERNET_AVAILABLE:
        return Fernet(key).encrypt(value.encode()).decode()
    return base64.urlsafe_b64encode(value.encode()).decode()


def _decrypt(token: str, key: bytes) -> str:
    if _FERNET_AVAILABLE:
        return Fernet(key).decrypt(token.encode()).decode()
    return base64.urlsafe_b64decode(token.encode()).decode()


class SettingsStore:
    """Read and write application settings in the SQLite database."""

    def __init__(self, db_path: Path | str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._key = _derive_key(self.db_path)
        self._init_table()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    is_secret INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
                """
            )

    # ── Read ────────────────────────────────────────────────────────

    def get(self, key: str) -> str | None:
        """Return decrypted value for *key*, or ``None`` if unset."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value, is_secret FROM app_settings WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        if row["is_secret"]:
            try:
                return _decrypt(row["value"], self._key)
            except Exception:
                return None
        return row["value"]

    def get_all(self, *, mask_secrets: bool = False) -> dict[str, str | None]:
        """Return all settings.  When *mask_secrets* is ``True`` secret values
        are replaced with a masked indicator if they are set."""
        result: dict[str, str | None] = {k: None for k in SETTING_KEYS}
        with self._connect() as conn:
            rows = conn.execute("SELECT key, value, is_secret FROM app_settings").fetchall()
        for row in rows:
            key = row["key"]
            if key not in SETTING_KEYS:
                continue
            if row["is_secret"]:
                if mask_secrets:
                    result[key] = "••••••••"
                else:
                    try:
                        result[key] = _decrypt(row["value"], self._key)
                    except Exception:
                        result[key] = None
            else:
                result[key] = row["value"]
        return result

    # ── Write ───────────────────────────────────────────────────────

    def set(self, key: str, value: str) -> None:
        """Store a setting.  Secrets are encrypted at rest."""
        if key not in SETTING_KEYS:
            raise ValueError(f"unknown setting: {key}")
        is_secret = key in SECRET_KEYS
        stored = _encrypt(value, self._key) if is_secret else value
        from collection_swarm.models import utc_now

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO app_settings (key, value, is_secret, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value,
                    is_secret=excluded.is_secret, updated_at=excluded.updated_at
                """,
                (key, stored, int(is_secret), utc_now().isoformat()),
            )

    def set_many(self, settings: dict[str, str]) -> None:
        """Bulk-write multiple settings.  Empty-string values delete the key."""
        for key, value in settings.items():
            if key not in SETTING_KEYS:
                continue
            if value == "":
                self.delete(key)
            else:
                self.set(key, value)

    def delete(self, key: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))

    # ── Credential resolution ───────────────────────────────────────

    def resolve(self, key: str, env_var: str | None = None) -> str | None:
        """Return the setting value, falling back to the environment variable.

        Priority: stored setting > environment variable > ``.env`` file
        (the latter is already loaded into ``os.environ`` by callers).
        """
        stored = self.get(key)
        if stored:
            return stored
        if env_var:
            return os.getenv(env_var) or None
        return None


# ── Module-level helpers for the backends ───────────────────────

_store_instance: SettingsStore | None = None


def get_settings_store(db_path: Path | str | None = None) -> SettingsStore:
    """Return (and cache) a global SettingsStore instance."""
    global _store_instance
    if _store_instance is None or (db_path is not None and Path(db_path) != _store_instance.db_path):
        resolved = Path(db_path) if db_path else Path(
            os.environ.get("COLLECTION_SWARM_DB_PATH", "output/collection_swarm.sqlite")
        )
        _store_instance = SettingsStore(resolved)
    return _store_instance


def reset_settings_store() -> None:
    """Drop the cached singleton (useful for tests)."""
    global _store_instance
    _store_instance = None
