#!/usr/bin/env python3
"""Claude Agent SDK adapter.

Uses claude-agent-sdk (same as EvoSkill) for programmatic agent interaction.
Requires: pip install claude-agent-sdk

Reference:
- SDK: https://github.com/anthropics/claude-agent-sdk-python
- EvoSkill pattern: ClaudeSDKClient async context manager
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, AsyncIterator

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


def _serialize(obj: Any) -> Any:
    """Recursively serialize SDK message objects to JSON-safe dicts.

    Follows autoservice pattern: preserves structure with _type metadata.
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, (list, tuple)):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if hasattr(obj, '__dict__'):
        return {
            '_type': obj.__class__.__name__,
            **{k: _serialize(v) for k, v in vars(obj).items()}
        }
    return str(obj)


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
        """Launch via Claude Agent SDK (same pattern as EvoSkill).

        Uses ClaudeSDKClient for reliable message handling.
        RateLimitEvent is silently collected (not thrown).
        """
        try:
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        except ImportError:
            try:
                # Fallback to claude-code-sdk if claude-agent-sdk not available
                from claude_code_sdk import query, ClaudeCodeOptions
                options = ClaudeCodeOptions(
                    cwd=str(self.config.project_dir),
                    system_prompt=self.config.soul,
                    allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill"],
                )
                try:
                    async for message in query(prompt=prompt, options=options):
                        yield _serialize(message)
                except Exception as e:
                    if "Unknown message type" in str(e):
                        yield {"_type": "Error", "content": f"SDK error (non-fatal): {e}"}
                    else:
                        raise
                return
            except ImportError:
                print("[Claude SDK] Neither claude-agent-sdk nor claude-code-sdk installed.")
                print("  Install: uv pip install 'claude-agent-sdk>=0.1.16'")
                return

        options = ClaudeAgentOptions(
            cwd=str(self.config.project_dir),  # so SDK finds .claude/skills/
            system_prompt=self.config.soul,
            allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Skill"],
            setting_sources=["user", "project"],
            permission_mode="acceptEdits",
        )

        async with ClaudeSDKClient(options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                yield _serialize(message)


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
