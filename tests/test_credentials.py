"""Tests for the dashboard-managed credential subsystem."""

from __future__ import annotations

from collections import OrderedDict

import pytest

from collection_swarm.backends.cursor_sdk import CursorSdkBackend
from collection_swarm.backends.nim import NimBackend
from collection_swarm.credentials import (
    CredentialResolver,
    CredentialStore,
    get_provider,
    list_providers,
)
from collection_swarm.models import CursorSdkPromptConfig, ModelConfig


def _empty_env() -> dict[str, str]:
    return {}


def test_store_round_trip_persists_credentials(tmp_path) -> None:
    store = CredentialStore(tmp_path / "creds.sqlite")

    saved = store.set("cursor", "key_abcd1234")

    assert saved.value == "key_abcd1234"
    fetched = store.get("cursor")
    assert fetched is not None
    assert fetched.value == "key_abcd1234"
    assert "cursor" in store.all()


def test_store_rejects_empty_values(tmp_path) -> None:
    store = CredentialStore(tmp_path / "creds.sqlite")

    with pytest.raises(ValueError):
        store.set("cursor", "   ")


def test_store_strips_whitespace(tmp_path) -> None:
    store = CredentialStore(tmp_path / "creds.sqlite")

    store.set("cursor", "  trimmed_value  ")

    assert store.get("cursor").value == "trimmed_value"  # type: ignore[union-attr]


def test_store_delete_removes_credential(tmp_path) -> None:
    store = CredentialStore(tmp_path / "creds.sqlite")
    store.set("cursor", "foo")

    assert store.delete("cursor") is True
    assert store.get("cursor") is None
    assert store.delete("cursor") is False


def test_store_unknown_provider_raises(tmp_path) -> None:
    store = CredentialStore(tmp_path / "creds.sqlite")

    with pytest.raises(KeyError):
        store.set("does_not_exist", "value")


def test_resolver_prefers_store_over_env(tmp_path) -> None:
    store = CredentialStore(tmp_path / "creds.sqlite")
    store.set("cursor", "stored_value")
    resolver = CredentialResolver(store=store, env={"CURSOR_API_KEY": "env_value"})

    assert resolver.get("cursor") == "stored_value"


def test_resolver_falls_back_to_env(tmp_path) -> None:
    store = CredentialStore(tmp_path / "creds.sqlite")
    resolver = CredentialResolver(store=store, env={"NVIDIA_NIM_API_KEY": "env_value"})

    assert resolver.get("nvidia_nim") == "env_value"


def test_resolver_returns_none_when_unconfigured(tmp_path) -> None:
    store = CredentialStore(tmp_path / "creds.sqlite")
    resolver = CredentialResolver(store=store, env=_empty_env())

    assert resolver.get("cursor") is None
    with pytest.raises(RuntimeError, match="CURSOR_API_KEY is required"):
        resolver.require("cursor")


def test_resolver_status_reports_source_and_preview(tmp_path) -> None:
    store = CredentialStore(tmp_path / "creds.sqlite")
    store.set("cursor", "abcdefghijkl1234")
    resolver = CredentialResolver(store=store, env={"NVIDIA_NIM_API_KEY": "from_env_value"})

    statuses = {s["id"]: s for s in resolver.statuses()}

    assert statuses["cursor"]["source"] == "store"
    assert statuses["cursor"]["preview"] == "abcd...1234"
    assert statuses["cursor"]["env_set"] is False
    assert statuses["nvidia_nim"]["source"] == "env"
    assert statuses["nvidia_nim"]["env_set"] is True
    assert statuses["nvidia_nim"]["preview"] is None


def test_resolver_env_overlay_only_includes_stored(tmp_path) -> None:
    store = CredentialStore(tmp_path / "creds.sqlite")
    store.set("cursor", "stored")
    resolver = CredentialResolver(store=store, env={"NVIDIA_NIM_API_KEY": "env"})

    overlay = resolver.env_overlay()

    assert overlay == {"CURSOR_API_KEY": "stored"}


async def test_nim_backend_uses_stored_credential_first(monkeypatch, tmp_path) -> None:
    store = CredentialStore(tmp_path / "creds.sqlite")
    store.set("nvidia_nim", "from_store_key")
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)

    captured: dict[str, object] = {}

    async def fake_completion(**kwargs):
        captured.update(kwargs)

        class _Choice:
            class message:  # noqa: N801
                content = "ok"

        class _Resp:
            choices = [_Choice]
            usage = type("Usage", (), {"prompt_tokens": 1, "completion_tokens": 2})()

        return _Resp()

    monkeypatch.setattr("collection_swarm.backends.nim.acompletion", fake_completion)

    backend = NimBackend(credentials=CredentialResolver(store=store, env={}))
    response = await backend.complete(
        ModelConfig(id="nim-test", backend="nim", litellm_model="nim/test"),
        [],
    )

    assert captured["api_key"] == "from_store_key"
    assert response.backend == "nim"


async def test_nim_backend_surfaces_friendly_error_when_unset(monkeypatch, tmp_path) -> None:
    store = CredentialStore(tmp_path / "creds.sqlite")
    monkeypatch.delenv("NVIDIA_NIM_API_KEY", raising=False)
    backend = NimBackend(credentials=CredentialResolver(store=store, env={}))

    with pytest.raises(RuntimeError, match="dashboard Settings page"):
        await backend.complete(
            ModelConfig(id="nim-test", backend="nim", litellm_model="nim/test"),
            [],
        )


async def test_cursor_sdk_backend_surfaces_friendly_error_when_unset(monkeypatch, tmp_path) -> None:
    store = CredentialStore(tmp_path / "creds.sqlite")
    monkeypatch.delenv("CURSOR_API_KEY", raising=False)
    backend = CursorSdkBackend(
        CursorSdkPromptConfig(preamble="x"),
        credentials=CredentialResolver(store=store, env={}),
    )

    with pytest.raises(RuntimeError, match="dashboard Settings page"):
        await backend.complete(
            ModelConfig(id="cursor-test", backend="cursor_sdk", model_name="gpt-5.5"),
            [],
        )


def test_provider_registry_is_stable() -> None:
    ids = [p.id for p in list_providers()]

    assert ids == ["cursor", "nvidia_nim"]
    assert get_provider("cursor").env_var == "CURSOR_API_KEY"
    assert get_provider("nvidia_nim").env_var == "NVIDIA_NIM_API_KEY"
    with pytest.raises(KeyError):
        get_provider("unknown")


def test_resolver_handles_ordereddict_env(tmp_path) -> None:
    """Defensive: any Mapping should work, not only os.environ."""
    store = CredentialStore(tmp_path / "creds.sqlite")
    env = OrderedDict({"CURSOR_API_KEY": "from_env"})
    resolver = CredentialResolver(store=store, env=env)

    assert resolver.get("cursor") == "from_env"
