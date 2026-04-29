"""Cursor ACP backend.

Cursor's CLI exposes `agent acp`, a newline-delimited JSON-RPC server over
stdio. This backend keeps one short-lived ACP subprocess per completion so
failures are isolated and the implementation stays safe for batch simulations.
Install/authenticate the Cursor CLI separately with `agent login` or
`CURSOR_API_KEY`/`CURSOR_AUTH_TOKEN`.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from collections.abc import Mapping
from itertools import count
from pathlib import Path
from typing import Any

from collection_swarm.backends.base import LLMResponse
from collection_swarm.models import LLMMessage, ModelConfig


class AcpBackend:
    def __init__(self, command: str | None = None, cwd: Path | str | None = None, timeout_seconds: float = 120.0) -> None:
        self.command = command or os.getenv("CURSOR_ACP_COMMAND") or "agent"
        self.cwd = Path(cwd or os.getcwd())
        self.timeout_seconds = timeout_seconds

    async def complete(self, model: ModelConfig, messages: list[LLMMessage]) -> LLMResponse:
        if shutil.which(self.command) is None:
            raise RuntimeError(
                f"Cursor ACP command '{self.command}' was not found. Install/authenticate Cursor CLI "
                "so `agent acp` is available, or set CURSOR_ACP_COMMAND."
            )

        client = _AcpJsonRpcClient(self.command, self.cwd)
        try:
            await asyncio.wait_for(client.start(), timeout=self.timeout_seconds)
            await asyncio.wait_for(client.initialize(), timeout=self.timeout_seconds)
            prompt_text = _messages_to_prompt(messages)
            content = await asyncio.wait_for(client.prompt(prompt_text, model.id), timeout=self.timeout_seconds)
            return LLMResponse(
                content=content,
                input_tokens=sum(len(message.content.split()) for message in messages),
                output_tokens=len(content.split()),
                estimated_cost_usd=0.0,
                model_id=model.id,
                backend="acp",
            )
        finally:
            await client.close()


class _AcpJsonRpcClient:
    def __init__(self, command: str, cwd: Path) -> None:
        self.command = command
        self.cwd = cwd
        self._ids = count(1)
        self._pending: dict[int, asyncio.Future[Mapping[str, Any]]] = {}
        self._chunks: list[str] = []
        self._process: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._process = await asyncio.create_subprocess_exec(
            self.command,
            "acp",
            cwd=self.cwd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._reader_task = asyncio.create_task(self._read_stdout())

    async def initialize(self) -> None:
        await self.request(
            "initialize",
            {
                "protocolVersion": 1,
                "clientCapabilities": {"fs": {"readTextFile": False, "writeTextFile": False}, "terminal": False},
                "clientInfo": {"name": "collection-swarm", "version": "0.1.0"},
            },
        )
        await self.request("authenticate", {"methodId": "cursor_login"})
        session = await self.request("session/new", {"cwd": str(self.cwd), "mcpServers": []})
        self.session_id = str(session["sessionId"])

    async def prompt(self, prompt_text: str, model_id: str) -> str:
        params: dict[str, Any] = {
            "sessionId": self.session_id,
            "prompt": [{"type": "text", "text": prompt_text}],
        }
        if model_id != "cursor-agent":
            params["model"] = model_id
        await self.request("session/prompt", params)
        return "".join(self._chunks).strip()

    async def request(self, method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        request_id = next(self._ids)
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Mapping[str, Any]] = loop.create_future()
        self._pending[request_id] = future
        await self._write({"jsonrpc": "2.0", "id": request_id, "method": method, "params": dict(params)})
        return await future

    async def close(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
        if self._process:
            if self._process.stdin:
                self._process.stdin.close()
                try:
                    await self._process.stdin.wait_closed()
                except (BrokenPipeError, ConnectionResetError):
                    pass
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self._process.kill()

    async def _write(self, payload: Mapping[str, Any]) -> None:
        if not self._process or not self._process.stdin:
            raise RuntimeError("ACP process is not running")
        self._process.stdin.write(json.dumps(payload).encode("utf-8") + b"\n")
        # JSON-RPC messages are newline-delimited; flush each request promptly so
        # the ACP subprocess can respond without waiting for buffer pressure.
        await self._process.stdin.drain()

    async def _read_stdout(self) -> None:
        if not self._process or not self._process.stdout:
            return
        while line := await self._process.stdout.readline():
            message = json.loads(line.decode("utf-8"))
            if "id" in message and ("result" in message or "error" in message):
                pending = self._pending.pop(int(message["id"]), None)
                if pending:
                    if "error" in message:
                        pending.set_exception(RuntimeError(str(message["error"])))
                    else:
                        pending.set_result(message.get("result") or {})
                continue
            if message.get("method") == "session/update":
                self._record_update(message.get("params", {}))
                continue
            if message.get("method") == "session/request_permission" and "id" in message:
                await self._write(
                    {
                        "jsonrpc": "2.0",
                        "id": message["id"],
                        "result": {"outcome": {"outcome": "selected", "optionId": "reject-once"}},
                    }
                )

    def _record_update(self, params: Mapping[str, Any]) -> None:
        update = params.get("update", {})
        if not isinstance(update, Mapping):
            return
        if update.get("sessionUpdate") == "agent_message_chunk":
            content = update.get("content", {})
            if isinstance(content, Mapping) and isinstance(content.get("text"), str):
                self._chunks.append(content["text"])


def _messages_to_prompt(messages: list[LLMMessage]) -> str:
    return "\n\n".join(f"{message.role.upper()}:\n{message.content}" for message in messages)
