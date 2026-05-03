"""Dashboard-managed API credentials.

Historically, the LLM backends (Cursor SDK, NVIDIA NIM) read their API keys
exclusively from process environment variables. That works for one-off CLI
runs, but it forces every dashboard user to manage shell environment files.

This module introduces a small abstraction layer so that operators can store
credentials in the application database (managed via the web dashboard or the
``collection-swarm creds`` CLI group) and have every backend — CLI, web,
runner, model-eval probes — pick them up automatically.

Resolution order for a given credential is:

1. An explicit override stored in the credential database
2. The matching process environment variable
3. ``None`` (the backend then surfaces a friendly error)

Credentials are stored as plain text in the SQLite database. The database is
intended to live on a trusted developer machine; downstream users that need
encryption-at-rest should manage the underlying SQLite file with the same
permission posture they apply to ``.env`` files.
"""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping


# ── Provider registry ────────────────────────────────────────────

@dataclass(frozen=True)
class CredentialProvider:
    """Static metadata describing a provider whose key the dashboard manages."""

    id: str
    label: str
    env_var: str
    description: str
    docs_url: str


CREDENTIAL_PROVIDERS: tuple[CredentialProvider, ...] = (
    CredentialProvider(
        id="cursor",
        label="Cursor SDK",
        env_var="CURSOR_API_KEY",
        description="Powers the Cursor coding-agent backend used by collector, debtor, and judge LLM roles.",
        docs_url="https://cursor.com/dashboard?tab=integrations",
    ),
    CredentialProvider(
        id="nvidia_nim",
        label="NVIDIA NIM",
        env_var="NVIDIA_NIM_API_KEY",
        description="Free-tier NVIDIA NIM hosted inference for production-grade models.",
        docs_url="https://build.nvidia.com",
    ),
)

_PROVIDERS_BY_ID: dict[str, CredentialProvider] = {p.id: p for p in CREDENTIAL_PROVIDERS}
_PROVIDERS_BY_ENV: dict[str, CredentialProvider] = {p.env_var: p for p in CREDENTIAL_PROVIDERS}


def list_providers() -> tuple[CredentialProvider, ...]:
    return CREDENTIAL_PROVIDERS


def get_provider(provider_id: str) -> CredentialProvider:
    try:
        return _PROVIDERS_BY_ID[provider_id]
    except KeyError as exc:
        raise KeyError(f"unknown credential provider '{provider_id}'") from exc


def get_provider_by_env(env_var: str) -> CredentialProvider | None:
    return _PROVIDERS_BY_ENV.get(env_var)


# ── Stored credential record ─────────────────────────────────────

@dataclass(frozen=True)
class StoredCredential:
    provider_id: str
    value: str
    updated_at: datetime


# ── Persistence layer ────────────────────────────────────────────

