#!/usr/bin/env python3
"""OpenAI Codex/Agents SDK adapter.

Uses openai-agents SDK for programmatic agent interaction.
Built-in tracing to OpenAI dashboard.
Requires: uv pip install 'openai-agents>=0.10.0'

v0.3.0: yield MessageEvent instead of serialize(msg) dicts.

Reference:
- CLI: https://openai.github.io/codex/cli/reference
- SDK: https://openai.github.io/openai-agents-python/
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import AsyncIterator

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig, EventKind, MessageEvent


class CodexAdapter(BaseAdapter):
    """OpenAI Codex CLI / Agents SDK adapter."""

    def launch_shell(self) -> None:
        """Launch via Codex CLI."""
        import subprocess
        subprocess.run([
            "codex",
            "--cd", str(self.config.project_dir),
            "--full-auto",
        ])

    async def launch_sdk(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        max_turns: int | None = None,
    ) -> AsyncIterator[MessageEvent]:
        """Launch via OpenAI Agents SDK, yielding MessageEvent.

        Note: OpenAI Agents SDK currently runs synchronously (no streaming).
        The entire result is returned at once, then emitted as a single TEXT_DELTA.
        """
        try:
            from agents import Agent, Runner
        except ImportError:
            yield MessageEvent(
                kind=EventKind.ERROR,
                content="openai-agents not installed. Install: uv pip install 'openai-agents>=0.10.0'",
            )
            return

        agent = Agent(
            name=self.config.name,
            instructions=self.config.soul,
        )

        yield MessageEvent(kind=EventKind.TURN_START)

        # OpenAI SDK is synchronous — returns RunResult after completion
        result = await Runner.run(agent, prompt)

        # Emit final output as a single text delta
        if result.final_output:
            yield MessageEvent(
                kind=EventKind.TEXT_DELTA,
                content=result.final_output,
            )

        yield MessageEvent(
            kind=EventKind.SESSION_END,
            metadata={
                "trace_id": getattr(result, "trace_id", None),
            },
        )

        yield MessageEvent(kind=EventKind.TURN_END)


if __name__ == "__main__":
    import argparse
    import asyncio
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir")
    parser.add_argument("--prompt", default="You are ready.")
    args = parser.parse_args()
    config = RoleConfig.from_runtime(args.project_dir)

    async def main():
        async for event in CodexAdapter(config).launch_sdk(args.prompt):
            if event.kind == EventKind.TEXT_DELTA:
                print(event.content, end="", flush=True)
            elif event.kind == EventKind.ERROR:
                print(f"[error] {event.content}", flush=True)

    asyncio.run(main())
