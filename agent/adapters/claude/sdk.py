#!/usr/bin/env python3
"""Claude Agent SDK adapter.

Launches agent programmatically using Claude Agent SDK.
Used by src/start_agent.py for production deployment.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


class ClaudeAdapter(BaseAdapter):
    """Claude Agent SDK adapter."""

    def launch_shell(self) -> None:
        import subprocess
        subprocess.run([
            "claude",
            "--project-dir", str(self.config.project_dir),
            "--permission-mode", "bypassPermissions",
        ])

    def launch_sdk(self) -> None:
        print(f"[Claude SDK] Launching {self.config.name}")
        print(f"[Claude SDK] PROJECT_DIR: {self.config.project_dir}")
        print(f"[Claude SDK] SOUL.md: {len(self.config.soul)} chars")

        # TODO: Replace with actual Claude Agent SDK
        # from claude_agent_sdk import Agent
        # agent = Agent(
        #     model="claude-sonnet-4-6",
        #     system_prompt=self.config.soul,
        #     project_dir=str(self.config.project_dir),
        # )
        # agent.run()

        print("[Claude SDK] Mock mode — SDK not installed yet")


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
