#!/usr/bin/env python3
"""Claude Agent SDK launcher.

Reads GitAgent directory and launches via Claude Agent SDK.

Usage:
  uv run launcher.py                              # launch main agent
  uv run launcher.py --agent-dir ../../agents/code-reviewer  # launch sub-agent
  uv run launcher.py --task "Review PR #42"        # headless mode
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import AgentConfig, BaseAdapter


class ClaudeAdapter(BaseAdapter):
    """Claude Agent SDK adapter."""

    def build_system_prompt(self) -> str:
        parts = [self.config.soul]
        if self.config.rules:
            parts.append(f"\n---\n{self.config.rules}")

        # Load SKILL.md from each skill directory
        agent_dir = Path(__file__).parent.parent.parent
        skills_dir = agent_dir / "skills"
        for skill_name in self.config.skills:
            skill_md = skills_dir / skill_name / "SKILL.md"
            if skill_md.exists():
                parts.append(f"\n---\n{skill_md.read_text()}")

        return "\n".join(parts)

    def launch(self) -> None:
        system_prompt = self.build_system_prompt()
        print(f"[Claude Adapter] Launching agent: {self.config.name}")
        print(f"[Claude Adapter] Model: {self.config.model_preferred}")
        print(f"[Claude Adapter] System prompt length: {len(system_prompt)} chars")
        print(f"[Claude Adapter] Max turns: {self.config.max_turns}")
        print()

        # TODO: Replace with actual Claude Agent SDK call
        # from claude_agent_sdk import Agent
        # agent = Agent(
        #     model=self.config.model_preferred,
        #     system_prompt=system_prompt,
        #     max_turns=self.config.max_turns,
        # )
        # agent.run()

        print("[Claude Adapter] Mock mode — SDK not installed yet")
        print(f"[Claude Adapter] Would launch with prompt:\n{system_prompt[:500]}...")

    def launch_headless(self, task: str) -> str:
        system_prompt = self.build_system_prompt()
        print(f"[Claude Adapter] Headless task: {task}")

        # TODO: Replace with actual Claude Agent SDK call
        # from claude_agent_sdk import Agent
        # agent = Agent(
        #     model=self.config.model_preferred,
        #     system_prompt=system_prompt,
        #     max_turns=self.config.max_turns,
        # )
        # return agent.run_headless(task)

        return f"[Mock] Would execute: {task}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch agent via Claude SDK")
    parser.add_argument("--agent-dir", default=str(Path(__file__).parent.parent.parent),
                        help="GitAgent directory")
    parser.add_argument("--task", help="Headless task (omit for interactive)")
    args = parser.parse_args()

    config = AgentConfig.from_dir(args.agent_dir)
    adapter = ClaudeAdapter(config)

    if args.task:
        result = adapter.launch_headless(args.task)
        print(result)
    else:
        adapter.launch()


if __name__ == "__main__":
    main()
