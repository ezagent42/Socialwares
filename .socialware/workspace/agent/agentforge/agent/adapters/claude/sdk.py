#!/usr/bin/env python3
"""Claude Code adapter — long-running session via ClaudeSDKClient.

Uses ClaudeSDKClient for stateful, multi-turn conversations.
The agent stays connected across multiple query() calls, maintaining
full conversation context.

Lifecycle: connect() → query() × N → disconnect()

Reference:
- CLI: https://docs.anthropic.com/en/docs/claude-code/cli-reference
- SDK: https://docs.anthropic.com/en/docs/claude-code/sdk-reference
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


class ClaudeAdapter(BaseAdapter):
    """Claude Code adapter using ClaudeSDKClient for persistent sessions."""

    def __init__(self, config: RoleConfig) -> None:
        super().__init__(config)
        self._client = None

    def launch_shell(self) -> None:
        """Launch Claude Code TUI via CLI."""
        cmd = ["claude", "--dangerously-skip-permissions"]
        soul_path = self.config.project_dir / "SOUL.md"
        if soul_path.exists():
            cmd.extend(["--append-system-prompt-file", str(soul_path)])
        subprocess.run(cmd, cwd=str(self.config.project_dir))

    @classmethod
    def is_available(cls) -> bool:
        return shutil.which("claude") is not None

    async def connect(self) -> None:
        """Start a long-running Claude Code session."""
        os.environ["PYTHONUTF8"] = "1"
        os.environ["PYTHONIOENCODING"] = "utf-8"

        from claude_code_sdk import ClaudeSDKClient, ClaudeCodeOptions

        # Use project_dir as cwd so Claude Code finds .claude/skills/
        project_dir = self.config.project_dir

        # Use file for system prompt (inline breaks on Windows)
        soul_path = project_dir / "SOUL.md"
        extra = {
            # Only load project-level settings, skip user-level (global plugins).
            # This preserves OAuth auth while preventing superpowers etc. from loading.
            "setting-sources": "project,local",
        }
        if soul_path.exists():
            extra["append-system-prompt-file"] = str(soul_path)

        options = ClaudeCodeOptions(
            cwd=str(project_dir),
            permission_mode="bypassPermissions",
            extra_args=extra,
        )

        self._client = ClaudeSDKClient(options)
        await self._client.connect()
        self._connected = True

    async def disconnect(self) -> None:
        """Close the Claude Code session."""
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None
        self._connected = False

    async def query(self, prompt: str) -> list[dict]:
        """Send a prompt within the active session, return text responses.

        Reads raw JSON events from the underlying transport to avoid
        MessageParseError on unknown event types (e.g. rate_limit_event).
        """
        if not self._client or not self._connected:
            await self.connect()

        await self._client.query(prompt)

        messages: list[dict] = []
        try:
            # Read raw dicts from the internal query stream so that
            # unknown message types (rate_limit_event, etc.) don't crash.
            raw_stream = self._client._query.receive_messages()
            async for data in raw_stream:
                msg_type = data.get("type")
                if msg_type == "assistant":
                    for block in data.get("message", {}).get("content", []):
                        if block.get("type") == "text" and block.get("text"):
                            messages.append({"type": "text", "text": block["text"]})
                elif msg_type == "result":
                    # Response complete
                    break
        except Exception as e:
            if not messages:
                messages.append({"type": "text", "text": f"[Claude error] {e}"})

        return messages

    def launch_sdk(self) -> None:
        """Launch programmatically."""
        import asyncio
        print(f"[Claude] Launching {self.config.name}")
        try:
            async def run():
                await self.connect()
                result = await self.query("You are ready. Wait for instructions.")
                for msg in result:
                    print(msg.get("text", ""))
                await self.disconnect()
            asyncio.run(run())
        except Exception as e:
            print(f"[Claude] Error: {e}, falling back to shell...")
            self.launch_shell()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir", help="Path to .runtime/agents/{role}/")
    parser.add_argument("--mode", default="sdk", choices=["shell", "sdk"])
    args = parser.parse_args()
    config = RoleConfig.from_runtime(args.project_dir)
    adapter = ClaudeAdapter(config)
    if args.mode == "shell":
        adapter.launch_shell()
    else:
        adapter.launch_sdk()
