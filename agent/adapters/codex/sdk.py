#!/usr/bin/env python3
"""OpenAI Codex/Agents SDK adapter.

Launches agent programmatically using OpenAI Agents SDK.
Requires: pip install openai-agents

Reference:
- CLI: https://openai.github.io/codex/cli/reference
- SDK: https://openai.github.io/openai-agents-python/
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, AsyncIterator

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


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
        """Launch via OpenAI Agents SDK with built-in tracing."""
        try:
            from agents import Agent, Runner
        except ImportError:
            print("[Codex SDK] openai-agents not installed.")
            print("  Install: pip install openai-agents")
            return

        agent = Agent(
            name=self.config.name,
            instructions=self.config.soul,
        )

        # OpenAI Agents SDK has built-in tracing (enabled by default)
        # Traces go to OpenAI dashboard; local saving via trace processors
        result = await Runner.run(agent, prompt)

        # Yield the final output as a single message
        yield {
            "role": "assistant",
            "content": result.final_output,
            "trace_id": getattr(result, "trace_id", None),
        }


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
