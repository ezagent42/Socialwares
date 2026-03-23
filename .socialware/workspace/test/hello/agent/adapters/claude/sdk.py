#!/usr/bin/env python3
"""Claude Agent SDK adapter.

Launches agent programmatically using Claude Agent SDK.
Used by src/start_agent.py for production deployment.

Reference:
- CLI: https://docs.anthropic.com/en/docs/claude-code/cli-reference
- SDK: https://docs.anthropic.com/en/docs/claude-code/sdk-reference
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


class ClaudeAdapter(BaseAdapter):
    """Claude Agent SDK adapter."""

    def launch_shell(self) -> None:
        """Launch Claude Code TUI via CLI."""
        cmd = ["claude", "--dangerously-skip-permissions"]

        soul_path = self.config.project_dir / "SOUL.md"
        if soul_path.exists():
            cmd.extend(["--append-system-prompt-file", str(soul_path)])

        subprocess.run(cmd, cwd=str(self.config.project_dir))

    def launch_sdk(self) -> None:
        """Launch programmatically via Claude Agent SDK."""
        print(f"[Claude SDK] Launching {self.config.name}")
        print(f"[Claude SDK] Working dir: {self.config.project_dir}")
        print(f"[Claude SDK] SOUL.md: {len(self.config.soul)} chars")

        # Claude Agent SDK uses claude_code_sdk
        # Reference: https://docs.anthropic.com/en/docs/claude-code/sdk-reference
        try:
            from claude_code_sdk import query

            result = query(
                prompt="You are ready. Wait for instructions.",
                options={
                    "cwd": str(self.config.project_dir),
                    "system_prompt": self.config.soul,
                    "permission_mode": "plan",
                },
            )
            print(result)
        except ImportError:
            print("[Claude SDK] claude_code_sdk not installed.")
            print("  Install: pip install claude-code-sdk")
            print(f"  Falling back to CLI mode...")
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
