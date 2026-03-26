#!/usr/bin/env python3
"""Claude Agent SDK adapter.

Uses claude-agent-sdk for programmatic agent interaction.
Requires: uv pip install 'claude-agent-sdk>=0.1.16'

Reference:
- SDK: https://github.com/anthropics/claude-agent-sdk-python
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, AsyncIterator

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig, serialize


class ClaudeAdapter(BaseAdapter):
    """Claude Agent SDK adapter."""

    def launch_shell(self) -> None:
        """Launch Claude Code TUI via CLI."""
        import subprocess
        cmd = ["claude", "--dangerously-skip-permissions"]

        soul_path = self.config.project_dir / "SOUL.md"
        if soul_path.exists():
            cmd.extend(["--append-system-prompt-file", str(soul_path)])

        subprocess.run(cmd, cwd=str(self.config.project_dir))

    async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
        """Launch via Claude Agent SDK.

        Yields serialized message dicts. Uses ClaudeSDKClient pattern (same as EvoSkill).
        """
        try:
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        except ImportError:
            print("[Claude SDK] claude-agent-sdk not installed.")
            print("  Install: uv pip install 'claude-agent-sdk>=0.1.16'")
            return

        project_dir = str(self.config.project_dir)
        options = ClaudeAgentOptions(
            cwd=project_dir,
            system_prompt=self.config.soul,
            allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill"],
            setting_sources=["user", "project", "local"],
            permission_mode="acceptEdits",
        )

        async with ClaudeSDKClient(options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                yield serialize(message)


if __name__ == "__main__":
    import argparse
    import asyncio
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", help="Path to .runtime/agents/{role}/")
    parser.add_argument("--prompt", default="You are ready.", help="Initial prompt")
    args = parser.parse_args()

    config = RoleConfig.from_runtime(args.project_dir)
    adapter = ClaudeAdapter(config)

    async def main():
        async for msg in adapter.launch_sdk(args.prompt):
            print(msg)

    asyncio.run(main())
