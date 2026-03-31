#!/usr/bin/env python3
"""Claude Code SDK adapter.

Uses claude-code-sdk for programmatic agent interaction.
Requires: uv pip install claude-code-sdk

Reference:
- SDK: https://docs.anthropic.com/en/docs/claude-code/sdk-reference
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, AsyncIterator

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig, serialize


class ClaudeAdapter(BaseAdapter):
    """Claude Code SDK adapter."""

    def launch_shell(self) -> None:
        """Launch Claude Code TUI via CLI."""
        import subprocess
        cmd = ["claude", "--dangerously-skip-permissions"]

        soul_path = self.config.project_dir / "SOUL.md"
        if soul_path.exists():
            cmd.extend(["--append-system-prompt-file", str(soul_path)])

        subprocess.run(cmd, cwd=str(self.config.project_dir))

    async def launch_sdk(self, prompt: str) -> AsyncIterator[Any]:
        """Launch via Claude Code SDK.

        Yields serialized message dicts from the streaming query.
        """
        try:
            from claude_code_sdk import query, ClaudeCodeOptions
        except ImportError:
            yield serialize({
                "_type": "ErrorMessage",
                "content": "claude-code-sdk not installed. Run: uv pip install claude-code-sdk",
            })
            return

        # Use workspace root as cwd (not .runtime/agents/role/ which is too deep)
        cwd = str(self.config.workspace_root) if self.config.workspace_root else str(self.config.project_dir)

        options = ClaudeCodeOptions(
            cwd=cwd,
            system_prompt=self.config.soul,
            allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep"],
            permission_mode="bypassPermissions",
        )

        import logging
        logger = logging.getLogger("claude_adapter")

        try:
            async for message in query(prompt=prompt, options=options):
                logger.info("SDK message: %s", type(message).__name__)
                yield serialize(message)
        except Exception as e:
            err_str = str(e)
            # SDK may throw on unknown message types (e.g. rate_limit_event)
            if "Unknown message type" in err_str:
                logger.warning("Ignored SDK parse error: %s", err_str)
            else:
                logger.error("SDK error: %s", err_str)
                raise


if __name__ == "__main__":
    import argparse
    import asyncio
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", help="Path to .runtime/agents/{role}/")
    parser.add_argument("--prompt", default="check health", help="Prompt to send")
    args = parser.parse_args()

    config = RoleConfig.from_runtime(args.project_dir)
    adapter = ClaudeAdapter(config)

    async def main():
        async for msg in adapter.launch_sdk(args.prompt):
            print(msg)

    asyncio.run(main())
