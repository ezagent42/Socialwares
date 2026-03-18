#!/usr/bin/env python3
"""KimiCode SDK launcher.

Reads GitAgent directory and launches via KimiCode SDK.

Usage:
  uv run launcher.py --agent-dir ../../
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import AgentConfig, BaseAdapter


class KimiCodeAdapter(BaseAdapter):
    """KimiCode SDK adapter."""

    def build_system_prompt(self) -> str:
        parts = [self.config.soul]
        if self.config.rules:
            parts.append(f"\n---\n{self.config.rules}")
        return "\n".join(parts)

    def launch(self) -> None:
        print(f"[KimiCode Adapter] Launching agent: {self.config.name}")
        print("[KimiCode Adapter] Mock mode — SDK not installed yet")

    def launch_headless(self, task: str) -> str:
        return f"[Mock] Would execute via KimiCode SDK: {task}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch agent via KimiCode SDK")
    parser.add_argument("--agent-dir", default=str(Path(__file__).parent.parent.parent))
    parser.add_argument("--task", help="Headless task")
    args = parser.parse_args()

    config = AgentConfig.from_dir(args.agent_dir)
    adapter = KimiCodeAdapter(config)

    if args.task:
        print(adapter.launch_headless(args.task))
    else:
        adapter.launch()


if __name__ == "__main__":
    main()
