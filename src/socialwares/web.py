"""Web communication layer — SessionManager for WebSocket streaming.

Sits above the adapter layer, consuming MessageEvent from any adapter
and streaming events to a WebSocket client with heartbeat and session resume.

On Windows, uvicorn 0.36+ uses asyncio.Runner(loop_factory=...) which
bypasses EventLoopPolicy entirely. When --reload or --workers>1 is active,
uvicorn forces SelectorEventLoop, which cannot create subprocesses.

Fix: use a run.py launcher that patches uvicorn's loop factory BEFORE
calling uvicorn.run(). Do NOT use `uv run uvicorn ...` directly.

Usage (run.py + FastAPI):

    # run.py
    import asyncio, sys
    if sys.platform == "win32":
        import uvicorn.loops.asyncio as _uv_loops
        def _proactor_factory(use_subprocess: bool = False):
            return asyncio.ProactorEventLoop
        _uv_loops.asyncio_loop_factory = _proactor_factory

    import uvicorn
    if __name__ == "__main__":
        uvicorn.run("src.app:app", host="0.0.0.0", port=8002, reload=True)

    # src/app.py
    from socialwares.adapters.base import RoleConfig
    from socialwares.adapters.claude.sdk import ClaudeAdapter
    from socialwares.web import SessionManager

    config = RoleConfig.from_runtime(role_dir)
    adapter = ClaudeAdapter(config)
    manager = SessionManager(adapter)

    @app.websocket("/ws/chat")
    async def ws_chat(ws: WebSocket):
        await ws.accept()
        # ... init ...
        while True:
            msg = await ws.receive_json()
            prompt = msg["content"]
            await manager.stream(prompt, ws.send_json)

Not coupled to FastAPI — accepts any async `send(dict)` callable.
"""
from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from socialwares.adapters.base import BaseAdapter, EventKind, MessageEvent


class SessionManager:
    """WebSocket session manager — heartbeat, session resume, event dispatch.

    One instance per WebSocket connection. Maintains SDK session_id across turns
    for multi-turn conversation context.
    """

    def __init__(
        self,
        adapter: BaseAdapter,
        *,
        heartbeat_interval: float = 15.0,
        max_turns: int | None = 20,
    ) -> None:
        self.adapter = adapter
        self.heartbeat_interval = heartbeat_interval
        self.max_turns = max_turns
        self._session_id: str | None = None

    @property
    def session_id(self) -> str | None:
        """Current SDK session ID (None before first turn completes)."""
        return self._session_id

    async def stream(
        self,
        prompt: str,
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        """Process one user message: call adapter, stream events to WebSocket.

        Args:
            prompt: User input text.
            send: Async function to send a JSON dict to the client (e.g. ws.send_json).
        """
        hb_stop = asyncio.Event()

        async def _heartbeat() -> None:
            while not hb_stop.is_set():
                try:
                    await asyncio.wait_for(hb_stop.wait(), timeout=self.heartbeat_interval)
                    break
                except asyncio.TimeoutError:
                    pass
                try:
                    await send({"type": "heartbeat"})
                except Exception:
                    break

        hb_task = asyncio.create_task(_heartbeat())

        try:
            async for event in self.adapter.launch_sdk(
                prompt,
                session_id=self._session_id,
                max_turns=self.max_turns,
            ):
                ws_msg = self._event_to_ws(event)
                if ws_msg:
                    try:
                        await send(ws_msg)
                    except Exception:
                        break  # Client disconnected, stop streaming

                if event.kind == EventKind.SESSION_END and event.session_id:
                    self._session_id = event.session_id
        finally:
            hb_stop.set()
            hb_task.cancel()
            try:
                await send({"type": "done"})
            except Exception:
                pass  # Client already disconnected

    @staticmethod
    def _event_to_ws(event: MessageEvent) -> dict[str, Any] | None:
        """Convert a MessageEvent to a WebSocket JSON message.

        Returns None for events that are internal (not sent to client).
        """
        match event.kind:
            case EventKind.TEXT_DELTA:
                return {"type": "text_delta", "content": event.content}
            case EventKind.TOOL_START:
                return {
                    "type": "tool_start",
                    "tool": event.tool_name,
                    "preview": str(event.tool_input)[:120],
                }
            case EventKind.TOOL_RESULT:
                return {
                    "type": "tool_result",
                    "tool": event.tool_name,
                    "output": event.tool_output[:200],
                }
            case EventKind.SUBAGENT_START:
                return {
                    "type": "subagent_start",
                    "name": event.tool_name,
                }
            case EventKind.SUBAGENT_RESULT:
                return {
                    "type": "subagent_result",
                    "name": event.tool_name,
                    "output": event.tool_output[:200],
                }
            case EventKind.ERROR:
                return {"type": "error", "content": event.content}
            case EventKind.TURN_START | EventKind.TURN_END | EventKind.SESSION_END:
                return None  # Internal lifecycle — not sent to client
            case _:
                return None
