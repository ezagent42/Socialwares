#!/usr/bin/env python3
"""OpenAI Codex/Agents SDK adapter.

Reference:
- CLI: https://openai.github.io/codex/cli/reference
- SDK: https://openai.github.io/openai-agents-python/
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


class CodexAdapter(BaseAdapter):
    """OpenAI Codex CLI / Agents SDK adapter."""

    def launch_shell(self) -> None:
        subprocess.run(["codex", "--cd", str(self.config.project_dir), "--full-auto"])

    @classmethod
    def is_available(cls) -> bool:
        return shutil.which("codex") is not None

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def query(self, prompt: str) -> list[dict]:
        try:
            from agents import Agent, Runner
            agent = Agent(name=self.config.name, instructions=self.config.soul)
            result = await Runner.run(agent, prompt)
            return [{"type": "text", "text": result.final_output}]
        except ImportError:
            return [{"type": "text", "text": "[Codex SDK not installed] pip install openai-agents"}]

    def launch_sdk(self) -> None:
        print(f"[Codex SDK] Launching {self.config.name}")
        try:
            from agents import Agent, Runner
            agent = Agent(name=self.config.name, instructions=self.config.soul)
            result = Runner.run_sync(agent, "You are ready.")
            print(result.final_output)
        except ImportError:
            print("[Codex SDK] openai-agents not installed.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir")
    args = parser.parse_args()
    config = RoleConfig.from_runtime(args.project_dir)
    CodexAdapter(config).launch_sdk()
