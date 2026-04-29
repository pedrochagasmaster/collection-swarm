"""Environment loading helpers."""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_if_present(path: Path | None = None) -> None:
    """Load simple KEY=VALUE entries from .env without overriding real env vars."""
    dotenv_path = path or _default_dotenv_path()
    if not dotenv_path.is_file():
        return

    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = _strip_quotes(value.strip())


def _default_dotenv_path() -> Path:
    cwd_dotenv = Path.cwd() / ".env"
    if cwd_dotenv.is_file():
        return cwd_dotenv
    return Path(__file__).resolve().parents[2] / ".env"


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
