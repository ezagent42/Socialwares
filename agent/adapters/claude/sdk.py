#!/usr/bin/env python3
"""Claude Agent SDK adapter.

Launches agent programmatically using Claude Agent SDK.
Requires: pip install claude-code-sdk

Reference:
- CLI: https://docs.anthropic.com/en/docs/claude-code/cli-reference
- SDK: https://docs.anthropic.com/en/docs/claude-code/sdk-reference
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, AsyncIterator

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


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
        """Launch via Claude Agent SDK with full config loading."""
        try:
            from claude_code_sdk import query, ClaudeCodeOptions
        except ImportError:
            print("[Claude SDK] claude-code-sdk not installed.")
            print("  Install: pip install claude-code-sdk")
            return

        options = ClaudeCodeOptions(
            cwd=str(self.config.project_dir),
            system_prompt=self.config.soul,
            allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill"],
        )

        async for message in query(prompt=prompt, options=options):
            yield message


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