class CredentialStore:
    """SQLite-backed credential storage colocated with simulation data."""

    TABLE = "dashboard_credentials"

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE} (
                    provider_id TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def set(self, provider_id: str, value: str) -> StoredCredential:
        provider = get_provider(provider_id)
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValueError(f"credential value for '{provider.id}' must not be empty")
        now = datetime.now(tz=timezone.utc)
        with self._connect() as connection:
            connection.execute(
                f"INSERT OR REPLACE INTO {self.TABLE} (provider_id, value, updated_at) VALUES (?, ?, ?)",
                (provider.id, cleaned, now.isoformat()),
            )
        return StoredCredential(provider_id=provider.id, value=cleaned, updated_at=now)

    def get(self, provider_id: str) -> StoredCredential | None:
        provider = get_provider(provider_id)
        with self._connect() as connection:
            row = connection.execute(
                f"SELECT provider_id, value, updated_at FROM {self.TABLE} WHERE provider_id = ?",
                (provider.id,),
            ).fetchone()
        if row is None:
            return None
        return StoredCredential(
            provider_id=row["provider_id"],
            value=row["value"],
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def delete(self, provider_id: str) -> bool:
        provider = get_provider(provider_id)
        with self._connect() as connection:
            cursor = connection.execute(
                f"DELETE FROM {self.TABLE} WHERE provider_id = ?",
                (provider.id,),
            )
        return cursor.rowcount > 0

    def all(self) -> dict[str, StoredCredential]:
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT provider_id, value, updated_at FROM {self.TABLE}"
            ).fetchall()
        out: dict[str, StoredCredential] = {}
        for row in rows:
            if row["provider_id"] not in _PROVIDERS_BY_ID:
                # Skip stale rows for providers the application no longer knows
                # about so renaming a provider doesn't crash callers.
                continue
            out[row["provider_id"]] = StoredCredential(
                provider_id=row["provider_id"],
                value=row["value"],
                updated_at=datetime.fromisoformat(row["updated_at"]),
            )
        return out


# ── Resolution layer ─────────────────────────────────────────────

class CredentialResolver:
    """Resolves credentials with dashboard-store-first precedence over env vars.

    A single instance is created per application (CLI invocation, web app,
    background runner) and threaded down to backends so they never have to
    touch ``os.environ`` directly.
    """

    def __init__(
        self,
        store: CredentialStore | None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self._store = store
        self._env = env if env is not None else os.environ

    @property
    def store(self) -> CredentialStore | None:
        return self._store

    def get(self, provider_id: str) -> str | None:
        provider = get_provider(provider_id)
        if self._store is not None:
            stored = self._store.get(provider_id)
            if stored and stored.value:
                return stored.value
        env_value = self._env.get(provider.env_var)
        if env_value:
            return env_value
        return None

    def get_by_env(self, env_var: str) -> str | None:
        provider = get_provider_by_env(env_var)
        if provider is not None:
            return self.get(provider.id)
        return self._env.get(env_var)

    def require(self, provider_id: str, *, error_message: str | None = None) -> str:
        value = self.get(provider_id)
        if value:
            return value
        provider = get_provider(provider_id)
        message = error_message or (
            f"{provider.env_var} is required for {provider.label}. "
            f"Add it from the dashboard Settings page, run "
            f"`collection-swarm creds set {provider.id}`, or export the env var."
        )
        raise RuntimeError(message)

    def status(self, provider_id: str) -> dict[str, object]:
        provider = get_provider(provider_id)
        stored = self._store.get(provider_id) if self._store is not None else None
        env_set = bool(self._env.get(provider.env_var))
        if stored:
            source: str | None = "store"
        elif env_set:
            source = "env"
        else:
            source = None
        return {
            "id": provider.id,
            "label": provider.label,
            "env_var": provider.env_var,
            "description": provider.description,
            "docs_url": provider.docs_url,
            "configured": stored is not None or env_set,
            "source": source,
            "stored": stored is not None,
            "env_set": env_set,
            "preview": _mask(stored.value) if stored else None,
            "updated_at": stored.updated_at.isoformat() if stored else None,
        }

    def statuses(self, provider_ids: Iterable[str] | None = None) -> list[dict[str, object]]:
        ids = list(provider_ids) if provider_ids is not None else [p.id for p in CREDENTIAL_PROVIDERS]
        return [self.status(pid) for pid in ids]

    def env_overlay(self, provider_ids: Iterable[str] | None = None) -> dict[str, str]:
        """Return env-var-name -> value mapping for stored credentials only.

        Useful for subprocess invocations (e.g. the Cursor SDK Node bridge) so
        we can layer dashboard-stored values on top of ``os.environ`` without
        leaking them into the parent process.
        """
        ids = list(provider_ids) if provider_ids is not None else [p.id for p in CREDENTIAL_PROVIDERS]
        overlay: dict[str, str] = {}
        if self._store is None:
            return overlay
        for pid in ids:
            provider = get_provider(pid)
            stored = self._store.get(pid)
            if stored and stored.value:
                overlay[provider.env_var] = stored.value
        return overlay


def _mask(value: str) -> str:
    """Return a non-sensitive preview of a credential."""
    if not value:
        return ""
    trimmed = value.strip()
    if len(trimmed) <= 8:
        return "*" * len(trimmed)
    return f"{trimmed[:4]}...{trimmed[-4:]}"


__all__ = [
    "CREDENTIAL_PROVIDERS",
    "CredentialProvider",
    "CredentialResolver",
    "CredentialStore",
    "StoredCredential",
    "get_provider",
    "get_provider_by_env",
    "list_providers",
]
