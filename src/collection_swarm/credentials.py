"""Dashboard-managed API key storage and lookup."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from collection_swarm.env import load_dotenv_if_present


@dataclass(frozen=True)
class ApiKeyProviderInfo:
    provider: str
    label: str
    env_var: str
    configured: bool
    source: str | None = None
    masked_value: str | None = None


class ApiKeyProvider(Protocol):
    def get_api_key(self, provider: str) -> str | None:
        """Return an API key for a known provider, if one is configured."""


SUPPORTED_API_KEY_PROVIDERS: dict[str, tuple[str, str]] = {
    "cursor": ("Cursor", "CURSOR_API_KEY"),
    "nvidia_nim": ("NVIDIA NIM", "NVIDIA_NIM_API_KEY"),
}


def mask_api_key(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


class CredentialStore(ApiKeyProvider):
    def __init__(self, path: Path | str = "output/collection_swarm.sqlite") -> None:
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
                """
                CREATE TABLE IF NOT EXISTS api_keys (
                    provider TEXT PRIMARY KEY,
                    api_key TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def list_api_keys(self) -> list[ApiKeyProviderInfo]:
        load_dotenv_if_present()
        with self._connect() as connection:
            stored = {
                row["provider"]: row["api_key"]
                for row in connection.execute("SELECT provider, api_key FROM api_keys").fetchall()
            }
        infos = []
        for provider, (label, env_var) in SUPPORTED_API_KEY_PROVIDERS.items():
            stored_value = stored.get(provider)
            env_value = os.getenv(env_var)
            value = stored_value or env_value
            source = "dashboard" if stored_value else ("env" if env_value else None)
            infos.append(
                ApiKeyProviderInfo(
                    provider=provider,
                    label=label,
                    env_var=env_var,
                    configured=bool(value),
                    source=source,
                    masked_value=mask_api_key(value),
                )
            )
        return infos

    def get_api_key(self, provider: str) -> str | None:
        self._validate_provider(provider)
        load_dotenv_if_present()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT api_key FROM api_keys WHERE provider = ?",
                (provider,),
            ).fetchone()
        if row is not None:
            return str(row["api_key"])
        env_var = SUPPORTED_API_KEY_PROVIDERS[provider][1]
        return os.getenv(env_var) or None

    def set_api_key(self, provider: str, api_key: str) -> ApiKeyProviderInfo:
        self._validate_provider(provider)
        clean_key = api_key.strip()
        if not clean_key:
            raise ValueError("api_key cannot be empty")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO api_keys (provider, api_key, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(provider) DO UPDATE SET
                    api_key = excluded.api_key,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (provider, clean_key),
            )
        return self._info_for_stored_key(provider, clean_key)

    def clear_api_key(self, provider: str) -> ApiKeyProviderInfo:
        self._validate_provider(provider)
        with self._connect() as connection:
            connection.execute("DELETE FROM api_keys WHERE provider = ?", (provider,))
        return next(info for info in self.list_api_keys() if info.provider == provider)

    def _info_for_stored_key(self, provider: str, value: str) -> ApiKeyProviderInfo:
        label, env_var = SUPPORTED_API_KEY_PROVIDERS[provider]
        return ApiKeyProviderInfo(
            provider=provider,
            label=label,
            env_var=env_var,
            configured=True,
            source="dashboard",
            masked_value=mask_api_key(value),
        )

    def _validate_provider(self, provider: str) -> None:
        if provider not in SUPPORTED_API_KEY_PROVIDERS:
            raise KeyError(provider)
