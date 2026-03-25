#!/usr/bin/env python3
"""OpenAI Codex/Agents SDK adapter.

Uses openai-agents SDK for programmatic agent interaction.
Built-in tracing to OpenAI dashboard.
Requires: uv pip install 'openai-agents>=0.10.0'

Reference:
- CLI: https://openai.github.io/codex/cli/reference
- SDK: https://openai.github.io/openai-agents-python/
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, AsyncIterator

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig, serialize


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

    async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
        """Launch via OpenAI Agents SDK.

        Yields serialized message dicts. Uses same serialize() as Claude adapter.
        Built-in tracing enabled by default (traces go to OpenAI dashboard).
        """
        try:
            from agents import Agent, Runner
        except ImportError:
            print("[Codex SDK] openai-agents not installed.")
            print("  Install: uv pip install 'openai-agents>=0.10.0'")
            return

        agent = Agent(
            name=self.config.name,
            instructions=self.config.soul,
        )

        # Run agent — OpenAI SDK returns a RunResult with full trace
        result = await Runner.run(agent, prompt)

        # Yield all raw messages from the run for complete trace
        for item in result.raw_responses:
            yield serialize(item)

        # Yield final result as structured summary
        yield serialize({
            "_type": "ResultMessage",
            "content": result.final_output,
            "trace_id": getattr(result, "trace_id", None),
            "is_error": False,
        })


if __name__ == "__main__":
    import argparse
    import asyncio
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir")
    parser.add_argument("--prompt", default="You are ready.")
    args = parser.parse_args()
    config = RoleConfig.from_runtime(args.project_dir)

    async def main():
        async for msg in CodexAdapter(config).launch_sdk(args.prompt):
            print(msg)

    asyncio.run(main())
