#!/usr/bin/env python3
"""OpenAI Codex/Agents SDK launcher.

Reads GitAgent directory and launches via OpenAI Agents SDK.

Usage:
  uv run launcher.py --agent-dir ../../
  uv run launcher.py --agent-dir ../../agents/code-reviewer --task "Review PR #42"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import AgentConfig, BaseAdapter


class CodexAdapter(BaseAdapter):
    """OpenAI Agents SDK adapter."""

    def build_system_prompt(self) -> str:
        parts = [self.config.soul]
        if self.config.rules:
            parts.append(f"\n---\n{self.config.rules}")
        return "\n".join(parts)

    def launch(self) -> None:
        print(f"[Codex Adapter] Launching agent: {self.config.name}")
        print(f"[Codex Adapter] Model: gpt-4o (mapped from {self.config.model_preferred})")
        print("[Codex Adapter] Mock mode — SDK not installed yet")

    def launch_headless(self, task: str) -> str:
        print(f"[Codex Adapter] Headless task: {task}")
        return f"[Mock] Would execute via OpenAI Agents SDK: {task}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch agent via Codex SDK")
    parser.add_argument("--agent-dir", default=str(Path(__file__).parent.parent.parent))
    parser.add_argument("--task", help="Headless task")
    args = parser.parse_args()

    config = AgentConfig.from_dir(args.agent_dir)
    adapter = CodexAdapter(config)

    if args.task:
        print(adapter.launch_headless(args.task))
    else:
        adapter.launch()


if __name__ == "__main__":
    main()
