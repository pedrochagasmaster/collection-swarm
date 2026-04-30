"""Cursor coding agent via the official TypeScript SDK (subprocess bridge).

See https://github.com/cursor/cookbook — set CURSOR_API_KEY and install bridge deps
(`npm install` in `cursor_sdk_bridge/`). Requires Node.js 22+ on PATH.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from pathlib import Path

from collection_swarm.backends.base import LLMBackend, LLMResponse
from collection_swarm.env import load_dotenv_if_present
from collection_swarm.models import CursorSdkPromptConfig, LLMMessage, ModelConfig


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _bridge_script() -> Path:
    return _repo_root() / "cursor_sdk_bridge" / "run.mjs"


class CursorSdkBackend(LLMBackend):
    def __init__(self, prompts: CursorSdkPromptConfig) -> None:
        self.prompts = prompts

    async def complete(self, model: ModelConfig, messages: list[LLMMessage]) -> LLMResponse:
        load_dotenv_if_present()
        api_key = os.getenv("CURSOR_API_KEY")
        if not api_key:
            raise RuntimeError(
                "CURSOR_API_KEY is required for Cursor SDK models. "
                "Create a key in the Cursor integrations dashboard."
            )

        script = _bridge_script()
        if not script.is_file():
            raise RuntimeError(
                f"Cursor SDK bridge not found at {script}. "
                "Ensure the repository includes the cursor_sdk_bridge directory."
            )

        node = shutil.which("node")
        if not node:
            raise RuntimeError("Node.js is required on PATH for the Cursor SDK backend (Node 22+ recommended).")

        cwd = os.getenv("CURSOR_SDK_WORKSPACE", str(Path.cwd().resolve()))
        model_id = model.model_name or model.id
        payload = json.dumps(
            {
                "messages": [m.model_dump() for m in messages],
                "modelId": model_id,
                "cwd": cwd,
                "preamble": self.prompts.preamble,
            },
            ensure_ascii=False,
        )

        proc = await asyncio.create_subprocess_exec(
            node,
            str(script),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
        )
        stdout_b, stderr_b = await proc.communicate(payload.encode("utf-8"))
        stderr = stderr_b.decode("utf-8", errors="replace").strip()

        try:
            data = json.loads(stdout_b.decode("utf-8"))
        except json.JSONDecodeError as exc:
            preview = stdout_b[:500].decode("utf-8", errors="replace")
            if proc.returncode != 0:
                hint = f" stderr={stderr!r}" if stderr else ""
                raise RuntimeError(
                    f"Cursor SDK bridge exited with code {proc.returncode} and returned "
                    f"non-JSON stdout: {preview!r}.{hint}"
                ) from exc
            raise RuntimeError(f"Cursor SDK bridge returned non-JSON stdout: {preview!r}") from exc

        if "error" in data:
            raise RuntimeError(f"Cursor SDK bridge: {data['error']}")

        if proc.returncode != 0:
            hint = f" stderr={stderr!r}" if stderr else ""
            raise RuntimeError(f"Cursor SDK bridge exited with code {proc.returncode}.{hint}")

        content = str(data.get("content", ""))
        input_tokens = int(data.get("inputTokens", 0) or 0)
        output_tokens = int(data.get("outputTokens", 0) or 0)
        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=_estimate_cost(model, input_tokens, output_tokens),
            model_id=model.id,
            backend="cursor_sdk",
        )


def _estimate_cost(model: ModelConfig, input_tokens: int, output_tokens: int) -> float:
    return (input_tokens / 1_000_000 * model.input_cost_per_m) + (
        output_tokens / 1_000_000 * model.output_cost_per_m
    )
