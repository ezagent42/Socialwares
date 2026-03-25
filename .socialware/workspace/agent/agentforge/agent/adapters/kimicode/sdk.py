#!/usr/bin/env python3
"""Kimi Code SDK adapter.

Reference:
- CLI: https://moonshotai.github.io/kimi-cli/en/reference/kimi-command.html
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from base import BaseAdapter, RoleConfig


class KimiCodeAdapter(BaseAdapter):
    """Kimi Code CLI adapter."""

    def launch_shell(self) -> None:
        subprocess.run(["kimi", "--work-dir", str(self.config.project_dir), "--yolo"])

    @classmethod
    def is_available(cls) -> bool:
        return shutil.which("kimi") is not None

    async def connect(self) -> None:
        self._connected = True

    async def disconnect(self) -> None:
        self._connected = False

    async def query(self, prompt: str) -> list[dict]:
        try:
            result = subprocess.run(
                ["kimi", "--work-dir", str(self.config.project_dir), "--yolo", "-p", prompt],
                capture_output=True, text=True, timeout=120,
            )
            return [{"type": "text", "text": result.stdout}]
        except FileNotFoundError:
            return [{"type": "text", "text": "[Kimi CLI not installed]"}]
        except subprocess.TimeoutExpired:
            return [{"type": "text", "text": "[Kimi CLI timeout]"}]

    def launch_sdk(self) -> None:
        print(f"[Kimi] Launching {self.config.name} via CLI")
        self.launch_shell()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("project_dir")
    args = parser.parse_args()
    config = RoleConfig.from_runtime(args.project_dir)
    KimiCodeAdapter(config).launch_shell()
