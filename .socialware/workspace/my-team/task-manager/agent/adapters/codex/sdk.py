#!/usr/bin/env python3
"""OpenAI Codex/Agents SDK adapter.

Reference:
- CLI: https://openai.github.io/codex/cli/reference
- SDK: https://openai.github.io/openai-agents-python/
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


class CodexAdapter(BaseAdapter):
    """OpenAI Codex CLI / Agents SDK adapter."""

    def launch_shell(self) -> None:
        """Launch via Codex CLI."""
        subprocess.run([
            "codex",
            "--cd", str(self.config.project_dir),
            "--full-auto",
        ])

    def launch_sdk(self) -> None:
        """Launch programmatically via OpenAI Agents SDK."""
        print(f"[Codex SDK] Launching {self.config.name}")
        print(f"[Codex SDK] Working dir: {self.config.project_dir}")

        try:
            from agents import Agent, Runner

            agent = Agent(
                name=self.config.name,
                instructions=self.config.soul,
            )
            result = Runner.run_sync(agent, "You are ready. Wait for instructions.")
            print(result.final_output)
        except ImportError:
            print("[Codex SDK] openai-agents not installed.")
            print("  Install: pip install openai-agents")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir")
    args = parser.parse_args()
    config = RoleConfig.from_runtime(args.project_dir)
    CodexAdapter(config).launch_sdk()
